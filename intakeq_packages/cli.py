"""CLI: python -m intakeq_packages verify | settings

verify   one GET /practitioners; prints the HTTP outcome and a count, never names or keys.
settings GET /appointments/settings; prints counts of services / locations / practitioners.
"""

from __future__ import annotations

import argparse
import sys

from .client import IntakeQClient, IntakeQError


def cmd_verify(args: argparse.Namespace) -> int:
    client = IntakeQClient(min_seconds_between_calls=0)
    mode = "env-var key" if client.api_key else "proxy-injected credential"
    try:
        rows = client.practitioners()
    except IntakeQError as e:
        print(f"auth mode: {mode}; GET /practitioners -> HTTP {e.status}", file=sys.stderr)
        return 1
    print(f"auth mode: {mode}; GET /practitioners -> HTTP 200; practitioners: {len(rows)}", file=sys.stderr)
    return 0


def cmd_settings(args: argparse.Namespace) -> int:
    s = IntakeQClient(min_seconds_between_calls=0).booking_settings()
    for k in ("Services", "Locations", "Practitioners"):
        print(f"{k}: {len(s.get(k) or [])}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="intakeq_packages")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify", help="one read-only GET /practitioners to confirm auth").set_defaults(func=cmd_verify)
    sub.add_parser("settings", help="counts of services / locations / practitioners").set_defaults(func=cmd_settings)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
