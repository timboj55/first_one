"""Unit tests for the lead follow-up agent. No network: GHL, Claude and Retell are faked."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lead_agent.brain import Brain, BrainError  # noqa: E402
from lead_agent.config import Config, Secrets  # noqa: E402
from lead_agent.db import Store  # noqa: E402
from lead_agent.ghl import GHLClient, humanize_slot, pick_offer  # noqa: E402
from lead_agent.hours import Clock, in_window, is_business_hours, is_quiet, next_allowed  # noqa: E402
from lead_agent.orchestrator import Orchestrator, normalize_inbound, normalize_lead  # noqa: E402
from lead_agent.scheduler import Scheduler  # noqa: E402
from lead_agent.tools import TOOL_DEFS, Tools  # noqa: E402
from lead_agent.voice import (build_agent_payload, build_llm_payload, parse_tool_request, sign,  # noqa: E402
                              verify_signature)

ET = ZoneInfo("America/New_York")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cfg() -> Config:
    return Config.load(os.path.join(ROOT, "agent_config.json"))


def secrets(**over) -> Secrets:
    base = dict(anthropic_api_key="x", ghl_token="t", ghl_location_id="loc", ghl_calendar_id="cal", ghl_webhook_secret="whs",
                retell_api_key="rk", retell_agent_id="agent_1", retell_from_number="+15550001111", public_base_url="https://x.test",
                admin_secret="adm", db_path=":memory:", dry_run=False)
    base.update(over)
    return Secrets(**base)


class FakeGHL(GHLClient):
    """In-memory GHL: records every write; serves slots for the next 5 weekdays."""

    def __init__(self, now: datetime):
        super().__init__("t", "loc")
        self.now = now
        self.contacts: dict[str, dict] = {}
        self.sms: list[dict] = []
        self.tags: dict[str, list[str]] = {}
        self.notes: dict[str, list[str]] = {}
        self.appointments: list[dict] = []
        self.messages: dict[str, list[dict]] = {}
        self.updates: list[tuple] = []
        self._mid = 0

    def get_contact(self, contact_id):
        c = dict(self.contacts.get(contact_id, {"id": contact_id, "firstName": "Sam", "phone": "+15555550100"}))
        c["tags"] = self.tags.get(contact_id, []) + c.get("tags", [])
        return c

    def add_tags(self, contact_id, tags):
        self.tags.setdefault(contact_id, []).extend(t for t in tags if t)

    def remove_tags(self, contact_id, tags):
        self.tags[contact_id] = [t for t in self.tags.get(contact_id, []) if t not in tags]

    def add_note(self, contact_id, body):
        self.notes.setdefault(contact_id, []).append(body)

    def update_contact(self, contact_id, **fields):
        self.updates.append((contact_id, fields))

    def send_sms(self, contact_id, message, from_number=None):
        self._mid += 1
        mid = f"m{self._mid}"
        self.sms.append({"contact_id": contact_id, "message": message, "id": mid})
        self.messages.setdefault("conv-" + contact_id, []).append({"id": mid, "direction": "outbound", "body": message, "type": "TYPE_SMS"})
        return {"conversationId": "conv-" + contact_id, "messageId": mid}

    def find_conversation_id(self, contact_id):
        return "conv-" + contact_id if ("conv-" + contact_id) in self.messages else None

    def recent_messages(self, conversation_id, limit=30):
        return list(reversed(self.messages.get(conversation_id, [])))[:limit]

    def free_slots(self, calendar_id, start, end, timezone, user_id=None):
        out = []
        day = start.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
        while day <= end.astimezone(ET):
            if day.weekday() < 5:
                for h in (9, 10, 11, 14, 15, 16):
                    s = day.replace(hour=h, minute=15)
                    if start <= s <= end:
                        out.append(s.isoformat())
            day += timedelta(days=1)
        return out

    def create_appointment(self, calendar_id, contact_id, start_iso, end_iso, title, assigned_user_id=None, ignore_free_slot_validation=False):
        appt = {"id": f"appt{len(self.appointments)+1}", "calendarId": calendar_id, "contactId": contact_id, "startTime": start_iso, "endTime": end_iso, "title": title, "appointmentStatus": "confirmed"}
        self.appointments.append(appt)
        return appt

    def contact_appointments(self, contact_id):
        return [a for a in self.appointments if a["contactId"] == contact_id]


class FakeClaude:
    """Scripted Claude: each call pops the next response. Responses are lists of content blocks."""

    def __init__(self, script: list[list[dict]]):
        self.script = list(script)
        self.calls: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.script:
            raise AssertionError("FakeClaude script exhausted")
        blocks = self.script.pop(0)
        content = [SimpleNamespace(**b) for b in blocks]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        if blocks and blocks[0].get("_stop"):
            stop = blocks[0]["_stop"]
        return SimpleNamespace(content=content, stop_reason=stop, usage=None, model="fake")


def text(t):
    return {"type": "text", "text": t}


def tool_use(name, **args):
    return {"type": "tool_use", "id": f"tu-{name}-{int(time.time()*1000)%100000}", "name": name, "input": args}


class FakeRetell:
    def __init__(self):
        self.calls: list[dict] = []

    def create_phone_call(self, from_number, to_number, agent_id, dynamic_variables, metadata):
        self.calls.append({"to": to_number, "vars": dynamic_variables, "meta": metadata})
        return {"call_id": f"call{len(self.calls)}", "call_status": "registered"}


def make(now: datetime, script: list[list[dict]] | None = None, sec_over: dict | None = None):
    c = cfg()
    sec = secrets(**(sec_over or {}))
    store = Store(":memory:")
    ghl = FakeGHL(now)
    claude = FakeClaude(script or [])
    brain = Brain(c, client=claude)
    retell = FakeRetell()
    orch = Orchestrator(c, sec, store, ghl, brain, retell, Clock(now))
    sched = Scheduler(store, orch.run_job)
    return orch, ghl, claude, retell, sched


def run_all_due(orch: Orchestrator, sched: Scheduler, at: datetime) -> int:
    """Advance the clock to `at` and run everything due by then."""
    orch.clock.fixed = at
    total = 0
    for _ in range(10):
        n = len(orch.store.claim_due_jobs(now=at.timestamp()))
        # claim_due_jobs marked them running; re-fetch and run via scheduler semantics
        if n == 0:
            break
        rows = orch.store.conn().execute("SELECT * FROM jobs WHERE status='running'").fetchall()
        for r in rows:
            job = Store._job(r)
            sched._run_one(job)
            total += 1
    return total


# --------------------------------------------------------------------------- hours

class HoursTests(unittest.TestCase):
    def test_windows(self):
        c = cfg()
        tue_2pm = datetime(2026, 9, 29, 14, 0, tzinfo=ET)
        tue_9pm = datetime(2026, 9, 29, 21, 0, tzinfo=ET)
        sat = datetime(2026, 10, 3, 11, 0, tzinfo=ET)
        self.assertTrue(is_business_hours(tue_2pm, c.business_hours, c.holidays))
        self.assertFalse(is_business_hours(tue_9pm, c.business_hours, c.holidays))
        self.assertFalse(is_business_hours(sat, c.business_hours, c.holidays))
        self.assertFalse(is_business_hours(datetime(2026, 11, 26, 10, 0, tzinfo=ET), c.business_hours, c.holidays))
        self.assertTrue(is_quiet(tue_9pm, c.quiet_hours))
        self.assertFalse(is_quiet(tue_2pm, c.quiet_hours))
        self.assertTrue(in_window(datetime(2026, 9, 29, 1, 0, tzinfo=ET), "20:30", "08:00"))

    def test_next_allowed_defers_past_quiet_hours_and_into_call_window(self):
        c = cfg()
        late = datetime(2026, 9, 29, 22, 15, tzinfo=ET)
        nxt = next_allowed(late, c.quiet_hours)
        self.assertEqual((nxt.day, nxt.hour, nxt.minute), (30, 8, 0))
        nxt_call = next_allowed(late, c.quiet_hours, c.call_window)
        self.assertEqual((nxt_call.day, nxt_call.hour), (30, 9))
        ok = datetime(2026, 9, 29, 14, 0, tzinfo=ET)
        self.assertEqual(next_allowed(ok, c.quiet_hours), ok)


# --------------------------------------------------------------------------- ghl helpers

class GHLHelperTests(unittest.TestCase):
    def test_pick_offer_spreads_and_skips_too_soon(self):
        now = datetime(2026, 9, 29, 9, 0, tzinfo=ET)
        slots = FakeGHL(now).free_slots("cal", now, now + timedelta(days=3), "America/New_York")
        offer = pick_offer(slots, ET, now, max_offer=4)
        self.assertEqual(len(offer), 4)
        self.assertTrue(all(datetime.fromisoformat(s) >= now + timedelta(minutes=60) for s in offer))
        days = {datetime.fromisoformat(s).date() for s in offer}
        self.assertGreaterEqual(len(days), 2)

    def test_humanize(self):
        self.assertEqual(humanize_slot("2026-09-30T10:15:00-04:00", ET), "Wednesday Sep 30 at 10:15 AM")
        self.assertEqual(humanize_slot("2026-09-30T14:00:00-04:00", ET), "Wednesday Sep 30 at 2 PM")


# --------------------------------------------------------------------------- payload parsing

class PayloadTests(unittest.TestCase):
    def test_normalize_lead_from_ghl_workflow_shape(self):
        p = {"contact_id": "abc", "first_name": "Sam", "last_name": "Rivera", "full_name": "Sam Rivera", "phone": "+15555550100",
             "email": "s@x.com", "tags": "lead, web", "location": {"id": "loc"}, "contact_source": "Website form",
             "customData": {"service_interest": "knee pain"}}
        lead = normalize_lead(p)
        self.assertEqual(lead["contact_id"], "abc")
        self.assertEqual(lead["tags"], ["lead", "web"])
        self.assertEqual(lead["service_interest"], "knee pain")
        self.assertEqual(lead["source"], "Website form")
        self.assertEqual(lead["location_id"], "loc")

    def test_normalize_inbound_variants(self):
        a = normalize_inbound({"contact_id": "abc", "message": {"body": "hi", "type": "SMS", "direction": "inbound", "id": "m1"}})
        self.assertEqual((a["body"], a["message_id"], a["direction"]), ("hi", "m1", "inbound"))
        b = normalize_inbound({"contact_id": "abc", "customData": {"message_body": "yo", "message_type": "SMS"}})
        self.assertEqual(b["body"], "yo")
        self.assertEqual(b["message_type"], "SMS")


# --------------------------------------------------------------------------- brain + tools

class BrainTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)  # Tuesday 8:05pm, after hours
        self.c = cfg()
        self.store = Store(":memory:")
        self.ghl = FakeGHL(self.now)
        self.statuses: list[tuple] = []
        self.tools = Tools(self.c, self.ghl, self.store, "cal", "abc", {"first_name": "Sam", "name": "Sam Rivera"}, clock=Clock(self.now),
                           on_status=lambda s, o, d: self.statuses.append((s, o)))

    def test_tool_defs_are_strict_and_complete(self):
        names = {t["name"] for t in TOOL_DEFS}
        self.assertEqual(names, {"get_available_slots", "book_inquiry_call", "flag_for_team", "mark_outcome"})
        for t in TOOL_DEFS:
            self.assertTrue(t["strict"])
            self.assertFalse(t["input_schema"]["additionalProperties"])
            self.assertEqual(set(t["input_schema"]["required"]), set(t["input_schema"]["properties"]))

    def test_slots_then_book(self):
        out, err = self.tools.run("get_available_slots", {"days_ahead": 3, "preference": "mornings"})
        self.assertFalse(err)
        self.assertIn("ISO=", out)
        iso = out.split("ISO=")[1].split()[0]
        out2, err2 = self.tools.run("book_inquiry_call", {"start_time": iso, "notes": "knee pain"})
        self.assertFalse(err2, out2)
        self.assertIn("Booked for", out2)
        self.assertEqual(len(self.ghl.appointments), 1)
        self.assertEqual(self.ghl.appointments[0]["contactId"], "abc")
        self.assertIn("ai-agent-booked", self.ghl.tags["abc"])
        self.assertEqual(self.statuses, [("booked", "booked")])

    def test_book_rejects_slot_not_offered(self):
        self.tools.run("get_available_slots", {"days_ahead": 3, "preference": ""})
        out, err = self.tools.run("book_inquiry_call", {"start_time": "2026-09-30T12:37:00-04:00", "notes": ""})
        self.assertFalse(err)
        self.assertIn("not open", out)
        self.assertEqual(self.ghl.appointments, [])

    def test_opt_out_sets_dnd_and_status(self):
        out, _ = self.tools.run("mark_outcome", {"outcome": "opted_out", "summary": "said STOP"})
        self.assertIn("NO_REPLY", out)
        self.assertEqual(self.statuses, [("opted_out", "opted_out")])
        self.assertTrue(any("dndSettings" in f for _, f in self.ghl.updates))

    def test_brain_tool_loop_and_no_reply(self):
        claude = FakeClaude([
            [tool_use("get_available_slots", days_ahead=7, preference="")],
            [text("Hi Sam! Want to grab a quick call tomorrow at 10:15 or 2:15?")],
        ])
        brain = Brain(self.c, client=claude)
        res = brain.turn([], self.tools, event="Send the first outreach text.")
        self.assertIn("10:15", res.reply)
        self.assertEqual(len(res.messages), 4)  # user, assistant(tool_use), user(tool_result), assistant(text)
        self.assertEqual(res.messages[2]["content"][0]["type"], "tool_result")
        self.assertEqual(claude.calls[0]["model"], "claude-opus-5-5")
        self.assertEqual(claude.calls[0]["fallbacks"], "default")
        self.assertIn("cache_control", claude.calls[0]["system"][0])
        # follow-up turn appends to history
        claude.script.append([text("NO_REPLY")])
        res2 = brain.turn(res.messages, self.tools, user_text="STOP", now_text="Tue Sep 29, 8:10 PM")
        self.assertIsNone(res2.reply)
        self.assertEqual(len(res2.messages), 6)

    def test_brain_refusal_hands_off(self):
        claude = FakeClaude([[{**text(""), "_stop": "refusal"}]])
        brain = Brain(self.c, client=claude)
        res = brain.turn([], self.tools, user_text="something", now_text="")
        self.assertIn("team", res.reply)
        self.assertEqual(self.statuses, [("handoff", "other")])

    def test_brain_transient_errors_bubble_as_brain_error(self):
        import anthropic
        class Boom:
            def __init__(self):
                self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._c))
            def _c(self, **kw):
                raise anthropic.APIConnectionError(request=None)  # type: ignore[arg-type]
        brain = Brain(self.c, client=Boom())
        with self.assertRaises(BrainError):
            brain.turn([], self.tools, event="x")


# --------------------------------------------------------------------------- orchestrator

class OrchestratorTests(unittest.TestCase):
    LEAD = {"contact_id": "abc", "first_name": "Sam", "last_name": "Rivera", "phone": "+15555550100",
            "customData": {"service_interest": "knee pain", "message_body": "hurts when I run"}}

    def test_after_hours_lead_gets_immediate_text_then_call_then_text(self):
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)  # 8:05 pm Tue
        orch, ghl, claude, retell, sched = make(now, [
            [tool_use("get_available_slots", days_ahead=7, preference="")],
            [text("Hi Sam, this is Maya with Movement Solutions. Tomorrow 10:15 or 2:15 for a quick call?")],
            [text("Just checking in, Sam. Would Thursday morning work better?")],
        ])
        res = orch.handle_new_lead(self.LEAD)
        self.assertEqual(res["delay_minutes"], 0)
        self.assertIn("ai-agent-active", ghl.tags["abc"])
        # step 0: sms now
        run_all_due(orch, sched, now)
        self.assertEqual(len(ghl.sms), 1)
        self.assertIn("Maya", ghl.sms[0]["message"])
        conv = orch.store.get_conversation("abc")
        self.assertEqual(conv["sms_sent"], 1)
        # step 1: call 4 minutes later, inside call window (before 19:30)? 20:09 is outside -> deferred to 9am next day
        run_all_due(orch, sched, now + timedelta(minutes=5))
        self.assertEqual(len(retell.calls), 0)
        jobs = orch.store.pending_jobs("abc")
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0]["payload"].get("deferred"))
        nine = datetime(2026, 9, 30, 9, 0, tzinfo=ET)
        run_all_due(orch, sched, nine + timedelta(minutes=1))
        self.assertEqual(len(retell.calls), 1)
        self.assertEqual(retell.calls[0]["to"], "+15555550100")
        self.assertEqual(retell.calls[0]["meta"]["contact_id"], "abc")
        self.assertIn("ISO", retell.calls[0]["vars"]["offered_slots"])
        self.assertEqual(retell.calls[0]["vars"]["lead_first_name"], "Sam")
        # step 2: sms 90 min after the call
        run_all_due(orch, sched, nine + timedelta(minutes=95))
        self.assertEqual(len(ghl.sms), 2)
        self.assertIn("Thursday", ghl.sms[1]["message"])

    def test_business_hours_waits_then_engages_if_team_silent(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Hi Sam! Quick call tomorrow?")]])
        res = orch.handle_new_lead(self.LEAD)
        self.assertEqual(res["delay_minutes"], 5)
        run_all_due(orch, sched, now + timedelta(minutes=1))
        self.assertEqual(ghl.sms, [])
        run_all_due(orch, sched, now + timedelta(minutes=6))
        self.assertEqual(len(ghl.sms), 1)

    def test_business_hours_team_replied_in_time_stops_agent(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("should not send")]])
        orch.handle_new_lead(self.LEAD)
        ghl.messages["conv-abc"] = [{"id": "human1", "direction": "outbound", "body": "Hi Sam, this is Dana from the front desk", "type": "TYPE_SMS"}]
        run_all_due(orch, sched, now + timedelta(minutes=6))
        self.assertEqual(ghl.sms, [])
        self.assertEqual(orch.store.get_conversation("abc")["outcome"], "team_handled")

    def test_busy_mode_engages_immediately_in_business_hours(self):
        now = datetime(2026, 9, 29, 14, 0, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Hi Sam!")]])
        orch.set_busy(True)
        res = orch.handle_new_lead(self.LEAD)
        self.assertEqual(res["delay_minutes"], 0)

    def test_quiet_hours_defer_first_text_to_morning(self):
        now = datetime(2026, 9, 29, 23, 0, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Morning Sam!")]])
        res = orch.handle_new_lead(self.LEAD)
        self.assertTrue(res["first_touch_at"].startswith("2026-09-30T08:00"))
        run_all_due(orch, sched, now + timedelta(minutes=30))
        self.assertEqual(ghl.sms, [])

    def test_inbound_reply_books_and_stops_cadence(self):
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [
            [text("Hi Sam, tomorrow 10:15 or 2:15?")],
            [tool_use("get_available_slots", days_ahead=3, preference="10:15 tomorrow")],
            [tool_use("book_inquiry_call", start_time="2026-09-30T10:15:00-04:00", notes="knee pain when running")],
            [text("You're all set for Wednesday at 10:15am. Our coordinator will call you then!")],
        ])
        orch.handle_new_lead(self.LEAD)
        run_all_due(orch, sched, now)
        self.assertEqual(len(orch.store.pending_jobs("abc")), 1)  # the call step
        r = orch.handle_inbound({"contact_id": "abc", "message": {"body": "10:15 tomorrow works", "type": "SMS", "direction": "inbound", "id": "in1"}})
        self.assertIn("queued", r)
        run_all_due(orch, sched, now + timedelta(minutes=1))
        conv = orch.store.get_conversation("abc")
        self.assertEqual(conv["status"], "booked")
        self.assertEqual(conv["appointment_id"], "appt1")
        self.assertEqual(len(ghl.appointments), 1)
        self.assertEqual(ghl.appointments[0]["startTime"], "2026-09-30T10:15:00-04:00")
        self.assertEqual(len(ghl.sms), 2)
        self.assertIn("all set", ghl.sms[1]["message"])
        self.assertEqual(orch.store.pending_jobs("abc"), [])
        # duplicate webhook delivery is ignored
        r2 = orch.handle_inbound({"contact_id": "abc", "message": {"body": "10:15 tomorrow works", "type": "SMS", "direction": "inbound", "id": "in1"}})
        self.assertEqual(r2.get("skipped"), "duplicate")

    def test_inbound_then_silence_schedules_nudge(self):
        now = datetime(2026, 9, 29, 12, 5, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Hi!")], [text("Sure, what day works?")], [text("Still there? Mornings or afternoons?")]])
        orch.set_busy(True)
        orch.handle_new_lead(self.LEAD)
        run_all_due(orch, sched, now)
        orch.handle_inbound({"contact_id": "abc", "message": {"body": "maybe", "type": "SMS", "direction": "inbound", "id": "in2"}})
        run_all_due(orch, sched, now + timedelta(minutes=1))
        jobs = orch.store.pending_jobs("abc")
        self.assertEqual([j["kind"] for j in jobs], ["nudge"])
        run_all_due(orch, sched, now + timedelta(minutes=125))
        self.assertEqual(len(ghl.sms), 3)
        self.assertIn("Mornings", ghl.sms[2]["message"])

    def test_human_takeover_pauses_agent(self):
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Hi Sam!")], [text("should not be sent")]])
        orch.handle_new_lead(self.LEAD)
        run_all_due(orch, sched, now)
        ghl.messages["conv-abc"].append({"id": "human9", "direction": "outbound", "body": "Hey Sam, Dana here", "type": "TYPE_SMS"})
        orch.handle_inbound({"contact_id": "abc", "message": {"body": "thanks Dana", "type": "SMS", "direction": "inbound", "id": "in3"}})
        run_all_due(orch, sched, now + timedelta(minutes=1))
        conv = orch.store.get_conversation("abc")
        self.assertEqual(conv["status"], "paused_human")
        self.assertEqual(len(ghl.sms), 1)
        self.assertIn("ai-agent-paused-human", ghl.tags["abc"])

    def test_stop_tag_and_dnd_skip(self):
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [])
        ghl.tags["abc"] = ["ai-agent-stop"]
        self.assertEqual(orch.handle_new_lead(self.LEAD)["skipped"], "tag:ai-agent-stop")
        orch2, ghl2, *_ = make(now, [])
        ghl2.contacts["abc"] = {"id": "abc", "phone": "+15555550100", "dndSettings": {"SMS": {"status": "active"}}}
        self.assertEqual(orch2.handle_new_lead(self.LEAD)["skipped"], "dnd:sms")

    def test_appointment_booked_elsewhere_stops_outreach(self):
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Hi Sam!")]])
        orch.handle_new_lead(self.LEAD)
        run_all_due(orch, sched, now)
        orch.handle_appointment_booked({"contact_id": "abc", "appointment": {"id": "web-appt"}})
        conv = orch.store.get_conversation("abc")
        self.assertEqual(conv["status"], "booked")
        self.assertEqual(orch.store.pending_jobs("abc"), [])

    def test_voice_tool_and_events(self):
        now = datetime(2026, 9, 30, 10, 0, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Sorry I missed you! Tomorrow 10:15 or 2:15?")], [text("Got it, we'll reach out tomorrow after 5.")]])
        orch.set_busy(True)
        orch.handle_new_lead(self.LEAD)
        call = {"call_id": "c1", "metadata": {"contact_id": "abc"}}
        out = orch.handle_voice_tool("get_available_slots", {"days_ahead": 3, "preference": ""}, call)
        self.assertIn("ISO=", out)
        iso = out.split("ISO=")[1].split()[0]
        out2 = orch.handle_voice_tool("book_inquiry_call", {"start_time": iso, "notes": "from call"}, call)
        self.assertIn("Booked", out2)
        self.assertEqual(orch.store.get_conversation("abc")["status"], "booked")
        # a missed call on a different active lead schedules a 'missed you' text
        orch.handle_new_lead({**self.LEAD, "contact_id": "def"})
        orch.store.cancel_jobs("def")
        orch.handle_voice_event("call_ended", {"call_id": "c2", "metadata": {"contact_id": "def"}, "disconnection_reason": "dial_no_answer"})
        self.assertEqual([j["kind"] for j in orch.store.pending_jobs("def")], ["missed_call_sms"])
        run_all_due(orch, sched, now + timedelta(minutes=2))
        self.assertTrue(any("missed" in s["message"] for s in ghl.sms))
        # call_analyzed with callback request hands off + notes + confirmation text
        orch.handle_voice_event("call_analyzed", {"call_id": "c2", "metadata": {"contact_id": "def"}, "transcript": "agent: hi\nuser: call me tomorrow after 5",
                                                  "call_analysis": {"call_summary": "wants callback", "custom_analysis_data": {"outcome": "callback_requested", "callback_window": "tomorrow after 5pm"}}})
        conv = orch.store.get_conversation("def")
        self.assertEqual(conv["status"], "handoff")
        self.assertTrue(any("Transcript" in n for n in ghl.notes["def"]))
        run_all_due(orch, sched, now + timedelta(minutes=3))
        self.assertTrue(any("after 5" in s["message"] for s in ghl.sms))

    def test_cadence_exhausts_and_closes(self):
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)
        c = cfg()
        n_sms = sum(1 for s in c.cadence if s["channel"] == "sms")
        orch, ghl, claude, retell, sched = make(now, [[text(f"touch {i}")] for i in range(n_sms + 3)], sec_over={"retell_agent_id": ""})
        orch.handle_new_lead(self.LEAD)
        t = now
        for _ in range(40):
            t += timedelta(hours=6)
            run_all_due(orch, sched, t)
            if orch.store.get_conversation("abc")["status"] == "done":
                break
        conv = orch.store.get_conversation("abc")
        self.assertEqual(conv["status"], "done")
        self.assertEqual(conv["outcome"], "no_response")
        self.assertLessEqual(conv["sms_sent"], c.max_sms)
        self.assertTrue(any("Outreach ended" in n for n in ghl.notes["abc"]))


# --------------------------------------------------------------------------- voice payloads + signature

class VoiceTests(unittest.TestCase):
    def test_signature_roundtrip(self):
        body = '{"event":"call_ended"}'
        sig = sign(body, "key", ts_ms=1_700_000_000_000)
        self.assertTrue(verify_signature(body, "key", sig, now_ms=1_700_000_010_000))
        self.assertFalse(verify_signature(body, "other", sig, now_ms=1_700_000_010_000))
        self.assertFalse(verify_signature(body, "key", sig, now_ms=1_700_000_000_000 + 10 * 60 * 1000))
        self.assertFalse(verify_signature(body + " ", "key", sig, now_ms=1_700_000_010_000))

    def test_parse_tool_request(self):
        name, args, call = parse_tool_request({"name": "book_inquiry_call", "args": {"start_time": "x"}, "call": {"call_id": "c"}}, "ignored")
        self.assertEqual((name, args["start_time"], call["call_id"]), ("book_inquiry_call", "x", "c"))
        name, args, call = parse_tool_request({"days_ahead": 3}, "get_available_slots")
        self.assertEqual((name, args), ("get_available_slots", {"days_ahead": 3}))

    def test_payloads(self):
        c = cfg()
        llm = build_llm_payload(c, "https://x.test")
        names = [t["name"] for t in llm["general_tools"]]
        self.assertIn("book_inquiry_call", names)
        self.assertIn("end_call", names)
        self.assertNotIn("transfer_to_team", names)
        custom = next(t for t in llm["general_tools"] if t["name"] == "book_inquiry_call")
        self.assertEqual(custom["url"], "https://x.test/voice/tools/book_inquiry_call")
        self.assertIn("{{lead_first_name}}", llm["general_prompt"])
        agent = build_agent_payload(c, "llm_1", "https://x.test")
        self.assertEqual(agent["webhook_url"], "https://x.test/voice/webhook")
        self.assertEqual(agent["response_engine"], {"type": "retell-llm", "llm_id": "llm_1"})
        self.assertTrue(agent["enable_backchannel"])
        self.assertEqual(agent["ambient_sound"], "call-center")
        outcome = next(d for d in agent["post_call_analysis_data"] if d["name"] == "outcome")
        self.assertIn("callback_requested", outcome["choices"])
        json.dumps(llm); json.dumps(agent)


# --------------------------------------------------------------------------- server

class ServerTests(unittest.TestCase):
    def test_routes_and_auth(self):
        import http.client
        import threading
        from http.server import ThreadingHTTPServer
        from lead_agent.server import make_handler
        now = datetime(2026, 9, 29, 20, 5, tzinfo=ET)
        orch, ghl, claude, retell, sched = make(now, [[text("Hi Sam!")]])
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(orch, None))
        port = httpd.server_address[1]
        th = threading.Thread(target=httpd.serve_forever, daemon=True); th.start()
        try:
            def req(method, path, body=None, headers=None):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                data = json.dumps(body) if body is not None else None
                conn.request(method, path, body=data, headers={"Content-Type": "application/json", **(headers or {})})
                r = conn.getresponse()
                return r.status, json.loads(r.read() or b"{}")
            self.assertEqual(req("GET", "/healthz")[0], 200)
            self.assertEqual(req("POST", "/webhooks/ghl/wrong/new-lead", {"contact_id": "abc"})[0], 404)
            st, res = req("POST", "/webhooks/ghl/whs/new-lead", OrchestratorTests.LEAD)
            self.assertEqual((st, res["contact_id"]), (200, "abc"))
            # retell tool call requires a valid signature
            body = {"name": "get_available_slots", "args": {"days_ahead": 2, "preference": ""}, "call": {"call_id": "c", "metadata": {"contact_id": "abc"}}}
            self.assertEqual(req("POST", "/voice/tools/get_available_slots", body)[0], 401)
            raw = json.dumps(body)
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("POST", "/voice/tools/get_available_slots", body=raw, headers={"Content-Type": "application/json", "x-retell-signature": sign(raw, "rk")})
            r = conn.getresponse(); out = json.loads(r.read())
            self.assertEqual(r.status, 200)
            self.assertIn("ISO=", out["result"])
            st, res = req("POST", "/admin/adm/busy", {"on": True})
            self.assertEqual((st, res["busy_mode"]), (200, True))
            st, res = req("GET", "/admin/adm/status?contact_id=abc")
            self.assertEqual(res["conversation"]["status"], "active")
        finally:
            httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    unittest.main()
