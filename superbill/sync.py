"""Find clients whose superbill needs a refresh, rebuild it, and replace the file in PracticeQ.

``SuperbillSync.sync(since_days)`` is stateless and idempotent: it looks at every appointment
scheduled in the last ``since_days`` days plus anything modified since yesterday (a cancellation
of a past visit also changes the superbill), collects the distinct clients, and calls
``refresh(client_id)`` for each. ``refresh`` builds the data, skips the upload when the
fingerprint matches the last upload (optional state file), otherwise renders the PDF, deletes
any older file whose name starts with ``file.replace_prefix`` and uploads the new one.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .api import SuperbillAPI
from .build import SuperbillData, appointment_end, build_superbill
from .render import render_pdf

log = logging.getLogger("superbill.sync")


@dataclass
class RefreshResult:
    client_id: int
    action: str  # uploaded | unchanged | no-visits | error
    file_name: str = ""
    visits: int = 0
    deleted: int = 0
    error: str = ""


@dataclass
class SyncResult:
    started: str
    finished: str = ""
    candidates: int = 0
    results: List[RefreshResult] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for r in self.results:
            counts[r.action] = counts.get(r.action, 0) + 1
        return {"started": self.started, "finished": self.finished, "candidates": self.candidates, **counts}


class SuperbillSync:
    def __init__(self, api: SuperbillAPI, cfg: Dict[str, Any], dry_run: bool = False, state_path: Optional[str] = None):
        self.api = api
        self.cfg = cfg
        self.dry_run = dry_run
        self.tz = ZoneInfo(cfg["timezone"])
        if state_path is None:
            state_path = os.environ.get("SUPERBILL_STATE") or cfg.get("sync", {}).get("state_path") or ""
        self.state_path = state_path
        self.state: Dict[str, str] = self._load_state()

    # ---- state (optional): client id -> fingerprint of the last uploaded superbill ------

    def _load_state(self) -> Dict[str, str]:
        if self.state_path and os.path.exists(self.state_path):
            try:
                with open(self.state_path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _save_state(self) -> None:
        if not self.state_path or self.dry_run:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.state_path)), exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=1, sort_keys=True)
        os.replace(tmp, self.state_path)

    # ---- one client ----------------------------------------------------------------------

    def file_name(self, data: SuperbillData) -> str:
        fmt = self.cfg["file"]["name_format"]
        safe = re.sub(r'[\\/:*?"<>|]+', " ", data.client_name).strip() or str(data.client_id)
        return fmt.format(name=safe, client_id=data.client_id, date=data.statement_date.isoformat())

    def refresh(self, client_id: int, seed_appointment: Optional[Dict[str, Any]] = None, force: bool = False) -> RefreshResult:
        try:
            data = build_superbill(self.api, client_id, self.cfg, seed_appointment=seed_appointment)
        except Exception as e:  # noqa: BLE001
            log.exception("build failed for client %s", client_id)
            return RefreshResult(client_id, "error", error=str(e))
        if data is None:
            return RefreshResult(client_id, "no-visits")
        fp = data.fingerprint()
        if not force and self.state.get(str(client_id)) == fp:
            return RefreshResult(client_id, "unchanged", visits=len(data.lines))
        name = self.file_name(data)
        pdf = render_pdf(data, self.cfg)
        if self.dry_run:
            return RefreshResult(client_id, "uploaded", file_name=name, visits=len(data.lines))
        try:
            deleted = self._delete_previous(client_id)
            self.api.upload_file(client_id, name, pdf)
        except Exception as e:  # noqa: BLE001
            log.exception("upload failed for client %s", client_id)
            return RefreshResult(client_id, "error", file_name=name, visits=len(data.lines), error=str(e))
        self.state[str(client_id)] = fp
        self._save_state()
        return RefreshResult(client_id, "uploaded", file_name=name, visits=len(data.lines), deleted=deleted)

    def _delete_previous(self, client_id: int) -> int:
        prefix = self.cfg["file"]["replace_prefix"]
        n = 0
        for f in self.api.files(client_id):
            if str(f.get("FileName") or "").startswith(prefix):
                self.api.delete_file(str(f["Id"]))
                n += 1
        return n

    # ---- many clients ---------------------------------------------------------------------

    def candidates(self, since_days: int, now: Optional[datetime] = None) -> Dict[int, Dict[str, Any]]:
        """Clients with an appointment that ended in the window, or any appointment modified
        since yesterday. Returns {client_id: one appointment (used as the search seed)}."""
        now = (now or datetime.now(self.tz)).astimezone(self.tz)
        today = now.date()
        start = (today - timedelta(days=since_days)).isoformat()
        end = (today + timedelta(days=1)).isoformat()
        out: Dict[int, Dict[str, Any]] = {}
        for a in self.api.appointments(start_date=start, end_date=end):
            cid = a.get("ClientId")
            if cid is None:
                continue
            finished = appointment_end(a, self.tz)
            if str(a.get("Status")) in self.cfg["completed_statuses"] and finished and finished <= now:
                out.setdefault(int(cid), a)
        yesterday = (today - timedelta(days=1)).isoformat()
        for a in self.api.appointments(updated_since=yesterday):
            cid = a.get("ClientId")
            if cid is None:
                continue
            started = a.get("StartDate")
            if started and appointment_end(a, self.tz) and appointment_end(a, self.tz) <= now:
                out.setdefault(int(cid), a)
        return out

    def sync(self, since_days: Optional[int] = None, now: Optional[datetime] = None) -> SyncResult:
        since = int(since_days if since_days is not None else self.cfg["sync"]["lookback_days"])
        res = SyncResult(started=datetime.now(self.tz).isoformat(timespec="seconds"))
        cands = self.candidates(since, now)
        res.candidates = len(cands)
        for cid, seed in sorted(cands.items()):
            r = self.refresh(cid, seed_appointment=seed)
            log.info("client %s: %s %s", cid, r.action, r.file_name or r.error)
            res.results.append(r)
        res.finished = datetime.now(self.tz).isoformat(timespec="seconds")
        return res
