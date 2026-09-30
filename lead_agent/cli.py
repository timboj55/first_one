"""python -m lead_agent <command>

  serve            run the HTTP server + scheduler (production)
  setup-voice      create/update the Retell LLM + agent from agent_config.json; prints ids
  simulate         drive a fake lead through the SMS brain locally (no GHL/Retell writes)
  busy on|off      toggle busy mode
  status [id]      show conversations / one lead's timeline
  check            validate config + secrets, ping GHL
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

from .brain import Brain
from .config import Config, Secrets, load_dotenv
from .db import Store
from .ghl import GHLClient
from .hours import Clock
from .orchestrator import Orchestrator
from .scheduler import Scheduler
from .voice import RetellClient, build_agent_payload, build_llm_payload

VOICE_STATE = ".lead_agent_voice.json"


def build(dry_run: bool | None = None, need_voice: bool = False) -> tuple[Config, Secrets, Orchestrator]:
    load_dotenv()
    cfg = Config.load()
    sec = Secrets.from_env()
    if dry_run is not None:
        sec.dry_run = dry_run
    store = Store(sec.db_path)
    ghl = GHLClient(sec.ghl_token, sec.ghl_location_id, dry_run=sec.dry_run)
    brain = Brain(cfg)
    retell = RetellClient(sec.retell_api_key, dry_run=sec.dry_run) if (sec.retell_api_key or sec.dry_run) else None
    orch = Orchestrator(cfg, sec, store, ghl, brain, retell, Clock())
    return cfg, sec, orch


def cmd_serve(args: argparse.Namespace) -> int:
    cfg, sec, orch = build()
    missing = sec.missing(voice=bool(sec.retell_api_key))
    if missing and not sec.dry_run:
        print("missing env: " + ", ".join(missing), file=sys.stderr)
        return 2
    from .server import serve
    sched = Scheduler(orch.store, orch.run_job)
    sched.start()
    serve(orch, sched, args.host, args.port)
    sched.stop()
    return 0


def cmd_setup_voice(args: argparse.Namespace) -> int:
    load_dotenv()
    cfg = Config.load()
    sec = Secrets.from_env()
    if not sec.retell_api_key or not sec.public_base_url:
        print("need RETELL_API_KEY and PUBLIC_BASE_URL", file=sys.stderr)
        return 2
    client = RetellClient(sec.retell_api_key)
    state = {}
    if os.path.exists(VOICE_STATE):
        with open(VOICE_STATE) as f:
            state = json.load(f)
    llm_payload = build_llm_payload(cfg, sec.public_base_url)
    if args.print:
        print(json.dumps({"llm": llm_payload, "agent": build_agent_payload(cfg, "<llm_id>", sec.public_base_url)}, indent=2))
        return 0
    if state.get("llm_id"):
        llm = client.update_llm(state["llm_id"], llm_payload)
    else:
        llm = client.create_llm(llm_payload)
    llm_id = llm.get("llm_id") or state.get("llm_id")
    agent_payload = build_agent_payload(cfg, llm_id, sec.public_base_url)
    agent_id = state.get("agent_id") or sec.retell_agent_id
    if agent_id:
        agent = client.update_agent(agent_id, agent_payload)
    else:
        agent = client.create_agent(agent_payload)
    agent_id = agent.get("agent_id") or agent_id
    with open(VOICE_STATE, "w") as f:
        json.dump({"llm_id": llm_id, "agent_id": agent_id}, f, indent=2)
    print(f"llm_id={llm_id}\nagent_id={agent_id}\nSet RETELL_AGENT_ID={agent_id} in .env and bind a Retell phone number to this agent for outbound.")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Local conversation loop against the real Claude API with GHL/Retell in dry-run."""
    os.environ["LEAD_AGENT_DRY_RUN"] = "1"
    os.environ.setdefault("LEAD_AGENT_DB", ":memory:")
    os.environ.setdefault("GHL_WEBHOOK_SECRET", "sim")
    os.environ.setdefault("GHL_CALENDAR_ID", "sim-calendar")
    os.environ.setdefault("GHL_LOCATION_ID", "sim-location")
    os.environ.setdefault("GHL_TOKEN", "sim")
    cfg, sec, orch = build(dry_run=True)

    class FakeGHL(GHLClient):
        def get_contact(self, contact_id):
            return {"id": contact_id, "firstName": args.name.split()[0], "tags": [], "timezone": cfg.timezone}

        def free_slots(self, calendar_id, start, end, timezone, user_id=None):
            base = start.replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
            out = []
            for d in range(0, 5):
                day = base + timedelta(days=d)
                if day.weekday() >= 5:
                    continue
                for h in (9, 10, 11, 14, 15, 16):
                    out.append(day.replace(hour=h, minute=15).isoformat())
            return out

        def find_conversation_id(self, contact_id):
            return None

        def contact_appointments(self, contact_id):
            return []

    orch.ghl = FakeGHL("sim", "sim", dry_run=True)
    orch.store.set_setting("busy_mode", "1")
    res = orch.handle_new_lead({"contact_id": "sim-1", "full_name": args.name, "phone": "+15555550100",
                                "customData": {"service_interest": args.interest, "message_body": args.message}})
    print("new lead ->", res)
    sched = Scheduler(orch.store, orch.run_job)
    # force the first touch now
    for j in orch.store.pending_jobs("sim-1"):
        orch.store.conn().execute("UPDATE jobs SET run_at=0 WHERE id=?", (j["id"],))
        orch.store.conn().commit()
    sched.tick()
    print("\nType the lead's replies (Ctrl-D to quit).")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        orch.handle_inbound({"contact_id": "sim-1", "message": {"body": line, "type": "SMS", "direction": "inbound", "id": str(hash(line))}})
        sched.tick()
        conv = orch.store.get_conversation("sim-1")
        print(f"[status={conv['status']} outcome={conv['outcome']}]")
    return 0


def cmd_busy(args: argparse.Namespace) -> int:
    _, _, orch = build()
    orch.set_busy(args.state == "on")
    print("busy_mode =", orch.busy_mode())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _, _, orch = build()
    print(json.dumps(orch.status(args.contact_id), indent=2, default=str))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    cfg, sec, orch = build()
    missing = sec.missing(voice=bool(sec.retell_api_key))
    print("config:", cfg.practice.get("name"), "| tz", cfg.timezone, "| agent", cfg.agent_name)
    print("missing env:", missing or "none")
    if "GHL_TOKEN" not in missing and "GHL_CALENDAR_ID" not in missing:
        try:
            now = datetime.now(orch.practice_zone)
            slots = orch.ghl.free_slots(sec.ghl_calendar_id, now, now + timedelta(days=3), cfg.timezone)
            print(f"GHL ok: {len(slots)} free slots in next 3 days; first: {slots[:2]}")
        except Exception as e:
            print("GHL check failed:", e)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(name)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="lead_agent", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve"); s.add_argument("--host", default="0.0.0.0"); s.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080"))); s.set_defaults(fn=cmd_serve)
    s = sub.add_parser("setup-voice"); s.add_argument("--print", action="store_true", help="print payloads, do not call Retell"); s.set_defaults(fn=cmd_setup_voice)
    s = sub.add_parser("simulate"); s.add_argument("--name", default="Sam Rivera"); s.add_argument("--interest", default="knee pain after running"); s.add_argument("--message", default=""); s.set_defaults(fn=cmd_simulate)
    s = sub.add_parser("busy"); s.add_argument("state", choices=["on", "off"]); s.set_defaults(fn=cmd_busy)
    s = sub.add_parser("status"); s.add_argument("contact_id", nargs="?"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("check"); s.set_defaults(fn=cmd_check)
    args = p.parse_args(argv)
    return int(args.fn(args) or 0)
