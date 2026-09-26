"""Loaders for the cockpit's existing data files, tolerant of unknown column names.

The cockpit keeps two files that we must consume rather than rebuild:
  * data/packages_all.csv   the PracticeQ Packages export (one row per purchased package)
  * data/appt_packages.json the package each appointment was charged to (20k+ rows)

Neither schema is known to this code yet, so columns and keys are detected by name
heuristics and the detected mapping is reported so it can be pinned in config later.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Semantic field -> candidate column-name fragments, tried in order, case-insensitive.
EXPORT_FIELD_HINTS: Dict[str, List[str]] = {
    "package_id":      ["packageid", "package_id", "appointmentpackageid", "^id$", "guid"],
    "client_id":       ["clientidnumber", "clientid", "client_id", "clientnumber"],
    "client_name":     ["clientname", "client_name", "^client$", "patient"],
    "package_name":    ["packagename", "package_name", "^package$", "^name$", "title"],
    "sessions_total":  ["totalsessions", "sessions_total", "total_sessions", "numberofsessions", "sessions", "total"],
    "sessions_unused": ["unusedsessions", "unused", "remaining", "sessionsleft"],
    "sessions_used":   ["usedsessions", "used", "completed", "consumed"],
    "purchase_date":   ["purchasedate", "purchase_date", "datecreated", "created", "purchased", "startdate"],
    "expiry_date":     ["expirationdate", "expirydate", "expires", "expiration", "expiry"],
    "practitioner":    ["practitioner", "provider", "therapist"],
    "price":           ["price", "amount", "total"],
}

APPT_KEY_HINTS: Dict[str, List[str]] = {
    "appointment_id": ["appointmentid", "appointment_id", "apptid", "^id$"],
    "package_id":     ["appointmentpackageid", "packageid", "package_id", "package"],
    "package_name":   ["appointmentpackagename", "packagename", "package_name"],
    "client_id":      ["clientid", "client_id"],
    "status":         ["status"],
    "start":          ["startdate", "start", "date"],
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def detect_columns(columns: Iterable[str], hints: Dict[str, List[str]]) -> Dict[str, Optional[str]]:
    cols = list(columns)
    normed = {c: _norm(c) for c in cols}
    taken: set = set()
    out: Dict[str, Optional[str]] = {}
    for field_name, candidates in hints.items():
        hit = None
        for cand in candidates:
            if cand.startswith("^") and cand.endswith("$"):
                target = _norm(cand[1:-1])
                hit = next((c for c in cols if normed[c] == target and c not in taken), None)
            else:
                target = _norm(cand)
                hit = next((c for c in cols if target in normed[c] and c not in taken), None)
            if hit:
                break
        out[field_name] = hit
        if hit:
            taken.add(hit)
    return out


def _to_int(v: Any) -> Optional[int]:
    if v in (None, ""):
        return None
    try:
        return int(float(str(v).strip()))
    except ValueError:
        return None


def _to_date(v: Any) -> Optional[dt.date]:
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        if x > 1e11:
            x /= 1000.0
        return dt.datetime.fromtimestamp(x, tz=dt.timezone.utc).date()
    s = str(v).strip()
    if re.fullmatch(r"\d{12,13}", s):
        return dt.datetime.fromtimestamp(int(s) / 1000.0, tz=dt.timezone.utc).date()
    if re.fullmatch(r"\d{9,10}", s):
        return dt.datetime.fromtimestamp(int(s), tz=dt.timezone.utc).date()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%m/%d/%Y %H:%M", "%m/%d/%y", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s[: len(dt.datetime.now().strftime(fmt))] if "T" in fmt else s, fmt).date()
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


@dataclass
class ExportPackage:
    row: Dict[str, str]                 # the original export row, untouched
    package_id: Optional[str]
    client_id: Optional[int]
    client_name: str
    package_name: str
    sessions_total: Optional[int]
    sessions_unused: Optional[int]
    purchase_date: Optional[dt.date]
    expiry_date: Optional[dt.date]


@dataclass
class PackagesExport:
    path: str
    columns: List[str]
    mapping: Dict[str, Optional[str]]
    rows: List[ExportPackage] = field(default_factory=list)

    @classmethod
    def load(cls, path: str, mapping_override: Optional[Dict[str, str]] = None) -> "PackagesExport":
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columns = list(reader.fieldnames or [])
            raw_rows = list(reader)
        mapping = detect_columns(columns, EXPORT_FIELD_HINTS)
        if mapping_override:
            mapping.update(mapping_override)
        exp = cls(path=path, columns=columns, mapping=mapping)
        g = lambda r, k: r.get(mapping[k]) if mapping.get(k) else None  # noqa: E731
        for r in raw_rows:
            exp.rows.append(ExportPackage(
                row=r,
                package_id=(g(r, "package_id") or "").strip() or None,
                client_id=_to_int(g(r, "client_id")),
                client_name=(g(r, "client_name") or "").strip(),
                package_name=(g(r, "package_name") or "").strip(),
                sessions_total=_to_int(g(r, "sessions_total")),
                sessions_unused=_to_int(g(r, "sessions_unused")),
                purchase_date=_to_date(g(r, "purchase_date")),
                expiry_date=_to_date(g(r, "expiry_date")),
            ))
        return exp

    def by_package_id(self) -> Dict[str, ExportPackage]:
        return {r.package_id: r for r in self.rows if r.package_id}

    def missing_fields(self) -> List[str]:
        return [k for k, v in self.mapping.items() if v is None and k in ("package_id", "package_name", "sessions_total")]


@dataclass
class ApptPackageMap:
    """appointment_id -> {package_id, package_name, client_id, status, start}, plus the raw records."""
    path: str
    mapping: Dict[str, Optional[str]]
    records: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    raw: Any = None

    @classmethod
    def load(cls, path: str) -> "ApptPackageMap":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        items: List[Tuple[Optional[str], Dict[str, Any]]]
        if isinstance(raw, dict) and raw and all(isinstance(v, dict) for v in raw.values()):
            items = [(k, v) for k, v in raw.items()]           # {apptId: {...}}
        elif isinstance(raw, dict) and raw and all(isinstance(v, str) or v is None for v in raw.values()):
            items = [(k, {"packageId": v}) for k, v in raw.items()]  # {apptId: packageId}
        elif isinstance(raw, list):
            items = [(None, r) for r in raw if isinstance(r, dict)]
        else:
            items = []
        sample_keys = set()
        for _, rec in items[:200]:
            sample_keys.update(rec.keys())
        mapping = detect_columns(sample_keys, APPT_KEY_HINTS)
        m = cls(path=path, mapping=mapping, raw=raw)
        for key, rec in items:
            appt_id = key or (rec.get(mapping["appointment_id"]) if mapping.get("appointment_id") else None)
            if not appt_id:
                continue
            m.records[str(appt_id)] = {
                "package_id": rec.get(mapping["package_id"]) if mapping.get("package_id") else None,
                "package_name": rec.get(mapping["package_name"]) if mapping.get("package_name") else None,
                "client_id": rec.get(mapping["client_id"]) if mapping.get("client_id") else None,
                "status": rec.get(mapping["status"]) if mapping.get("status") else None,
                "start": rec.get(mapping["start"]) if mapping.get("start") else None,
                "_raw": rec,
            }
        return m

    def as_appointments(self) -> List[Dict[str, Any]]:
        """Project to the IntakeQ appointment shape that build_ledger understands."""
        out = []
        for appt_id, r in self.records.items():
            if not r.get("package_id"):
                continue
            raw = r["_raw"]
            start = r.get("start")
            start_ms = None
            d = _to_date(start)
            if d:
                start_ms = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)
            out.append({
                "Id": appt_id,
                "ClientId": _to_int(r.get("client_id")),
                "ClientName": raw.get("ClientName", ""),
                "ClientEmail": raw.get("ClientEmail", ""),
                "Status": r.get("status") or "Confirmed",
                "StartDate": raw.get("StartDate", start_ms),
                "DateCreated": raw.get("DateCreated", start_ms),
                "InvoiceId": raw.get("InvoiceId"),
                "AppointmentPackageId": r["package_id"],
                "AppointmentPackageName": r.get("package_name") or "",
            })
        return out

    def upsert_from_appointment(self, appt: Dict[str, Any]) -> bool:
        """Record a live appointment (from GET /appointments/{id} or a webhook). Returns True if changed."""
        appt_id = str(appt.get("Id"))
        new = {
            "package_id": appt.get("AppointmentPackageId"),
            "package_name": appt.get("AppointmentPackageName"),
            "client_id": appt.get("ClientId"),
            "status": appt.get("Status"),
            "start": appt.get("StartDate"),
        }
        old = self.records.get(appt_id)
        if old and all(old.get(k) == v for k, v in new.items()):
            return False
        keep = dict((old or {}).get("_raw") or {})
        # Reuse the file's own key names where they were detected, so the file stays homogeneous.
        k = lambda semantic, default: self.mapping.get(semantic) or default  # noqa: E731
        keep.update({
            k("appointment_id", "AppointmentId"): appt_id,
            k("package_id", "AppointmentPackageId"): new["package_id"],
            k("package_name", "AppointmentPackageName"): new["package_name"],
            k("client_id", "ClientId"): new["client_id"],
            k("status", "Status"): new["status"],
            k("start", "StartDate"): new["start"],
            "DateCreated": appt.get("DateCreated"), "InvoiceId": appt.get("InvoiceId"), "LastModified": appt.get("LastModified"),
        })
        if not self.mapping.get("appointment_id"):
            self.mapping["appointment_id"] = "AppointmentId"
        for sem, default in (("package_id", "AppointmentPackageId"), ("package_name", "AppointmentPackageName"),
                             ("client_id", "ClientId"), ("status", "Status"), ("start", "StartDate")):
            self.mapping.setdefault(sem, default)
            if self.mapping[sem] is None:
                self.mapping[sem] = default
        self.records[appt_id] = {**new, "_raw": keep}
        return True

    def save(self, path: Optional[str] = None) -> None:
        """Write back in the same top-level shape the file was loaded with."""
        path = path or self.path
        if isinstance(self.raw, dict) and self.raw and all(isinstance(v, str) or v is None for v in self.raw.values()):
            data: Any = {k: v["package_id"] for k, v in self.records.items()}
        elif isinstance(self.raw, dict):
            data = {k: v["_raw"] for k, v in self.records.items()}
        else:
            data = [v["_raw"] for v in self.records.values()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, default=str)
