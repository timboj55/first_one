"""Nightly reconciliation: catch anything the webhook missed, rebuild the ledger, stay under budget.

Plan (owner's constraints: 20 req/min tenant limit shared with a 4:06am ET cockpit refresh,
list endpoint may lack package fields, webhooks get missed):
  1. GET /appointments?updatedSince=<since>  (1 call per 100 changed appointments)
  2. GET /appointments/{id} for each changed id, paced (default one call per 8 s, ~7.5/min)
  3. upsert into the appointment->package map (data/appt_packages.json)
  4. rebuild the ledger from the map + PracticeQ export, write CSVs
  5. stop cleanly at a hard deadline (default 03:55 America/New_York) and record what was left
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from .client import IntakeQClient
from .ledger_export import merge_export_into_ledger, write_ledger_files
from .packages import PackageConfig, build_ledger
from .sources import ApptPackageMap, PackagesExport

ET = ZoneInfo("America/New_York")


def default_deadline(now: Optional[dt.datetime] = None, hour: int = 3, minute: int = 55) -> dt.datetime:
    now = now or dt.datetime.now(tz=ET)
    dl = now.astimezone(ET).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if dl <= now:
        dl += dt.timedelta(days=1)
    return dl


def run_nightly(
    client: IntakeQClient,
    config: PackageConfig,
    appt_map_path: str,
    export_path: Optional[str],
    out_dir: str,
    since: Optional[str] = None,
    deadline: Optional[dt.datetime] = None,
    max_calls: int = 300,
    state_path: Optional[str] = None,
    now: Optional[dt.datetime] = None,
    fetch_details: bool = True,
    clock: Optional[Callable[[], dt.datetime]] = None,
) -> Dict[str, Any]:
    clock = clock or (lambda: dt.datetime.now(tz=ET))
    now = now or clock()
    deadline = deadline or default_deadline(now)
    state_path = state_path or os.path.join(out_dir, "nightly_state.json")
    state = _load_state(state_path)
    since = since or state.get("next_since") or (now - dt.timedelta(days=2)).strftime("%Y-%m-%d")

    appt_map = ApptPackageMap.load(appt_map_path) if os.path.exists(appt_map_path) else ApptPackageMap(appt_map_path, {}, {}, [])
    export = PackagesExport.load(export_path) if export_path and os.path.exists(export_path) else None

    report: Dict[str, Any] = {"since": since, "started": now.isoformat(), "deadline": deadline.isoformat(),
                              "changed_listed": 0, "details_fetched": 0, "map_updates": 0, "skipped_for_deadline": 0,
                              "carried_over_ids": [], "api_calls": 0}

    # 1. what changed
    changed: List[Dict[str, Any]] = []
    pending_ids: List[str] = list(state.get("carried_over_ids") or [])
    # Listing is cheap (1 call per 100 changed rows) and pages already fetched cost nothing more,
    # so the deadline and call budget are applied to the per-appointment fetches below only.
    changed = list(client.appointments(updated_since=since))
    report["changed_listed"] = len(changed)

    # 2. detail fetch (only if the list rows lack the package fields, or we were told to)
    for row in changed:
        rid = str(row.get("Id"))
        has_fields = "AppointmentPackageId" in row
        if has_fields and not fetch_details:
            report["map_updates"] += int(appt_map.upsert_from_appointment(row))
        else:
            pending_ids.append(rid)
    remaining: List[str] = []
    for rid in dict.fromkeys(pending_ids):  # dedupe, keep order
        if client.calls_made >= max_calls or clock() >= deadline:
            remaining.append(rid)
            continue
        try:
            detail = client.appointment(rid)
        except Exception as e:  # noqa: BLE001
            report.setdefault("errors", []).append(f"{rid}: {e}")
            remaining.append(rid)
            continue
        report["details_fetched"] += 1
        report["map_updates"] += int(appt_map.upsert_from_appointment(detail))
    report["skipped_for_deadline"] = len(remaining)
    report["carried_over_ids"] = remaining

    # 3./4. persist map, rebuild ledger
    if report["map_updates"]:
        appt_map.save()
    ledgers = build_ledger(appt_map.as_appointments(), config, today=now.date())
    derived = merge_export_into_ledger(ledgers, export, config, today=now.date())
    paths = write_ledger_files(out_dir, export, ledgers, derived)
    report.update({"package_instances": len(derived), "files": paths, "api_calls": client.calls_made,
                   "status_counts": _count(derived, "status"),
                   "export_mapping": export.mapping if export else None,
                   "appt_map_mapping": appt_map.mapping})

    # 5. state for next run: resume from yesterday relative to *this* run so a missed night is covered
    state = {"next_since": (now - dt.timedelta(days=1)).strftime("%Y-%m-%d"),
             "carried_over_ids": remaining, "last_run": now.isoformat(), "last_report": report}
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=1, default=str)
    return report


def _load_state(path: str) -> Dict[str, Any]:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _count(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        out[str(r.get(key))] = out.get(str(r.get(key)), 0) + 1
    return out
