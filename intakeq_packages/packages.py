"""Rebuild appointment-package balances from IntakeQ appointments + invoices.

Facts the public API gives us
  * Every appointment carries AppointmentPackageId (one id per *purchased package instance*)
    and AppointmentPackageName (the package definition's name).
  * Invoices carry line Items with Description / Price / Units / Date; a package sale is a
    line item whose Description contains the package name.

Facts it does NOT give us, which live in a local config mirror (packages.json)
  * how many sessions a package contains, and its expiry rule.

Balance per package instance = sessions_in_definition - used - scheduled.

Cancellation rule (official Appointment Packages article): a canceled package appointment is
NOT replenished back to the package unless staff add the slot back. So by default Canceled
counts as used, whatever its date. If your staff routinely re-add canceled slots, drop
"Canceled" from count_as_used in packages.json to avoid double counting.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class PackageDefinition:
    name: str
    sessions: Optional[int] = None
    valid_days: Optional[int] = None
    expiry_basis: str = "booking"  # booking | appointment


@dataclass
class PackageConfig:
    packages: Dict[str, PackageDefinition] = field(default_factory=dict)
    count_as_used: List[str] = field(default_factory=lambda: ["Confirmed", "Missed", "Canceled"])
    count_as_scheduled: List[str] = field(default_factory=lambda: ["Confirmed", "WaitingConfirmation"])

    @classmethod
    def load(cls, path: str) -> "PackageConfig":
        with open(path) as f:
            raw = json.load(f)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PackageConfig":
        cfg = cls()
        for name, spec in (raw.get("packages") or {}).items():
            cfg.packages[name] = PackageDefinition(
                name=name,
                sessions=spec.get("sessions"),
                valid_days=spec.get("valid_days"),
                expiry_basis=spec.get("expiry_basis", "booking"),
            )
        cfg.count_as_used = raw.get("count_as_used", cfg.count_as_used)
        cfg.count_as_scheduled = raw.get("count_as_scheduled", cfg.count_as_scheduled)
        return cfg

    def definition(self, name: Optional[str]) -> PackageDefinition:
        if name in self.packages:
            return self.packages[name]
        # Tolerate case / whitespace drift between PracticeQ and the config.
        wanted = (name or "").strip().lower()
        for key, d in self.packages.items():
            if key.strip().lower() == wanted:
                return d
        return PackageDefinition(name=name or "")


@dataclass
class PackageLedger:
    package_instance_id: str
    package_name: str
    client_id: Optional[int]
    client_name: str
    client_email: str
    sessions_total: Optional[int]
    used: int
    scheduled: int
    remaining: Optional[int]
    first_booked: Optional[str]
    last_appointment: Optional[str]
    purchase_date: Optional[str]
    purchase_invoice_number: Optional[int]
    purchase_amount: Optional[float]
    expires_on: Optional[str]
    expired: Optional[bool]
    status: str  # active | exhausted | expired | unknown-definition
    appointment_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_date(unix_ms_or_s: Optional[float]) -> Optional[dt.date]:
    if unix_ms_or_s in (None, 0):
        return None
    v = float(unix_ms_or_s)
    if v > 1e11:  # IntakeQ returns milliseconds
        v /= 1000.0
    return dt.datetime.fromtimestamp(v, tz=dt.timezone.utc).date()


def _iso(d: Optional[dt.date]) -> Optional[str]:
    return d.isoformat() if d else None


CONSUMED_REGARDLESS_OF_DATE = {"Canceled"}


def _purchase_record(inv: Dict[str, Any], item: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    issued = _to_date(inv.get("IssuedDate") or (item or {}).get("Date") or inv.get("DateCreated"))
    amount = (item or {}).get("TotalAmount", (item or {}).get("Price")) if item else inv.get("TotalAmount")
    return {
        "invoice_number": inv.get("Number"),
        "invoice_id": inv.get("Id"),
        "issued": issued,
        "amount": amount,
        "status": inv.get("Status"),
    }


def _find_purchase(
    invoices: Iterable[Dict[str, Any]],
    client_id: Optional[int],
    package_name: str,
    around: Optional[dt.date],
    linked_invoice_ids: Iterable[str] = (),
) -> Optional[Dict[str, Any]]:
    """Pick the invoice that most plausibly sold this package instance.

    1. Prefer an invoice directly linked from a package appointment (Appointment.InvoiceId).
    2. Otherwise match on client + a line-item Description containing the package name,
       preferring the issued date closest to (and not after) the first booking.
    """
    invoices = list(invoices)
    linked = {i for i in linked_invoice_ids if i}
    if linked:
        for inv in invoices:
            if inv.get("Id") in linked and inv.get("Status") not in ("Draft", "Canceled", "Cancelled"):
                wanted_l = package_name.strip().lower()
                item = next((it for it in inv.get("Items") or [] if wanted_l and wanted_l in (it.get("Description") or "").lower()), None)
                return _purchase_record(inv, item)

    wanted = package_name.strip().lower()
    if not wanted:
        return None
    best = None
    best_score = None
    for inv in invoices:
        inv_client = inv.get("ClientIdNumber") or inv.get("ClientId")
        try:
            inv_client = int(inv_client)
        except (TypeError, ValueError):
            pass
        if client_id is not None and inv_client != client_id:
            continue
        if inv.get("Status") in ("Draft", "Canceled", "Cancelled"):
            continue
        for item in inv.get("Items") or []:
            desc = (item.get("Description") or "").strip().lower()
            if wanted not in desc:
                continue
            issued = _to_date(inv.get("IssuedDate") or item.get("Date") or inv.get("DateCreated"))
            if around and issued:
                delta = (around - issued).days
                score = delta if delta >= 0 else 10_000 + abs(delta)  # prefer sale before first booking
            else:
                score = 5_000
            if best_score is None or score < best_score:
                best_score = score
                best = _purchase_record(inv, item)
    return best


def build_ledger(
    appointments: Iterable[Dict[str, Any]],
    config: PackageConfig,
    invoices: Optional[Iterable[Dict[str, Any]]] = None,
    today: Optional[dt.date] = None,
) -> List[PackageLedger]:
    today = today or dt.datetime.now(tz=dt.timezone.utc).date()
    invoices = list(invoices or [])

    groups: Dict[str, List[Dict[str, Any]]] = {}
    for appt in appointments:
        pid = appt.get("AppointmentPackageId")
        if not pid:
            continue
        groups.setdefault(pid, []).append(appt)

    ledgers: List[PackageLedger] = []
    for pid, appts in groups.items():
        appts.sort(key=lambda a: a.get("StartDate") or 0)
        head = appts[0]
        name = head.get("AppointmentPackageName") or ""
        definition = config.definition(name)
        client_id = head.get("ClientId")

        used = scheduled = 0
        for a in appts:
            status = a.get("Status")
            start = _to_date(a.get("StartDate"))
            is_past = start is not None and start <= today
            if status in config.count_as_used and (is_past or status in CONSUMED_REGARDLESS_OF_DATE):
                used += 1
            elif not is_past and status in config.count_as_scheduled:
                scheduled += 1

        first_booked = min((_to_date(a.get("DateCreated")) for a in appts if a.get("DateCreated")), default=None)
        last_appt = max((_to_date(a.get("StartDate")) for a in appts if a.get("StartDate")), default=None)

        purchase = _find_purchase(invoices, client_id, name, first_booked,
                                  linked_invoice_ids=[a.get("InvoiceId") for a in appts])
        purchase_date = (purchase or {}).get("issued") or first_booked

        warnings: List[str] = []
        remaining: Optional[int] = None
        if definition.sessions is None:
            warnings.append(f"package '{name}' not in config; sessions total unknown")
        else:
            remaining = definition.sessions - used - scheduled
            if remaining < 0:
                warnings.append("more appointments linked than sessions in definition; check config")

        expires_on: Optional[dt.date] = None
        if definition.valid_days and purchase_date:
            expires_on = purchase_date + dt.timedelta(days=definition.valid_days)
        expired: Optional[bool] = (expires_on < today) if expires_on else None
        if purchase is None and invoices:
            warnings.append("no matching invoice line item found; purchase date taken from first booking")

        if definition.sessions is None:
            status = "unknown-definition"
        elif expired:
            status = "expired"
        elif remaining is not None and remaining <= 0 and scheduled == 0:
            status = "exhausted"
        else:
            status = "active"

        ledgers.append(
            PackageLedger(
                package_instance_id=pid,
                package_name=name,
                client_id=client_id,
                client_name=head.get("ClientName") or "",
                client_email=head.get("ClientEmail") or "",
                sessions_total=definition.sessions,
                used=used,
                scheduled=scheduled,
                remaining=remaining,
                first_booked=_iso(first_booked),
                last_appointment=_iso(last_appt),
                purchase_date=_iso(purchase_date),
                purchase_invoice_number=(purchase or {}).get("invoice_number"),
                purchase_amount=(purchase or {}).get("amount"),
                expires_on=_iso(expires_on),
                expired=expired,
                status=status,
                appointment_ids=[a.get("Id") for a in appts],
                warnings=warnings,
            )
        )

    ledgers.sort(key=lambda l: (l.client_name.lower(), l.purchase_date or ""))
    return ledgers
