"""Lead lifecycle: when to engage, what to send, when to call, when to stop.

Engagement policy
  - After hours (outside business hours or a holiday): engage immediately.
  - Busy mode on (admin toggle or config always_on): engage immediately.
  - Business hours otherwise: wait `busy_mode.auto_after_minutes_unanswered`; if no team member
    has touched the lead by then, the team is busy and the agent engages.
  - Every outbound step re-checks: stop tags, DND, an appointment already on the calendar, and
    whether a human has messaged the lead (then the agent pauses and hands the thread over).
  - Nothing goes out during quiet hours; calls only inside the call window. Both are evaluated
    in the lead's timezone when GHL knows it, else the practice's.

Cadence
  - `cadence.initial`: ordered touches for a lead who has not replied (sms / call), each with a
    delay from the previous touch. Capped by max_sms / max_calls.
  - `cadence.after_reply_silence`: nudges for a lead who replied and then went quiet.
  - Any inbound text cancels pending touches; the conversation becomes live.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from .brain import Brain, BrainError
from .config import Config, Secrets
from .db import Store
from .ghl import GHLClient, humanize_slot
from .hours import Clock, in_window, is_business_hours, is_quiet, next_allowed, tz
from .tools import Tools
from .voice import NOT_REACHED, RetellClient, contact_id_from_call, summarize_call

log = logging.getLogger("lead_agent.orchestrator")

TERMINAL = {"booked", "stopped", "opted_out", "not_interested", "handoff", "paused_human", "wrong_number", "existing_patient", "done"}


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def normalize_lead(payload: dict[str, Any]) -> dict[str, Any]:
    """Tolerant mapping of a GHL workflow webhook payload (or our own simulate payload)."""
    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else {}
    custom = payload.get("customData") if isinstance(payload.get("customData"), dict) else {}
    src: dict[str, Any] = {**contact, **payload, **custom}
    first = _first(src, "first_name", "firstName", default="") or ""
    last = _first(src, "last_name", "lastName", default="") or ""
    name = _first(src, "full_name", "name", "contact_name", default=f"{first} {last}".strip())
    lead = {
        "contact_id": _first(src, "contact_id", "contactId", "id"),
        "first_name": first or (name.split(" ")[0] if name else ""),
        "last_name": last,
        "name": name,
        "phone": _first(src, "phone", "phone_number", default=""),
        "email": _first(src, "email", default=""),
        "source": _first(src, "contact_source", "source", "lead_source", default=""),
        "timezone": _first(src, "timezone", "time_zone", default=None),
        "tags": src.get("tags") if isinstance(src.get("tags"), list) else (src.get("tags", "").split(",") if isinstance(src.get("tags"), str) else []),
        "service_interest": _first(src, "service_interest", "interest", "reason", "what_are_you_reaching_out_about", "What are you reaching out about?", default=""),
        "message_body": _first(src, "message_body", "lead_message", "message", default=""),
        "location_id": (payload.get("location") or {}).get("id") if isinstance(payload.get("location"), dict) else _first(src, "location_id", "locationId", default=None),
    }
    if isinstance(lead["message_body"], dict):  # Customer Replied payloads nest {message: {body}}
        lead["message_body"] = lead["message_body"].get("body", "")
    lead["tags"] = [t.strip() for t in lead["tags"] if isinstance(t, str) and t.strip()]
    return lead


def normalize_inbound(payload: dict[str, Any]) -> dict[str, Any]:
    lead = normalize_lead(payload)
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    custom = payload.get("customData") if isinstance(payload.get("customData"), dict) else {}
    body = _first(custom, "message_body", default=None) or _first(msg, "body", "message", default=None) or _first(payload, "body", "message_body", default="")
    mtype = (_first(custom, "message_type", default=None) or _first(msg, "type", "messageType", default="") or _first(payload, "type", "message_type", default="") or "")
    direction = (_first(msg, "direction", default="") or _first(payload, "direction", default="") or "inbound")
    return {
        **lead,
        "body": body if isinstance(body, str) else str(body),
        "message_type": str(mtype),
        "message_id": _first(custom, "message_id", default=None) or _first(msg, "id", "messageId", default=None) or _first(payload, "message_id", "messageId", default=None),
        "direction": str(direction).lower(),
    }


class Orchestrator:
    def __init__(self, cfg: Config, secrets: Secrets, store: Store, ghl: GHLClient, brain: Brain,
                 retell: RetellClient | None = None, clock: Clock | None = None):
        self.cfg = cfg
        self.secrets = secrets
        self.store = store
        self.ghl = ghl
        self.brain = brain
        self.retell = retell
        self.clock = clock or Clock()
        self.practice_zone = tz(cfg.timezone, "UTC")

    # ------------------------------------------------------------------ helpers
    def zone_for(self, conv: dict[str, Any]):
        return tz(conv.get("timezone"), self.cfg.timezone)

    def now_text(self, conv: dict[str, Any]) -> str:
        now = self.clock.now(self.zone_for(conv))
        return now.strftime("%a %b %d, %I:%M %p %Z").replace(" 0", " ")

    def busy_mode(self) -> bool:
        if self.cfg.busy.get("always_on"):
            return True
        return self.store.get_setting("busy_mode", "0") == "1"

    def set_busy(self, on: bool) -> None:
        self.store.set_setting("busy_mode", "1" if on else "0")
        self.store.log(None, "busy_mode", on=on)

    def engagement_delay_minutes(self, now: datetime) -> int:
        """0 = engage now. Otherwise wait this long and re-check that the team hasn't responded."""
        if not is_business_hours(now, self.cfg.business_hours, self.cfg.holidays):
            return 0
        if self.busy_mode():
            return 0
        return self.cfg.busy_after_minutes_unanswered

    def _tools(self, conv: dict[str, Any]) -> Tools:
        def on_status(status: str, outcome: str, data: dict[str, Any]) -> None:
            self._transition(conv["contact_id"], status, outcome, data)
        return Tools(self.cfg, self.ghl, self.store, self.secrets.ghl_calendar_id, conv["contact_id"], conv["lead"],
                     clock=self.clock, on_status=on_status, assigned_user_id=self.cfg.raw.get("calendar", {}).get("assigned_user_id"))

    def _transition(self, contact_id: str, status: str, outcome: str, data: dict[str, Any]) -> None:
        fields: dict[str, Any] = {"outcome": outcome}
        if status == "callback_requested":
            # not terminal: the team owns the callback; we stop automated touches but keep replying
            self.store.cancel_jobs(contact_id, ["cadence", "nudge", "call"])
            self.ghl.add_tags(contact_id, [self.cfg.tags["handoff"]])
            fields["status"] = "handoff"
        else:
            fields["status"] = status if status in TERMINAL else "active"
            if fields["status"] in TERMINAL:
                self.store.cancel_jobs(contact_id)
        if "appointment_id" in data:
            fields["appointment_id"] = data["appointment_id"]
        self.store.update_conversation(contact_id, **fields)
        self.store.log(contact_id, "status", status=fields["status"], outcome=outcome, **data)

    # ------------------------------------------------------------------ guards
    def _refresh_contact(self, conv: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.ghl.get_contact(conv["contact_id"])
        except Exception as e:
            log.warning("contact refresh failed for %s: %s", conv["contact_id"], e)
            return {}

    def _dnd(self, contact: dict[str, Any], channel: str) -> bool:
        if contact.get("dnd"):
            return True
        s = (contact.get("dndSettings") or {}).get(channel) or {}
        return s.get("status") in ("active", "permanent")

    def _stop_reason(self, conv: dict[str, Any], contact: dict[str, Any], channel: str) -> Optional[str]:
        tags = [t.lower() for t in (contact.get("tags") or conv["lead"].get("tags") or [])]
        for t in self.cfg.stop_tags:
            if t.lower() in tags:
                return f"tag:{t}"
        consent_tag = self.cfg.tags.get("consent")
        if consent_tag and consent_tag.lower() not in tags:
            return "no_consent_tag"
        if self._dnd(contact, "SMS" if channel == "sms" else "Call"):
            return f"dnd:{channel}"
        if conv["lead"].get("source", "").lower() in self.cfg.skip_sources:
            return "source_skipped"
        return None

    def _already_booked(self, conv: dict[str, Any]) -> bool:
        try:
            for appt in self.ghl.contact_appointments(conv["contact_id"]):
                if appt.get("calendarId") == self.secrets.ghl_calendar_id and str(appt.get("appointmentStatus", "")).lower() in ("confirmed", "new", "booked", ""):
                    start = appt.get("startTime")
                    try:
                        if start and datetime.fromisoformat(start.replace("Z", "+00:00")) < self.clock.now(self.practice_zone) - timedelta(hours=1):
                            continue
                    except ValueError:
                        pass
                    self._transition(conv["contact_id"], "booked", "booked_elsewhere", {"appointment_id": appt.get("id", "")})
                    return True
        except Exception as e:
            log.warning("appointment check failed: %s", e)
        return False

    def _human_touched(self, conv: dict[str, Any]) -> bool:
        """True if someone other than this agent sent the lead an outbound message since we started."""
        try:
            cid = conv.get("ghl_conversation_id") or self.ghl.find_conversation_id(conv["contact_id"])
            if not cid:
                return False
            if cid != conv.get("ghl_conversation_id"):
                self.store.update_conversation(conv["contact_id"], ghl_conversation_id=cid)
            for m in self.ghl.recent_messages(cid):
                if str(m.get("direction", "")).lower() != "outbound":
                    continue
                if self.store.sent_by_us(str(m.get("id", ""))):
                    continue
                added = m.get("dateAdded") or m.get("createdAt")
                try:
                    ts = datetime.fromisoformat(str(added).replace("Z", "+00:00")).timestamp() if added else None
                except ValueError:
                    ts = None
                if ts is not None and ts < conv["created_at"] - 60:
                    continue
                if (m.get("messageType") or m.get("type") or "").upper() in ("TYPE_ACTIVITY", "ACTIVITY"):
                    continue
                return True
        except Exception as e:
            log.warning("human-touch check failed: %s", e)
        return False

    def _pause_for_human(self, conv: dict[str, Any]) -> None:
        self.ghl.add_tags(conv["contact_id"], [self.cfg.tags["paused_human"]])
        self.ghl.add_note(conv["contact_id"], f"[{self.cfg.agent_name} AI] A team member messaged this lead, so the assistant paused. Remove the '{self.cfg.tags['paused_human']}' tag and re-trigger the workflow to resume.")
        self._transition(conv["contact_id"], "paused_human", "human_took_over", {})

    def _preflight(self, conv: dict[str, Any], channel: str) -> Optional[str]:
        """Run before every outbound touch. Returns a reason to skip, or None."""
        if conv["status"] not in ("active",):
            return f"status:{conv['status']}"
        contact = self._refresh_contact(conv)
        if contact:
            if contact.get("timezone") and contact["timezone"] != conv.get("timezone"):
                self.store.update_conversation(conv["contact_id"], timezone=contact["timezone"])
                conv["timezone"] = contact["timezone"]
        reason = self._stop_reason(conv, contact, channel)
        if reason:
            self._transition(conv["contact_id"], "stopped", reason, {})
            return reason
        if self._already_booked(conv):
            return "already_booked"
        if self._human_touched(conv):
            self._pause_for_human(conv)
            return "human_touched"
        return None

    # ------------------------------------------------------------------ entry: new lead
    def handle_new_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        lead = normalize_lead(payload)
        contact_id = lead.get("contact_id")
        if not contact_id:
            return {"ok": False, "error": "no contact_id in payload"}
        if self.store.seen_webhook(f"new-lead:{contact_id}", ttl_seconds=3600):
            return {"ok": True, "skipped": "duplicate"}
        existing = self.store.get_conversation(contact_id)
        if existing and existing["status"] == "active":
            return {"ok": True, "skipped": "already_active"}
        if existing and existing["status"] in TERMINAL and not payload.get("force"):
            return {"ok": True, "skipped": f"existing:{existing['status']}"}
        contact = {}
        try:
            contact = self.ghl.get_contact(contact_id)
        except Exception as e:
            log.warning("get_contact failed: %s", e)
        for k in ("firstName", "lastName", "phone", "email", "timezone", "source"):
            if contact.get(k) and not lead.get({"firstName": "first_name", "lastName": "last_name"}.get(k, k)):
                lead[{"firstName": "first_name", "lastName": "last_name"}.get(k, k)] = contact[k]
        if contact.get("tags"):
            lead["tags"] = contact["tags"]
        if not lead.get("name"):
            lead["name"] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        if not lead.get("phone"):
            self.store.log(contact_id, "skip", reason="no_phone")
            return {"ok": True, "skipped": "no_phone"}
        conv = self.store.upsert_conversation(contact_id, lead, lead.get("timezone"))
        self.store.update_conversation(contact_id, status="active", cadence_index=0, cadence_kind="initial", outcome=None, messages=[])
        conv = self.store.get_conversation(contact_id) or conv
        reason = self._stop_reason(conv, contact, "sms")
        if reason:
            self.store.update_conversation(contact_id, status="stopped", outcome=reason)
            self.store.log(contact_id, "skip", reason=reason)
            return {"ok": True, "skipped": reason}
        self.ghl.add_tags(contact_id, [self.cfg.tags["active"]])
        zone = self.zone_for(conv)
        now = self.clock.now(zone)
        delay = self.engagement_delay_minutes(self.clock.now(self.practice_zone))
        run_at = next_allowed(now + timedelta(minutes=delay), self.cfg.quiet_hours)
        job_id = self.store.schedule(contact_id, "cadence", run_at.timestamp(), {"index": 0, "kind": "initial", "check_team": delay > 0})
        self.store.log(contact_id, "new_lead", delay_minutes=delay, run_at=run_at.isoformat(), job_id=job_id, source=lead.get("source"))
        return {"ok": True, "contact_id": contact_id, "first_touch_at": run_at.isoformat(), "delay_minutes": delay}

    # ------------------------------------------------------------------ entry: inbound SMS
    def handle_inbound(self, payload: dict[str, Any]) -> dict[str, Any]:
        msg = normalize_inbound(payload)
        contact_id = msg.get("contact_id")
        if not contact_id or not msg.get("body"):
            return {"ok": False, "error": "need contact_id and message body"}
        if msg["direction"] != "inbound":
            return {"ok": True, "skipped": "not_inbound"}
        if msg["message_type"] and "SMS" not in msg["message_type"].upper() and msg["message_type"].upper() not in ("TYPE_SMS", "2"):
            return {"ok": True, "skipped": f"type:{msg['message_type']}"}
        key = f"inbound:{msg.get('message_id') or (contact_id + ':' + msg['body'][:80])}"
        if self.store.seen_webhook(key, ttl_seconds=600):
            return {"ok": True, "skipped": "duplicate"}
        conv = self.store.get_conversation(contact_id)
        if conv is None:
            if not self.cfg.raw.get("engage_on_unknown_inbound"):
                return {"ok": True, "skipped": "no_conversation"}
            res = self.handle_new_lead({**payload, "contact_id": contact_id})
            if not res.get("contact_id"):
                return res
            self.store.cancel_jobs(contact_id)  # they texted first; no opener needed
            conv = self.store.get_conversation(contact_id)
        assert conv is not None
        if conv["status"] not in ("active", "booked"):
            self.store.log(contact_id, "inbound_ignored", status=conv["status"], body=msg["body"][:200])
            return {"ok": True, "skipped": f"status:{conv['status']}"}
        self.store.cancel_jobs(contact_id, ["cadence", "nudge", "call"])
        self.store.update_conversation(contact_id, last_inbound_at=time.time())
        job_id = self.store.schedule(contact_id, "inbound", time.time(), {"body": msg["body"], "message_id": msg.get("message_id")})
        self.store.log(contact_id, "inbound", body=msg["body"][:500], job_id=job_id)
        return {"ok": True, "queued": job_id}

    # ------------------------------------------------------------------ entry: booked elsewhere
    def handle_appointment_booked(self, payload: dict[str, Any]) -> dict[str, Any]:
        lead = normalize_lead(payload)
        contact_id = lead.get("contact_id")
        if not contact_id:
            return {"ok": False, "error": "no contact_id"}
        conv = self.store.get_conversation(contact_id)
        if not conv or conv["status"] in TERMINAL:
            return {"ok": True, "skipped": "no_active_conversation"}
        appt_id = _first(payload, "appointment_id", "appointmentId", default="") or (payload.get("appointment") or {}).get("id", "")
        self._transition(contact_id, "booked", "booked_elsewhere", {"appointment_id": appt_id})
        self.ghl.add_tags(contact_id, [self.cfg.tags["booked"]])
        return {"ok": True, "status": "booked"}

    # ------------------------------------------------------------------ jobs
    def run_job(self, job: dict[str, Any]) -> None:
        kind = job["kind"]
        conv = self.store.get_conversation(job["contact_id"])
        if conv is None:
            return
        if kind == "cadence":
            self._run_cadence(conv, job)
        elif kind == "inbound":
            self._run_inbound(conv, job)
        elif kind == "nudge":
            self._run_nudge(conv, job)
        elif kind == "missed_call_sms":
            self._send_event_sms(conv, job["payload"].get("event", "You tried calling and could not reach the lead. Send one short 'sorry I missed you' text and offer two times or ask what works."), count_toward_cadence=True)
        elif kind == "callback_sms":
            self._send_event_sms(conv, job["payload"].get("event", ""), count_toward_cadence=False)
        else:
            log.warning("unknown job kind %s", kind)

    def _run_cadence(self, conv: dict[str, Any], job: dict[str, Any]) -> None:
        payload = job["payload"]
        index = int(payload.get("index", conv.get("cadence_index", 0)))
        steps = self.cfg.cadence
        if conv["status"] != "active":
            return
        if index >= len(steps):
            self._transition(conv["contact_id"], "done", "no_response", {})
            self.ghl.add_note(conv["contact_id"], f"[{self.cfg.agent_name} AI] No response after {conv['sms_sent']} texts and {conv['calls_placed']} calls. Outreach ended.")
            return
        step = steps[index]
        channel = step.get("channel", "sms")
        zone = self.zone_for(conv)
        now = self.clock.now(zone)
        practice_now = self.clock.now(self.practice_zone)
        # Business hours and not busy: the team owns the lead unless they've been silent past the busy threshold.
        if payload.get("check_team") and is_business_hours(practice_now, self.cfg.business_hours, self.cfg.holidays) and not self.busy_mode():
            if self._human_touched(conv):
                self._transition(conv["contact_id"], "stopped", "team_handled", {})
                self.store.log(conv["contact_id"], "skip", reason="team_handled_in_time")
                return
        # Quiet hours / call window: defer this same step.
        window = self.cfg.call_window if channel == "call" else None
        allowed = next_allowed(now, self.cfg.quiet_hours, window)
        if allowed > now + timedelta(minutes=1):
            self.store.schedule(conv["contact_id"], "cadence", allowed.timestamp(), {**payload, "deferred": True})
            self.store.log(conv["contact_id"], "deferred", step=index, channel=channel, until=allowed.isoformat())
            return
        reason = self._preflight(conv, channel)
        if reason:
            self.store.log(conv["contact_id"], "skip", step=index, reason=reason)
            return
        conv = self.store.get_conversation(conv["contact_id"]) or conv
        did = False
        if channel == "sms":
            if conv["sms_sent"] < self.cfg.max_sms:
                event = step.get("event") or ("Send the first outreach text to this lead now." if index == 0 else "The lead has not replied to earlier outreach. Send one short, friendly follow-up with a fresh angle or a new time. Do not repeat the previous wording.")
                did = self._send_event_sms(conv, event, count_toward_cadence=True)
            else:
                self.store.log(conv["contact_id"], "skip", step=index, reason="max_sms")
        elif channel == "call":
            if conv["calls_placed"] < self.cfg.max_calls and self.retell is not None and self.secrets.retell_agent_id:
                did = self.place_call(conv)
            else:
                self.store.log(conv["contact_id"], "skip", step=index, reason="max_calls_or_voice_disabled")
        # Schedule the next step regardless (a skipped step should not stall the sequence).
        next_index = index + 1
        self.store.update_conversation(conv["contact_id"], cadence_index=next_index)
        if next_index < len(steps):
            delay = int(steps[next_index].get("delay_minutes", 60))
            if channel == "call" and did:
                delay = max(delay, int(self.cfg.raw.get("cadence", {}).get("min_minutes_after_call", 10)))
            run_at = next_allowed(self.clock.now(zone) + timedelta(minutes=delay), self.cfg.quiet_hours)
            self.store.schedule(conv["contact_id"], "cadence", run_at.timestamp(), {"index": next_index, "kind": "initial"})
        else:
            self.store.schedule(conv["contact_id"], "cadence", (self.clock.now(zone) + timedelta(minutes=int(self.cfg.raw.get("cadence", {}).get("close_after_minutes", 2880)))).timestamp(), {"index": next_index, "kind": "initial"})

    def _send_event_sms(self, conv: dict[str, Any], event: str, count_toward_cadence: bool) -> bool:
        conv = self.store.get_conversation(conv["contact_id"]) or conv
        if conv["status"] not in ("active", "handoff", "booked"):
            return False
        tools = self._tools(conv)
        lead_ctx = self._lead_context(conv)
        result = self.brain.turn(conv["messages"], tools, event=f"{event} {lead_ctx} Current time: {self.now_text(conv)}.".strip(), now_text="")
        self.store.update_conversation(conv["contact_id"], messages=result.messages)
        if not result.reply:
            self.store.log(conv["contact_id"], "no_reply", event=event[:120], stop=result.stop_reason)
            return False
        self._send(conv, result.reply)
        if count_toward_cadence:
            self.store.bump(conv["contact_id"], "sms_sent")
        return True

    def _lead_context(self, conv: dict[str, Any]) -> str:
        lead = conv["lead"]
        bits = []
        if lead.get("first_name"):
            bits.append(f"Lead first name: {lead['first_name']}.")
        if lead.get("service_interest"):
            bits.append(f"They reached out about: {lead['service_interest']}.")
        if lead.get("message_body"):
            bits.append(f"Their form message: \"{str(lead['message_body'])[:300]}\".")
        if lead.get("source"):
            bits.append(f"Source: {lead['source']}.")
        return " ".join(bits)

    def _send(self, conv: dict[str, Any], text: str) -> None:
        res = self.ghl.send_sms(conv["contact_id"], text, self.secrets.ghl_sms_from_number or None)
        mid = str(res.get("messageId") or "")
        self.store.record_sent(mid, conv["contact_id"])
        fields: dict[str, Any] = {"last_outbound_at": time.time()}
        if res.get("conversationId"):
            fields["ghl_conversation_id"] = res["conversationId"]
        self.store.update_conversation(conv["contact_id"], **fields)
        self.store.log(conv["contact_id"], "sms_out", text=text, message_id=mid)

    def _run_inbound(self, conv: dict[str, Any], job: dict[str, Any]) -> None:
        body = job["payload"].get("body", "")
        if conv["status"] not in ("active", "booked", "handoff"):
            return
        if conv["status"] == "active" and self._human_touched(conv):
            self._pause_for_human(conv)
            return
        tools = self._tools(conv)
        first_turn = not conv["messages"]
        event = None
        if first_turn:
            event = f"The lead texted us before any outreach. {self._lead_context(conv)} Reply as the first contact."
        result = self.brain.turn(conv["messages"], tools, user_text=body, event=event, now_text=self.now_text(conv))
        self.store.update_conversation(conv["contact_id"], messages=result.messages)
        if result.reply:
            self._send(conv, result.reply)
        conv = self.store.get_conversation(conv["contact_id"]) or conv
        if conv["status"] == "active" and self.cfg.silent_cadence:
            first = self.cfg.silent_cadence[0]
            run_at = next_allowed(self.clock.now(self.zone_for(conv)) + timedelta(minutes=int(first.get("delay_minutes", 120))), self.cfg.quiet_hours)
            self.store.schedule(conv["contact_id"], "nudge", run_at.timestamp(), {"index": 0})

    def _run_nudge(self, conv: dict[str, Any], job: dict[str, Any]) -> None:
        index = int(job["payload"].get("index", 0))
        steps = self.cfg.silent_cadence
        if conv["status"] != "active" or index >= len(steps):
            return
        if conv.get("last_inbound_at") and conv["last_inbound_at"] > job["created_at"]:
            return  # they replied after this nudge was scheduled; the inbound path rescheduled
        reason = self._preflight(conv, "sms")
        if reason:
            return
        conv = self.store.get_conversation(conv["contact_id"]) or conv
        if conv["sms_sent"] >= self.cfg.max_sms:
            return
        step = steps[index]
        event = step.get("event") or "The lead replied earlier but has gone quiet. Send one gentle nudge that makes it easy to answer (a yes/no or a pick between two times)."
        self._send_event_sms(conv, event, count_toward_cadence=True)
        if index + 1 < len(steps):
            delay = int(steps[index + 1].get("delay_minutes", 1440))
            run_at = next_allowed(self.clock.now(self.zone_for(conv)) + timedelta(minutes=delay), self.cfg.quiet_hours)
            self.store.schedule(conv["contact_id"], "nudge", run_at.timestamp(), {"index": index + 1})

    # ------------------------------------------------------------------ voice
    def place_call(self, conv: dict[str, Any]) -> bool:
        assert self.retell is not None
        lead = conv["lead"]
        phone = lead.get("phone", "")
        if not phone:
            return False
        zone = self.zone_for(conv)
        now = self.clock.now(zone)
        if not in_window(now, self.cfg.call_window[0], self.cfg.call_window[1]) or is_quiet(now, self.cfg.quiet_hours):
            self.store.log(conv["contact_id"], "skip", reason="outside_call_window")
            return False
        tools = self._tools(conv)
        try:
            offer = tools.fetch_offer(self.cfg.slot_search_days, max_offer=3)
        except Exception as e:
            log.warning("slot prefetch failed: %s", e)
            offer = []
        spoken = " or ".join(humanize_slot(s, tools.zone) for s in offer[:2]) if offer else "a few times this week"
        listed = "; ".join(f"{humanize_slot(s, tools.zone)} (ISO {s})" for s in offer) if offer else "none prefetched; use get_available_slots"
        p = self.cfg.practice
        variables = {
            "lead_first_name": lead.get("first_name") or "there",
            "service_interest": lead.get("service_interest") or p.get("default_service_interest", "physical therapy"),
            "offered_slots": listed,
            "offered_slots_spoken": spoken,
            "current_time": self.clock.now(self.practice_zone).strftime("%A %B %d, %I:%M %p"),
            "contact_id": conv["contact_id"],
        }
        res = self.retell.create_phone_call(self.secrets.retell_from_number, phone, self.secrets.retell_agent_id, variables,
                                            {"contact_id": conv["contact_id"], "lead_name": lead.get("name", "")})
        call_id = res.get("call_id", "")
        self.store.record_call(call_id, conv["contact_id"], res.get("call_status", "registered"), {"variables": variables})
        self.store.bump(conv["contact_id"], "calls_placed")
        self.store.log(conv["contact_id"], "call_out", call_id=call_id, to=phone[-4:])
        return True

    def handle_voice_tool(self, name: str, args: dict[str, Any], call: dict[str, Any]) -> str:
        contact_id = contact_id_from_call(call)
        if not contact_id:
            return "Error: this call is not linked to a lead. Tell the lead the team will follow up and end the call."
        conv = self.store.get_conversation(contact_id)
        if conv is None:
            return "Error: unknown lead. Tell the lead the team will follow up and end the call."
        tools = self._tools(conv)
        out, _ = tools.run(name, args)
        return out

    def handle_voice_event(self, event: str, call: dict[str, Any]) -> dict[str, Any]:
        call_id = call.get("call_id", "")
        contact_id = contact_id_from_call(call)
        if not contact_id:
            return {"ok": True, "skipped": "no_contact"}
        conv = self.store.get_conversation(contact_id)
        info = summarize_call(call)
        self.store.record_call(call_id, contact_id, f"{event}:{info.get('status')}", info)
        if conv is None:
            return {"ok": True, "skipped": "no_conversation"}
        if event == "call_ended":
            reason = info.get("disconnection_reason") or ""
            not_reached = reason in NOT_REACHED or bool(info.get("in_voicemail"))
            self.store.log(contact_id, "call_ended", reason=reason, duration_ms=info.get("duration_ms"), reached=not not_reached)
            if not_reached and conv["status"] == "active" and self.cfg.raw.get("voice", {}).get("text_after_missed_call", True):
                zone = self.zone_for(conv)
                run_at = next_allowed(self.clock.now(zone) + timedelta(minutes=1), self.cfg.quiet_hours)
                self.store.schedule(contact_id, "missed_call_sms", run_at.timestamp(), {})
        elif event == "call_analyzed":
            note = [f"[{self.cfg.agent_name} AI] Call {call_id}: outcome={info.get('outcome')} sentiment={info.get('sentiment')} duration={int((info.get('duration_ms') or 0)/1000)}s"]
            if info.get("summary"):
                note.append(f"Summary: {info['summary']}")
            if info.get("lead_concern"):
                note.append(f"Lead concern: {info['lead_concern']}")
            if info.get("callback_window"):
                note.append(f"Callback requested: {info['callback_window']}")
            if info.get("recording_url"):
                note.append(f"Recording: {info['recording_url']}")
            if info.get("transcript"):
                note.append("Transcript:\n" + info["transcript"][:3500])
            self.ghl.add_note(contact_id, "\n".join(note))
            outcome = info.get("outcome")
            conv = self.store.get_conversation(contact_id) or conv
            if outcome == "callback_requested" and conv["status"] == "active":
                self._transition(contact_id, "callback_requested", "callback_requested", {"when": info.get("callback_window")})
                self.ghl.add_note(contact_id, f"[{self.cfg.agent_name} AI] Please call this lead back: {info.get('callback_window') or 'see transcript'}.")
                event_text = f"On a call just now the lead asked to be contacted at: '{info.get('callback_window') or 'a later time'}'. Send one short text confirming a team member will reach out then, and that they can reply here anytime."
                self.store.schedule(contact_id, "callback_sms", next_allowed(self.clock.now(self.zone_for(conv)), self.cfg.quiet_hours).timestamp(), {"event": event_text})
            elif outcome in ("not_interested", "opted_out", "wrong_number", "existing_patient") and conv["status"] == "active":
                self._transition(contact_id, outcome, outcome, {"via": "call_analysis"})
                self.ghl.add_tags(contact_id, [self.cfg.tags.get(outcome) or self.cfg.tags["not_interested"]])
            elif outcome == "needs_human" and conv["status"] == "active":
                self.ghl.add_tags(contact_id, [self.cfg.tags["handoff"]])
                self._transition(contact_id, "handoff", "needs_human", {})
            self.store.log(contact_id, "call_analyzed", outcome=outcome, booked=info.get("appointment_booked"))
        return {"ok": True}

    # ------------------------------------------------------------------ status
    def status(self, contact_id: str | None = None) -> dict[str, Any]:
        if contact_id:
            conv = self.store.get_conversation(contact_id)
            return {"conversation": conv, "jobs": self.store.pending_jobs(contact_id), "events": self.store.events(contact_id, 50)} if conv else {"error": "not found"}
        convs = self.store.list_conversations(limit=50)
        return {
            "busy_mode": self.busy_mode(),
            "conversations": [{k: v for k, v in c.items() if k not in ("messages", "lead")} | {"name": c["lead"].get("name")} for c in convs],
        }
