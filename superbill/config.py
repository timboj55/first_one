"""Practice, provider and rendering settings from superbill_config.json; secrets from env."""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict

DEFAULT_CONFIG_PATH = os.environ.get("SUPERBILL_CONFIG", "superbill_config.json")

DEFAULTS: Dict[str, Any] = {
    "timezone": "America/New_York",
    "practice": {
        "name": "Practice Name, LLC",
        "address_lines": [],
        "phone": "",
        "ein": "",
        "place_of_service_code": "11",
        "place_of_service_name": "Office",
    },
    "default_provider": {"name": "", "credentials": "", "license": "", "npi": "", "taxonomy": ""},
    "providers_by_email": {},
    "completed_statuses": ["Confirmed"],
    "include_zero_charge": False,
    # $0 visits (package-covered) are charged at the service's PracticeQ list price.
    "zero_price_uses_list_price": True,
    # Prepaid packages ("12-Visit Package") count only for the visits used: item / visits x used.
    "prorate_packages": True,
    "package_pattern": r"(?i)(\d+)\s*-?\s*visit",
    "exclude_service_patterns": [],
    "episode": {
        "rolling_days": 365,
        "start_service_pattern": None,
        "invoice_lookback_days": 45,
    },
    "invoice_statuses": ["Paid", "Unpaid", "PastDue"],
    "procedure_descriptions": {},
    "service_defaults": {},
    "file": {"name_format": "Superbill - {name}.pdf", "replace_prefix": "Superbill - "},
    "sync": {"lookback_days": 3, "state_path": ""},
    "text": {
        "title": "SUPERBILL",
        "subtitle": "Itemized statement of services for insurance reimbursement",
        "paid_in_full": (
            "This patient has paid in full for the services listed above. {practice} is NOT an "
            "insurance provider for this claim and has not been paid by any insurer."
        ),
        "payment_plan": (
            "This patient is paying for the services listed above under a payment plan with "
            "{practice}. Payments received to date: {paid}. {practice} is NOT an insurance "
            "provider for this claim and has not been paid by any insurer."
        ),
        "balance_due": (
            "This patient has paid {paid} toward the services listed above; {balance} remains "
            "due to {practice}. {practice} is NOT an insurance provider for this claim and has "
            "not been paid by any insurer."
        ),
        "reimburse_line": "PLEASE PROVIDE ANY PAYMENT DIRECTLY TO THE PATIENT.",
    },
}


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> Dict[str, Any]:
    path = path or DEFAULT_CONFIG_PATH
    data: Dict[str, Any] = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    return _merge(DEFAULTS, data)


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader (no dependency). Existing env vars win."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
