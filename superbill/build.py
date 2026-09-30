"""Turn IntakeQ data for one client into the numbers and lines on a superbill.

Rules (all tunable in superbill_config.json):
  * A visit is "completed" when its status is in ``completed_statuses`` (default Confirmed) and
    its end time is in the past. Canceled / Missed / Declined / future visits never appear.
  * The statement covers one episode: visits since the most recent appointment whose service
    matches ``episode.start_service_pattern`` (if set), otherwise the last ``episode.rolling_days``.
  * Each line: date, description, CPT x units, charge. Procedures come from the appointment's
    ``Procedures`` list when PracticeQ provides it, else from ``service_defaults`` by service
    name (``"*"`` is the catch-all). Charge is the appointment ``Price`` (or the sum of
    procedure prices when Price is empty).
  * Money: Total Charges = sum of line charges. Invoices issued in the episode (minus
    ``invoice_lookback_days`` so a package bought before the first visit counts) give
    Total Billed (sum of TotalAmount) and Total Payments (sum of AmountPaid). Provider
    Discount = Charges - Billed. Balance = Billed - Payments. Any invoice with a
    ClientPaymentPlanId marks the account as a payment plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .api import SuperbillAPI

DEFAULT_PROCEDURE_DESCRIPTIONS = {
    "97161": "PT Evaluation, Low Complexity",
    "97162": "PT Evaluation, Moderate Complexity",
    "97163": "PT Evaluation, High Complexity",
    "97164": "PT Re-evaluation",
    "97110": "Therapeutic Exercise",
    "97112": "Neuromuscular Re-education",
    "97116": "Gait Training",
    "97140": "Manual Therapy",
    "97530": "Therapeutic Activity",
    "97535": "Self-Care / Home Management Training",
    "97750": "Physical Performance Test",
    "97010": "Hot / Cold Pack",
    "97014": "Electrical Stimulation (unattended)",
    "97032": "Electrical Stimulation (attended)",
    "97035": "Ultrasound",
    "97039": "Physical Medicine Modality (unlisted)",
    "97139": "Physical Medicine Procedure (unlisted)",
    "97150": "Group Therapeutic Procedure",
    "97799": "Physical Medicine Service (unlisted)",
    "98960": "Self-Management Education",
}


@dataclass
class Procedure:
    code: str
    units: int = 1
    modifiers: List[str] = field(default_factory=list)

    def label(self) -> str:
        code = self.code
        if self.modifiers:
            code += "-" + "-".join(self.modifiers)
        return f"{code} x{self.units}" if self.units and self.units != 1 else code


@dataclass
class Line:
    date: date
    description: str
    procedures: List[Procedure]
    charge: float
    appointment_id: str = ""

    def procedure_label(self) -> str:
        return ", ".join(p.label() for p in self.procedures) if self.procedures else ""


@dataclass
class SuperbillData:
    client_id: int
    client_name: str
    client_dob: Optional[date]
    client_address: str
    client_phone: str
    client_email: str
    diagnosis_codes: List[str]
    provider: Dict[str, str]
    lines: List[Line]
    total_charges: float
    total_billed: float
    total_payments: float
    provider_discount: float
    balance: float
    payment_plan: bool
    installments_billed: int
    episode_start: date
    episode_end: date
    statement_date: date
    invoice_numbers: List[int] = field(default_factory=list)

    @property
    def paid_in_full(self) -> bool:
        return not self.payment_plan and self.balance <= 0.005

    def fingerprint(self) -> str:
        """Stable summary of what the PDF would show; unchanged fingerprint => skip re-upload."""
        parts = [
            str(self.client_id),
            self.client_name,
            str(self.client_dob),
            ",".join(self.diagnosis_codes),
            ";".join(f"{l.date}|{l.description}|{l.procedure_label()}|{l.charge:.2f}" for l in self.lines),
            f"{self.total_charges:.2f}|{self.total_billed:.2f}|{self.total_payments:.2f}|{self.payment_plan}",
        ]
        return "\n".join(parts)


# ---- helpers ---------------------------------------------------------------------------

def _ms_to_local(ms: Any, tz: ZoneInfo) -> Optional[datetime]:
    if ms in (None, "", 0):
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).astimezone(tz)
    except (TypeError, ValueError, OSError):
        return None


def _parse_dob(value: Any, tz: ZoneInfo) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        d = _ms_to_local(value, timezone.utc)  # DOB timestamps are midnight UTC
        return d.date() if d else None
    s = str(value)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[: len(fmt) + 2 if "T" in fmt else 10], fmt).date()
        except ValueError:
            continue
    return None


def appointment_end(appt: Dict[str, Any], tz: ZoneInfo) -> Optional[datetime]:
    end = _ms_to_local(appt.get("EndDate"), tz)
    if end:
        return end
    start = _ms_to_local(appt.get("StartDate"), tz)
    if start:
        return start + timedelta(minutes=int(appt.get("Duration") or 60))
    return None


def appointment_start(appt: Dict[str, Any], tz: ZoneInfo) -> Optional[datetime]:
    return _ms_to_local(appt.get("StartDate"), tz)


def service_name(appt: Dict[str, Any]) -> str:
    return str(appt.get("ServiceName") or appt.get("Service") or "").strip()


def is_completed(appt: Dict[str, Any], now: datetime, cfg: Dict[str, Any], tz: ZoneInfo) -> bool:
    if str(appt.get("Status")) not in cfg["completed_statuses"]:
        return False
    end = appointment_end(appt, tz)
    if end is None or end > now:
        return False
    name = service_name(appt)
    for pat in cfg.get("exclude_service_patterns") or []:
        if re.search(pat, name):
            return False
    return True


def procedures_for(appt: Dict[str, Any], cfg: Dict[str, Any]) -> List[Procedure]:
    raw = appt.get("Procedures") or []
    procs: List[Procedure] = []
    for p in raw:
        code = str(p.get("ProcedureCode") or p.get("Code") or "").strip()
        if not code:
            continue
        units = int(p.get("Units") or p.get("Quantity") or 1)
        procs.append(Procedure(code, units, [str(m) for m in (p.get("Modifiers") or [])]))
    if procs:
        return procs
    defaults = cfg.get("service_defaults") or {}
    name = service_name(appt)
    spec = None
    for key, val in defaults.items():
        if key != "*" and key.lower() == name.lower():
            spec = val
            break
    if spec is None:
        for key, val in defaults.items():
            if key != "*" and re.search(key, name, re.I):
                spec = val
                break
    if spec is None:
        spec = defaults.get("*")
    if not spec:
        return []
    return [Procedure(str(spec.get("cpt")), int(spec.get("units") or 1), list(spec.get("modifiers") or []))]


def charge_for(appt: Dict[str, Any], list_prices: Optional[Dict[str, float]] = None) -> float:
    """Appointment Price; else the sum of procedure prices; else (for $0 package-covered visits)
    the service's list price from PracticeQ, matched on ServiceId then service name."""
    price = appt.get("Price")
    try:
        if price not in (None, "") and float(price) > 0:
            return round(float(price), 2)
    except (TypeError, ValueError):
        pass
    total = 0.0
    for p in appt.get("Procedures") or []:
        try:
            total += float(p.get("Price") or 0) * int(p.get("Units") or p.get("Quantity") or 1)
        except (TypeError, ValueError):
            continue
    if total > 0 or not list_prices:
        return round(total, 2)
    for key in ("id:" + str(appt.get("ServiceId") or ""), "name:" + service_name(appt).lower()):
        if list_prices.get(key, 0) > 0:
            return round(list_prices[key], 2)
    return 0.0


def description_for(appt: Dict[str, Any], procs: List[Procedure], cfg: Dict[str, Any]) -> str:
    table = {**DEFAULT_PROCEDURE_DESCRIPTIONS, **(cfg.get("procedure_descriptions") or {})}
    defaults = cfg.get("service_defaults") or {}
    name = service_name(appt)
    for key, val in defaults.items():
        if key != "*" and (key.lower() == name.lower() or re.search(key, name, re.I)) and val.get("description"):
            return str(val["description"])
    if procs:
        names = []
        for p in procs:
            d = table.get(p.code)
            if d and d not in names:
                names.append(d)
        if names:
            return "; ".join(names)
    star = defaults.get("*") or {}
    return str(star.get("description") or name or "Physical Therapy Visit")


def provider_for(appt: Optional[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, str]:
    email = str((appt or {}).get("PractitionerEmail") or "").lower()
    by_email = {k.lower(): v for k, v in (cfg.get("providers_by_email") or {}).items()}
    prov = dict(cfg.get("default_provider") or {})
    if email and email in by_email:
        prov.update(by_email[email])
    if not prov.get("name") and appt:
        prov["name"] = str(appt.get("PractitionerName") or "")
    return prov


def _active_diagnosis_codes(rows: List[Dict[str, Any]]) -> List[str]:
    active = [r for r in rows if not r.get("EndDate")] or rows
    active.sort(key=lambda r: str(r.get("Date") or ""), reverse=True)
    out: List[str] = []
    for r in active:
        code = str(r.get("Code") or "").strip()
        if code and code not in out:
            out.append(code)
    return out


def _address(profile: Dict[str, Any]) -> str:
    parts = [profile.get("StreetAddress"), profile.get("UnitNumber")]
    line1 = " ".join(str(p) for p in parts if p)
    city = ", ".join(str(p) for p in (profile.get("City"), profile.get("StateShort")) if p)
    line2 = " ".join(str(p) for p in (city, profile.get("PostalCode")) if p)
    joined = ", ".join(p for p in (line1, line2) if p)
    return joined or str(profile.get("Address") or "")


def _item_amount(item: Dict[str, Any]) -> float:
    for key in ("TotalAmount", "Amount"):
        if item.get(key) not in (None, ""):
            try:
                return float(item[key])
            except (TypeError, ValueError):
                pass
    try:
        return float(item.get("Price") or 0) * float(item.get("Units") or item.get("Quantity") or 1)
    except (TypeError, ValueError):
        return 0.0


def _prorated_invoice_amount(
    inv: Dict[str, Any], total: float, remaining_visits: int, cfg: Dict[str, Any]
) -> "tuple[float, int]":
    """Amount of one invoice that belongs on the superbill. A prepaid package item (description
    matches ``package_pattern``, e.g. "12-Visit Package") counts only for the visits used so far:
    item amount / visits in the package x visits used. Other items count in full. Returns the
    counted amount and the package visits still to allocate to later invoices."""
    items = inv.get("Items") or []
    pattern = cfg.get("package_pattern") or r"(?i)(\d+)\s*-?\s*visit"
    package_total = 0.0
    counted_packages = 0.0
    for item in items:
        m = re.search(pattern, str(item.get("Description") or ""))
        if not m or int(m.group(1)) <= 0:
            continue
        try:
            qty = max(1, int(float(item.get("Units") or item.get("Quantity") or 1)))
        except (TypeError, ValueError):
            qty = 1
        visits = int(m.group(1)) * qty
        amount = _item_amount(item)
        used = min(visits, remaining_visits)
        remaining_visits -= used
        package_total += amount
        counted_packages += amount / visits * used
    if package_total <= 0:
        return total, remaining_visits
    return round(total - package_total + counted_packages, 2), remaining_visits


# ---- main entry --------------------------------------------------------------------------

def build_superbill(
    api: SuperbillAPI,
    client_id: int,
    cfg: Dict[str, Any],
    now: Optional[datetime] = None,
    seed_appointment: Optional[Dict[str, Any]] = None,
) -> Optional[SuperbillData]:
    """Fetch everything for one client and compute the superbill. Returns None when the client
    has no completed, billable visit in the episode."""
    tz = ZoneInfo(cfg["timezone"])
    now = (now or datetime.now(tz)).astimezone(tz)
    today = now.date()

    profile = api.client_profile(client_id) or {}
    search = str(profile.get("Email") or (seed_appointment or {}).get("ClientEmail") or profile.get("Name") or (seed_appointment or {}).get("ClientName") or "")
    if not search:
        return None

    window_days = int(cfg["episode"]["rolling_days"])
    window_start = today - timedelta(days=window_days)
    appts = api.appointments_for_client(client_id, search, window_start.isoformat(), (today + timedelta(days=1)).isoformat())
    completed = [a for a in appts if is_completed(a, now, cfg, tz)]
    completed.sort(key=lambda a: int(a.get("StartDate") or 0))
    if not completed:
        return None

    # episode start: most recent evaluation-type visit, if configured
    start_pat = cfg["episode"].get("start_service_pattern")
    episode_start_dt = appointment_start(completed[0], tz)
    if start_pat:
        for a in reversed(completed):
            if re.search(start_pat, service_name(a)):
                episode_start_dt = appointment_start(a, tz)
                break
    episode_start = (episode_start_dt or now).date()

    list_prices: Optional[Dict[str, float]] = None
    if cfg.get("zero_price_uses_list_price", True) and any(charge_for(a) <= 0 for a in completed):
        list_prices = api.service_list_prices()

    lines: List[Line] = []
    package_visits = 0  # $0 visits priced from the list price, i.e. covered by a prepaid package
    for a in completed:
        start = appointment_start(a, tz)
        if not start or start.date() < episode_start:
            continue
        procs = procedures_for(a, cfg)
        charge = charge_for(a, list_prices)
        if charge <= 0 and not cfg.get("include_zero_charge"):
            continue
        if charge > 0 and charge_for(a) <= 0:
            package_visits += 1
        lines.append(Line(start.date(), description_for(a, procs, cfg), procs, charge, str(a.get("Id") or "")))
    if not lines:
        return None

    total_charges = round(sum(l.charge for l in lines), 2)

    inv_from = episode_start - timedelta(days=int(cfg["episode"]["invoice_lookback_days"]))
    invoices = api.invoices_for_client(client_id, inv_from.isoformat())
    statuses = set(cfg["invoice_statuses"])
    billed = paid = 0.0
    payment_plan = False
    installments = 0
    numbers: List[int] = []
    inv_dx: List[str] = []
    kept = sorted(
        (inv for inv in invoices if str(inv.get("Status")) in statuses),
        key=lambda inv: float(inv.get("IssuedDate") or inv.get("DateCreated") or 0),
    )
    remaining_package_visits = package_visits
    for inv in kept:
        total = float(inv.get("TotalAmount") or 0)
        counted = total
        # payment-plan installments are already spread over time, so they count as invoiced
        if cfg.get("prorate_packages", True) and not inv.get("ClientPaymentPlanId"):
            counted, remaining_package_visits = _prorated_invoice_amount(inv, total, remaining_package_visits, cfg)
        billed += counted
        inv_paid = float(inv.get("AmountPaid") or 0)
        paid += inv_paid * (counted / total) if total > 0 else inv_paid
        if inv.get("ClientPaymentPlanId"):
            payment_plan = True
            installments += 1
        if inv.get("Number") is not None:
            numbers.append(int(inv["Number"]))
        for dx in inv.get("DiagnosisList") or []:
            if dx and dx not in inv_dx:
                inv_dx.append(str(dx))
    billed, paid = round(billed, 2), round(paid, 2)

    dx_codes = _active_diagnosis_codes(api.diagnoses(client_id)) or inv_dx

    last = completed[-1]
    dob = _parse_dob(profile.get("DateOfBirth"), tz) or _parse_dob(last.get("ClientDateOfBirth"), tz)
    name = str(profile.get("Name") or last.get("ClientName") or "").strip()

    return SuperbillData(
        client_id=client_id,
        client_name=name,
        client_dob=dob,
        client_address=_address(profile),
        client_phone=str(profile.get("MobilePhone") or profile.get("Phone") or last.get("ClientPhone") or ""),
        client_email=str(profile.get("Email") or last.get("ClientEmail") or ""),
        diagnosis_codes=dx_codes,
        provider=provider_for(last, cfg),
        lines=lines,
        total_charges=total_charges,
        total_billed=billed,
        total_payments=paid,
        provider_discount=round(max(0.0, total_charges - billed), 2),
        balance=round(billed - paid, 2),
        payment_plan=payment_plan,
        installments_billed=installments,
        episode_start=lines[0].date,
        episode_end=lines[-1].date,
        statement_date=today,
        invoice_numbers=sorted(numbers),
    )
