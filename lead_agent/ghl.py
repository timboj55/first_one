"""GoHighLevel (LeadConnector) API v2 client. Stdlib only.

Auth: a Private Integration Token (Settings > Private Integrations) or an OAuth access token,
sent as `Authorization: Bearer`. Calendar/contact endpoints use Version 2021-07-28;
conversation endpoints use 2021-04-15.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

log = logging.getLogger("lead_agent.ghl")

BASE = "https://services.leadconnectorhq.com"
V_DEFAULT = "2021-07-28"
V_CONVERSATIONS = "2021-04-15"


class GHLError(RuntimeError):
    def __init__(self, status: int, body: str, path: str):
        super().__init__(f"GHL {status} on {path}: {body[:400]}")
        self.status = status
        self.body = body


class GHLClient:
    def __init__(self, token: str, location_id: str, dry_run: bool = False):
        self.token = token
        self.location_id = location_id
        self.dry_run = dry_run

    # ---------------- low level ----------------
    def _req(self, method: str, path: str, *, params: dict | None = None, body: dict | None = None,
             version: str = V_DEFAULT, retries: int = 3) -> Any:
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        last: Exception | None = None
        for attempt in range(retries):
            req = urllib.request.Request(url, method=method, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                txt = e.read().decode(errors="replace")
                if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    last = GHLError(e.code, txt, path)
                    continue
                raise GHLError(e.code, txt, path) from None
            except urllib.error.URLError as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"GHL request failed after retries: {last}")

    # ---------------- contacts ----------------
    def get_contact(self, contact_id: str) -> dict[str, Any]:
        r = self._req("GET", f"/contacts/{contact_id}")
        return r.get("contact", r)

    def add_tags(self, contact_id: str, tags: list[str]) -> None:
        tags = [t for t in tags if t]
        if not tags:
            return
        if self.dry_run:
            log.info("[dry-run] add tags %s to %s", tags, contact_id)
            return
        self._req("POST", f"/contacts/{contact_id}/tags", body={"tags": tags})

    def remove_tags(self, contact_id: str, tags: list[str]) -> None:
        tags = [t for t in tags if t]
        if not tags:
            return
        if self.dry_run:
            log.info("[dry-run] remove tags %s from %s", tags, contact_id)
            return
        self._req("DELETE", f"/contacts/{contact_id}/tags", body={"tags": tags})

    def add_note(self, contact_id: str, body: str) -> None:
        if self.dry_run:
            log.info("[dry-run] note on %s: %s", contact_id, body[:120])
            return
        self._req("POST", f"/contacts/{contact_id}/notes", body={"body": body[:5000]})

    def update_contact(self, contact_id: str, **fields: Any) -> None:
        if self.dry_run:
            log.info("[dry-run] update %s: %s", contact_id, fields)
            return
        self._req("PUT", f"/contacts/{contact_id}", body=fields)

    # ---------------- conversations / SMS ----------------
    def send_sms(self, contact_id: str, message: str, from_number: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"type": "SMS", "contactId": contact_id, "message": message}
        if from_number:
            body["fromNumber"] = from_number
        if self.dry_run:
            log.info("[dry-run] SMS to %s: %s", contact_id, message)
            return {"conversationId": "dry", "messageId": f"dry-{int(time.time()*1000)}"}
        return self._req("POST", "/conversations/messages", body=body, version=V_CONVERSATIONS)

    def find_conversation_id(self, contact_id: str) -> Optional[str]:
        r = self._req("GET", "/conversations/search", params={"locationId": self.location_id, "contactId": contact_id},
                      version=V_CONVERSATIONS)
        convs = r.get("conversations") or []
        return convs[0].get("id") if convs else None

    def recent_messages(self, conversation_id: str, limit: int = 30) -> list[dict[str, Any]]:
        r = self._req("GET", f"/conversations/{conversation_id}/messages", params={"limit": limit}, version=V_CONVERSATIONS)
        msgs = r.get("messages", r)
        if isinstance(msgs, dict):
            msgs = msgs.get("messages", [])
        return msgs or []

    # ---------------- calendar ----------------
    def free_slots(self, calendar_id: str, start: datetime, end: datetime, timezone: str,
                   user_id: str | None = None) -> list[str]:
        """Return ISO slot start times between start and end (both tz-aware)."""
        params = {
            "startDate": int(start.timestamp() * 1000),
            "endDate": int(end.timestamp() * 1000),
            "timezone": timezone,
        }
        if user_id:
            params["userId"] = user_id
        r = self._req("GET", f"/calendars/{calendar_id}/free-slots", params=params)
        slots: list[str] = []
        for key, val in r.items():
            if key == "traceId" or not isinstance(val, dict):
                continue
            slots.extend(val.get("slots") or [])
        return sorted(slots)

    def create_appointment(self, calendar_id: str, contact_id: str, start_iso: str, end_iso: str | None,
                           title: str, assigned_user_id: str | None = None, ignore_free_slot_validation: bool = False) -> dict[str, Any]:
        body: dict[str, Any] = {
            "calendarId": calendar_id,
            "locationId": self.location_id,
            "contactId": contact_id,
            "startTime": start_iso,
            "title": title,
            "appointmentStatus": "confirmed",
            "ignoreFreeSlotValidation": ignore_free_slot_validation,
            "toNotify": True,
        }
        if end_iso:
            body["endTime"] = end_iso
        if assigned_user_id:
            body["assignedUserId"] = assigned_user_id
        if self.dry_run:
            log.info("[dry-run] book %s at %s", contact_id, start_iso)
            return {"id": f"dry-appt-{int(time.time())}", "startTime": start_iso}
        return self._req("POST", "/calendars/events/appointments", body=body)

    def contact_appointments(self, contact_id: str) -> list[dict[str, Any]]:
        r = self._req("GET", f"/contacts/{contact_id}/appointments")
        return r.get("events") or []


# ---------------- helpers shared by SMS brain and voice tools ----------------

def slot_end(start_iso: str, minutes: int) -> str:
    dt = datetime.fromisoformat(start_iso)
    return (dt + timedelta(minutes=minutes)).isoformat()


def humanize_slot(iso: str, zone: ZoneInfo) -> str:
    dt = datetime.fromisoformat(iso).astimezone(zone)
    hour = dt.strftime("%I:%M %p").lstrip("0").replace(":00", "")
    return f"{dt.strftime('%A %b')} {dt.day} at {hour}"


def pick_offer(slots: list[str], zone: ZoneInfo, now: datetime, max_offer: int = 6, min_lead_minutes: int = 60) -> list[str]:
    """Spread offered slots across days/times so the lead sees variety, not six 9:00s."""
    cutoff = now + timedelta(minutes=min_lead_minutes)
    usable = [s for s in slots if datetime.fromisoformat(s).astimezone(zone) >= cutoff]
    by_day: dict[str, list[str]] = {}
    for s in usable:
        by_day.setdefault(datetime.fromisoformat(s).astimezone(zone).date().isoformat(), []).append(s)
    out: list[str] = []
    for day, day_slots in sorted(by_day.items()):
        if len(out) >= max_offer:
            break
        # morning + afternoon pick from each day
        am = [s for s in day_slots if datetime.fromisoformat(s).astimezone(zone).hour < 12]
        pm = [s for s in day_slots if datetime.fromisoformat(s).astimezone(zone).hour >= 12]
        for bucket in (am, pm):
            if bucket and len(out) < max_offer:
                out.append(bucket[len(bucket) // 2])
    return out
