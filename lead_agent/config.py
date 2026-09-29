"""Configuration: non-secret practice settings from agent_config.json, secrets from env."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

DEFAULT_CONFIG_PATH = os.environ.get("LEAD_AGENT_CONFIG", "agent_config.json")


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
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


@dataclass
class Secrets:
    anthropic_api_key: str = ""
    ghl_token: str = ""
    ghl_location_id: str = ""
    ghl_calendar_id: str = ""
    ghl_sms_from_number: str = ""
    ghl_webhook_secret: str = ""
    retell_api_key: str = ""
    retell_agent_id: str = ""
    retell_from_number: str = ""
    public_base_url: str = ""
    admin_secret: str = ""
    db_path: str = "lead_agent.sqlite3"
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "Secrets":
        e = os.environ.get
        return cls(
            anthropic_api_key=e("ANTHROPIC_API_KEY", ""),
            ghl_token=e("GHL_TOKEN", ""),
            ghl_location_id=e("GHL_LOCATION_ID", ""),
            ghl_calendar_id=e("GHL_CALENDAR_ID", ""),
            ghl_sms_from_number=e("GHL_SMS_FROM_NUMBER", ""),
            ghl_webhook_secret=e("GHL_WEBHOOK_SECRET", ""),
            retell_api_key=e("RETELL_API_KEY", ""),
            retell_agent_id=e("RETELL_AGENT_ID", ""),
            retell_from_number=e("RETELL_FROM_NUMBER", ""),
            public_base_url=e("PUBLIC_BASE_URL", "").rstrip("/"),
            admin_secret=e("ADMIN_SECRET", ""),
            db_path=e("LEAD_AGENT_DB", "lead_agent.sqlite3"),
            dry_run=e("LEAD_AGENT_DRY_RUN", "0") in ("1", "true", "yes"),
        )

    def missing(self, voice: bool = False) -> list[str]:
        need = ["ANTHROPIC_API_KEY", "GHL_TOKEN", "GHL_LOCATION_ID", "GHL_CALENDAR_ID", "GHL_WEBHOOK_SECRET"]
        if voice:
            need += ["RETELL_API_KEY", "RETELL_AGENT_ID", "RETELL_FROM_NUMBER", "PUBLIC_BASE_URL"]
        env = os.environ
        return [n for n in need if not env.get(n)]


@dataclass
class Config:
    """Practice-level, non-secret configuration. See agent_config.json for the schema."""

    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> "Config":
        with open(path) as f:
            return cls(json.load(f))

    # --- practice ---
    @property
    def practice(self) -> dict[str, Any]:
        return self.raw.get("practice", {})

    @property
    def timezone(self) -> str:
        return self.practice.get("timezone", "America/New_York")

    @property
    def agent_name(self) -> str:
        return self.practice.get("agent_name", "Maya")

    # --- hours ---
    @property
    def business_hours(self) -> dict[str, list[str] | None]:
        return self.raw.get("hours", {}).get("business", {})

    @property
    def quiet_hours(self) -> list[str]:
        return self.raw.get("hours", {}).get("quiet", ["21:00", "08:00"])

    @property
    def call_window(self) -> list[str]:
        return self.raw.get("hours", {}).get("call_window", ["09:00", "20:00"])

    @property
    def holidays(self) -> list[str]:
        return self.raw.get("hours", {}).get("holidays", [])

    # --- busy mode ---
    @property
    def busy(self) -> dict[str, Any]:
        return self.raw.get("busy_mode", {})

    @property
    def busy_after_minutes_unanswered(self) -> int:
        return int(self.busy.get("auto_after_minutes_unanswered", 5))

    # --- cadence ---
    @property
    def cadence(self) -> list[dict[str, Any]]:
        return self.raw.get("cadence", {}).get("initial", [])

    @property
    def silent_cadence(self) -> list[dict[str, Any]]:
        return self.raw.get("cadence", {}).get("after_reply_silence", [])

    @property
    def max_calls(self) -> int:
        return int(self.raw.get("cadence", {}).get("max_calls", 2))

    @property
    def max_sms(self) -> int:
        return int(self.raw.get("cadence", {}).get("max_sms", 6))

    # --- tags / stop rules ---
    @property
    def tags(self) -> dict[str, str]:
        base = {
            "active": "ai-agent-active",
            "stop": "ai-agent-stop",
            "booked": "ai-agent-booked",
            "handoff": "ai-agent-handoff",
            "paused_human": "ai-agent-paused-human",
            "opted_out": "ai-agent-opted-out",
            "not_interested": "ai-agent-not-interested",
            "consent": "",
        }
        base.update(self.raw.get("tags", {}))
        return base

    @property
    def stop_tags(self) -> list[str]:
        return list(self.raw.get("stop_rules", {}).get("skip_if_tagged", [self.tags["stop"]]))

    @property
    def skip_sources(self) -> list[str]:
        return [s.lower() for s in self.raw.get("stop_rules", {}).get("skip_sources", [])]

    # --- models ---
    @property
    def sms_model(self) -> str:
        return self.raw.get("models", {}).get("sms", "claude-opus-5-5")

    @property
    def sms_effort(self) -> str:
        return self.raw.get("models", {}).get("sms_effort", "medium")

    # --- calendar ---
    @property
    def slot_search_days(self) -> int:
        return int(self.raw.get("calendar", {}).get("search_days", 7))

    @property
    def appointment_title(self) -> str:
        return self.raw.get("calendar", {}).get("appointment_title", "{inquiry_call_name} with {name}")

    @property
    def appointment_minutes(self) -> int:
        return int(self.practice.get("inquiry_call_minutes", 15))

    # --- voice ---
    @property
    def voice(self) -> dict[str, Any]:
        return self.raw.get("voice", {})
