"""Booking tools shared by the SMS brain and the voice agent.

Every tool returns a plain string for the model. Side effects (GHL booking, tags, notes,
conversation status) happen here so both channels behave identically.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from .config import Config
from .db import Store
from .ghl import GHLClient, humanize_slot, pick_offer, slot_end
from .hours import Clock, tz

log = logging.getLogger("lead_agent.tools")

OUTCOMES = ("not_interested", "opted_out", "wrong_number", "existing_patient")

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "get_available_slots",
        "description": "Look up open times for the inquiry call on the team calendar. Call this before offering times, or when the lead wants different days/times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "How many days ahead to search. Default 7, max 21."},
                "preference": {"type": "string", "description": "What the lead asked for in their words, e.g. 'mornings', 'Friday', 'after 5pm'. Empty if none."},
            },
            "required": ["days_ahead", "preference"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "book_inquiry_call",
        "description": "Book the inquiry call at a specific start time the lead agreed to. Use the exact ISO start time returned by get_available_slots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_time": {"type": "string", "description": "ISO 8601 start time with UTC offset, exactly as returned by get_available_slots."},
                "notes": {"type": "string", "description": "One line on what the lead wants to discuss, for the team."},
            },
            "required": ["start_time", "notes"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "flag_for_team",
        "description": "Hand this conversation to a human team member and pause automated outreach. Use for clinical questions, billing, complaints, existing patients, reschedules, or when the lead asks for a person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "enum": ["clinical_question", "billing", "complaint", "existing_patient", "wants_specific_person", "reschedule", "booking_failed", "other"]},
                "summary": {"type": "string", "description": "One or two sentences the team should know before they reach out."},
            },
            "required": ["reason", "summary"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "mark_outcome",
        "description": "Record a final outcome that ends automated outreach: the lead opted out, is not interested, wrong number, or is an existing patient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "outcome": {"type": "string", "enum": list(OUTCOMES)},
                "summary": {"type": "string", "description": "One line on why."},
            },
            "required": ["outcome", "summary"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class Tools:
    """Executes tools for one contact. `on_status` lets the orchestrator react (cancel jobs, etc.)."""

    def __init__(self, cfg: Config, ghl: GHLClient, store: Store, calendar_id: str, contact_id: str,
                 lead: dict[str, Any], clock: Clock | None = None,
                 on_status: Callable[[str, str, dict[str, Any]], None] | None = None,
                 assigned_user_id: str | None = None):
        self.cfg = cfg
        self.ghl = ghl
        self.store = store
        self.calendar_id = calendar_id
        self.contact_id = contact_id
        self.lead = lead
        self.clock = clock or Clock()
        self.on_status = on_status or (lambda status, outcome, data: None)
        self.assigned_user_id = assigned_user_id
        self.zone = tz(cfg.timezone, "UTC")
        self.last_slots: list[str] = []
        self.booked: dict[str, Any] | None = None

    # ------------ dispatch ------------
    def run(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Returns (result_text, is_error)."""
        fn = getattr(self, f"tool_{name}", None)
        if fn is None:
            return f"Unknown tool {name}", True
        try:
            out = fn(**(args or {}))
            self.store.log(self.contact_id, "tool", name=name, args=args, result=out[:500])
            return out, False
        except TypeError as e:
            return f"Bad arguments for {name}: {e}", True
        except Exception as e:  # tool failures are reported to the model, not raised
            log.exception("tool %s failed", name)
            self.store.log(self.contact_id, "tool_error", name=name, args=args, error=str(e))
            return f"{name} failed: {e}", True

    # ------------ tools ------------
    def fetch_offer(self, days_ahead: int = 7, max_offer: int = 6) -> list[str]:
        now = self.clock.now(self.zone)
        days_ahead = max(1, min(int(days_ahead or 7), 21))
        start = now
        end = (now + timedelta(days=days_ahead)).replace(hour=23, minute=59)
        slots = self.ghl.free_slots(self.calendar_id, start, end, self.cfg.timezone, self.assigned_user_id)
        offer = pick_offer(slots, self.zone, now, max_offer=max_offer)
        self.last_slots = slots
        return offer

    def tool_get_available_slots(self, days_ahead: int = 7, preference: str = "") -> str:
        offer = self.fetch_offer(days_ahead)
        if not offer:
            return "No open slots in that range. Offer to have the team reach out directly, or search further ahead."
        lines = [f"Open slots (times in {self.cfg.timezone}). Use the ISO value when booking:"]
        for iso in offer:
            lines.append(f"- {humanize_slot(iso, self.zone)}  ISO={iso}")
        if preference:
            lines.append(f"Lead preference: {preference}. Prefer matching slots; if none match, say so and offer the closest.")
        return "\n".join(lines)

    def tool_book_inquiry_call(self, start_time: str, notes: str = "") -> str:
        try:
            dt = datetime.fromisoformat(start_time)
        except ValueError:
            return "start_time must be ISO 8601 with offset, exactly as returned by get_available_slots."
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.zone)
        if dt < self.clock.now(self.zone):
            return "That time is in the past. Fetch slots again and offer a future time."
        start_iso = dt.isoformat()
        # Validate against the last fetched slots when available; if the model never fetched, fetch now.
        if not self.last_slots:
            self.fetch_offer(self.cfg.slot_search_days, max_offer=50)
        valid = {datetime.fromisoformat(s).astimezone(self.zone).replace(microsecond=0) for s in self.last_slots}
        if valid and dt.astimezone(self.zone).replace(microsecond=0) not in valid:
            return "That exact time is not open. Call get_available_slots and offer one of the returned slots."
        p = self.cfg.practice
        title = self.cfg.appointment_title.format(
            inquiry_call_name=p.get("inquiry_call_name", "Inquiry call"),
            name=self.lead.get("name") or self.lead.get("first_name") or "lead",
        )
        end_iso = slot_end(start_iso, self.cfg.appointment_minutes)
        appt = self.ghl.create_appointment(self.calendar_id, self.contact_id, start_iso, end_iso, title, self.assigned_user_id)
        appt_id = appt.get("id") or appt.get("appointmentId") or ""
        self.booked = {"appointment_id": appt_id, "start_time": start_iso, "notes": notes}
        self.ghl.add_tags(self.contact_id, [self.cfg.tags["booked"]])
        if notes:
            self.ghl.add_note(self.contact_id, f"[{self.cfg.agent_name} AI] Booked {p.get('inquiry_call_name', 'inquiry call')} for {humanize_slot(start_iso, self.zone)}. Lead wants to discuss: {notes}")
        self.on_status("booked", "booked", self.booked)
        return f"Booked for {humanize_slot(start_iso, self.zone)} ({self.cfg.timezone}). Appointment id {appt_id}. Confirm this to the lead in one short message."

    def tool_flag_for_team(self, reason: str, summary: str) -> str:
        self.ghl.add_tags(self.contact_id, [self.cfg.tags["handoff"]])
        self.ghl.add_note(self.contact_id, f"[{self.cfg.agent_name} AI] Needs a human ({reason}): {summary}")
        self.on_status("handoff", reason, {"summary": summary})
        return "Flagged. Tell the lead briefly that a team member will reach out (during office hours if it's after hours), then stop selling."

    def tool_mark_outcome(self, outcome: str, summary: str = "") -> str:
        if outcome not in OUTCOMES:
            return f"outcome must be one of {OUTCOMES}"
        tag = self.cfg.tags.get(outcome) or self.cfg.tags.get("not_interested")
        self.ghl.add_tags(self.contact_id, [tag])
        if outcome == "opted_out":
            try:
                self.ghl.update_contact(self.contact_id, dndSettings={"SMS": {"status": "active", "message": "Opted out via AI agent"},
                                                                    "Call": {"status": "active", "message": "Opted out via AI agent"}})
            except Exception as e:  # DND update is best-effort; the tag already stops us
                log.warning("dnd update failed: %s", e)
        self.ghl.add_note(self.contact_id, f"[{self.cfg.agent_name} AI] Outcome {outcome}: {summary}")
        self.on_status(outcome, outcome, {"summary": summary})
        return "Recorded. Do not send further outreach." + (" Reply NO_REPLY." if outcome == "opted_out" else " A short polite goodbye is fine if appropriate.")

    def tool_schedule_callback_note(self, when: str, channel: str = "call") -> str:
        self.ghl.add_note(self.contact_id, f"[{self.cfg.agent_name} AI] Lead asked to be reached by {channel}: {when}")
        self.on_status("callback_requested", channel, {"when": when})
        return "Noted. Tell the lead the team will reach out then, and end the call politely."
