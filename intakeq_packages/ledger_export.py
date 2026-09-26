"""Produce the cockpit-facing ledger: a CSV with exactly the PracticeQ Packages export columns,
plus a sidecar CSV of derived fields keyed by package id.

Rules (from the practice owner):
  * per-purchase session totals come from the export, never from the package name;
  * PracticeQ's own UnusedSessions column is copied through untouched;
  * new package instances seen in appointments but absent from the export get a row built
    from API data so the cockpit can diff and adopt them.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
from typing import Any, Dict, Iterable, List, Optional

from .packages import PackageConfig, PackageLedger, build_ledger
from .sources import PackagesExport

DERIVED_COLUMNS = [
    "package_id", "client_id", "package_name", "source", "sessions_total", "sessions_total_source",
    "used", "scheduled", "remaining_derived", "unused_practiceq", "purchase_date", "expires_on", "expired",
    "status", "first_booked", "last_appointment", "appointment_ids", "warnings",
]


def merge_export_into_ledger(ledgers: List[PackageLedger], export: Optional[PackagesExport],
                             config: PackageConfig, today: Optional[dt.date] = None) -> List[Dict[str, Any]]:
    """Return one derived record per package instance, preferring export totals over config defaults."""
    today = today or dt.datetime.now(tz=dt.timezone.utc).date()
    by_id = export.by_package_id() if export else {}
    derived: List[Dict[str, Any]] = []
    seen: set = set()

    for l in ledgers:
        exp = by_id.get(l.package_instance_id)
        seen.add(l.package_instance_id)
        total, total_src = l.sessions_total, "config-default"
        purchase = dt.date.fromisoformat(l.purchase_date) if l.purchase_date else None
        expires = dt.date.fromisoformat(l.expires_on) if l.expires_on else None
        warnings = list(l.warnings)
        if exp:
            if exp.sessions_total is not None:
                total, total_src = exp.sessions_total, "export"
            if exp.purchase_date:
                purchase = exp.purchase_date
                definition = config.definition(l.package_name)
                expires = exp.expiry_date or (purchase + dt.timedelta(days=definition.valid_days) if definition.valid_days else None)
            elif exp.expiry_date:
                expires = exp.expiry_date
            if exp.package_name and exp.package_name.strip().lower() != l.package_name.strip().lower():
                warnings.append(f"export names package '{exp.package_name}', appointments say '{l.package_name}'")
        else:
            warnings.append("not in PracticeQ export yet")
        remaining = (total - l.used - l.scheduled) if total is not None else None
        expired = (expires < today) if expires else None
        if total is None:
            status = "unknown-definition"
        elif expired:
            status = "expired"
        elif remaining is not None and remaining <= 0 and l.scheduled == 0:
            status = "exhausted"
        else:
            status = "active"
        if exp and exp.sessions_unused is not None and remaining is not None and exp.sessions_unused != remaining:
            warnings.append(f"PracticeQ UnusedSessions={exp.sessions_unused} vs derived remaining={remaining}")
        derived.append({
            "package_id": l.package_instance_id, "client_id": l.client_id, "package_name": l.package_name,
            "source": "export+appointments" if exp else "appointments-only",
            "sessions_total": total, "sessions_total_source": total_src,
            "used": l.used, "scheduled": l.scheduled, "remaining_derived": remaining,
            "unused_practiceq": exp.sessions_unused if exp else None,
            "purchase_date": purchase.isoformat() if purchase else None,
            "expires_on": expires.isoformat() if expires else None, "expired": expired, "status": status,
            "first_booked": l.first_booked, "last_appointment": l.last_appointment,
            "appointment_ids": "|".join(l.appointment_ids), "warnings": "; ".join(warnings),
        })

    # Export rows with no linked appointments at all (fully unscheduled packages).
    for pid, exp in by_id.items():
        if pid in seen:
            continue
        total = exp.sessions_total if exp.sessions_total is not None else config.definition(exp.package_name).sessions
        expires = exp.expiry_date
        if not expires and exp.purchase_date and config.definition(exp.package_name).valid_days:
            expires = exp.purchase_date + dt.timedelta(days=config.definition(exp.package_name).valid_days)
        expired = (expires < today) if expires else None
        derived.append({
            "package_id": pid, "client_id": exp.client_id, "package_name": exp.package_name, "source": "export-only",
            "sessions_total": total, "sessions_total_source": "export" if exp.sessions_total is not None else "config-default",
            "used": 0, "scheduled": 0, "remaining_derived": total,
            "unused_practiceq": exp.sessions_unused,
            "purchase_date": exp.purchase_date.isoformat() if exp.purchase_date else None,
            "expires_on": expires.isoformat() if expires else None, "expired": expired,
            "status": "expired" if expired else ("active" if total else "unknown-definition"),
            "first_booked": None, "last_appointment": None, "appointment_ids": "", "warnings": "",
        })
    derived.sort(key=lambda d: (d["package_name"], d["purchase_date"] or ""))
    return derived


def export_compatible_rows(export: Optional[PackagesExport], derived: Iterable[Dict[str, Any]],
                           ledgers: List[PackageLedger]) -> (List[str], List[Dict[str, str]]):
    """Rows with the export's exact columns: existing rows passed through verbatim (UnusedSessions
    untouched), new instances filled from API data where a column mapping exists."""
    if export is None:
        cols = ["Id", "ClientId", "ClientName", "PackageName", "TotalSessions", "UnusedSessions", "PurchaseDate", "ExpirationDate"]
        mapping = {"package_id": "Id", "client_id": "ClientId", "client_name": "ClientName", "package_name": "PackageName",
                   "sessions_total": "TotalSessions", "sessions_unused": "UnusedSessions",
                   "purchase_date": "PurchaseDate", "expiry_date": "ExpirationDate"}
        by_id = {}
    else:
        cols, mapping, by_id = export.columns, export.mapping, export.by_package_id()
    ledger_by_id = {l.package_instance_id: l for l in ledgers}
    rows: List[Dict[str, str]] = []
    for d in derived:
        pid = d["package_id"]
        if pid in by_id:
            rows.append(dict(by_id[pid].row))       # verbatim passthrough
            continue
        l = ledger_by_id.get(pid)
        row = {c: "" for c in cols}
        def put(k, v):
            c = mapping.get(k)
            if c and v not in (None, ""):
                row[c] = str(v)
        put("package_id", pid); put("client_id", d["client_id"]); put("package_name", d["package_name"])
        put("client_name", l.client_name if l else "")
        put("sessions_total", d["sessions_total"]); put("purchase_date", d["purchase_date"]); put("expiry_date", d["expires_on"])
        # UnusedSessions is PracticeQ's counter; for brand-new rows we have nothing else, so leave it blank.
        rows.append(row)
    return cols, rows


def write_ledger_files(out_dir: str, export: Optional[PackagesExport], ledgers: List[PackageLedger],
                       derived: List[Dict[str, Any]], ledger_name: str = "packages_ledger.csv",
                       derived_name: str = "packages_ledger_derived.csv") -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    cols, rows = export_compatible_rows(export, derived, ledgers)
    p1 = os.path.join(out_dir, ledger_name)
    with open(p1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    p2 = os.path.join(out_dir, derived_name)
    with open(p2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DERIVED_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for d in derived:
            w.writerow({k: ("" if v is None else v) for k, v in d.items()})
    return {"ledger": p1, "derived": p2}
