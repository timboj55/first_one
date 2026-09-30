"""CLI: python -m superbill sync | rebuild | preview | serve

sync     rebuild superbills for every client with a visit completed in the lookback window
rebuild  one client: --client-id 123 (upload) ; add --dry-run to only render
preview  one client to a local PDF file without touching PracticeQ (--out path)
serve    HTTP endpoints for n8n (see server.py)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .api import SuperbillAPI
from .build import build_superbill
from .config import load_config, load_dotenv
from .render import render_pdf
from .sync import SuperbillSync


def _api(args: argparse.Namespace) -> SuperbillAPI:
    return SuperbillAPI(min_seconds_between_calls=args.min_gap)


def cmd_sync(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    s = SuperbillSync(_api(args), cfg, dry_run=args.dry_run)
    res = s.sync(args.since_days)
    for r in res.results:
        print(json.dumps(r.__dict__), file=sys.stderr)
    print(json.dumps(res.summary()))
    return 0 if not any(r.action == "error" for r in res.results) else 1


def cmd_rebuild(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    s = SuperbillSync(_api(args), cfg, dry_run=args.dry_run)
    r = s.refresh(args.client_id, force=True)
    print(json.dumps(r.__dict__))
    return 0 if r.action != "error" else 1


def cmd_preview(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    data = build_superbill(_api(args), args.client_id, cfg)
    if data is None:
        print("no completed, billable visits in the episode window", file=sys.stderr)
        return 1
    with open(args.out, "wb") as f:
        f.write(render_pdf(data, cfg))
    print(json.dumps({"out": args.out, "visits": len(data.lines), "total_charges": data.total_charges,
                      "total_billed": data.total_billed, "total_payments": data.total_payments,
                      "balance": data.balance, "payment_plan": data.payment_plan}))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import serve

    cfg = load_config(args.config)
    serve(SuperbillSync(_api(args), cfg, dry_run=args.dry_run), port=args.port)
    return 0


def main(argv=None) -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="superbill")
    p.add_argument("--config", default=None, help="path to superbill_config.json")
    p.add_argument("--min-gap", type=float, default=None, help="seconds between IntakeQ calls (default from INTAKEQ_MIN_SECONDS_BETWEEN_CALLS or 6)")
    p.add_argument("--dry-run", action="store_true", help="build and render but never upload/delete")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sync", help="refresh superbills for clients with newly completed visits")
    s.add_argument("--since-days", type=int, default=None)
    s.set_defaults(func=cmd_sync)

    r = sub.add_parser("rebuild", help="rebuild and upload one client's superbill")
    r.add_argument("--client-id", type=int, required=True)
    r.set_defaults(func=cmd_rebuild)

    v = sub.add_parser("preview", help="render one client's superbill to a local PDF")
    v.add_argument("--client-id", type=int, required=True)
    v.add_argument("--out", default="superbill_preview.pdf")
    v.set_defaults(func=cmd_preview)

    w = sub.add_parser("serve", help="HTTP endpoints for n8n")
    w.add_argument("--port", type=int, default=None)
    w.set_defaults(func=cmd_serve)

    args = p.parse_args(argv)
    return args.func(args)
