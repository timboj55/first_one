"""CLI: python -m intakeq_packages report --config packages.json --since 2025-01-01 --out out/

Pulls appointments (and optionally invoices) through the public API and writes a package
ledger as JSON and CSV. Watch the request budget: each 100 rows is one call, and the standard
plan allows 500 calls/day.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import List

from .client import IntakeQClient
from .packages import PackageConfig, PackageLedger, build_ledger

CSV_COLUMNS = [
    "client_name", "client_email", "client_id", "package_name", "status", "sessions_total", "used",
    "scheduled", "remaining", "purchase_date", "expires_on", "purchase_invoice_number", "purchase_amount",
    "first_booked", "last_appointment", "package_instance_id", "warnings",
]


def write_outputs(ledgers: List[PackageLedger], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "packages.json"), "w") as f:
        json.dump([l.to_dict() for l in ledgers], f, indent=2)
    with open(os.path.join(out_dir, "packages.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for l in ledgers:
            row = l.to_dict()
            row["warnings"] = "; ".join(row["warnings"])
            w.writerow(row)


def cmd_report(args: argparse.Namespace) -> int:
    config = PackageConfig.load(args.config)
    client = IntakeQClient()
    appts = list(client.appointments(client=args.client, start_date=args.since, end_date=args.until,
                                     practitioner_email=args.practitioner))
    invoices = []
    if not args.skip_invoices:
        invoices = list(client.invoices(start_date=args.since, end_date=args.until,
                                        practitioner_email=args.practitioner))
    ledgers = build_ledger(appts, config, invoices)
    write_outputs(ledgers, args.out)
    print(f"{len(appts)} appointments, {len(invoices)} invoices, {len(ledgers)} package instances, "
          f"{client.calls_made} API calls -> {args.out}/packages.{{json,csv}}", file=sys.stderr)
    for l in ledgers:
        if l.status != "active" or (l.remaining is not None and l.remaining <= 1):
            print(f"  {l.client_name:30} {l.package_name:25} {l.status:20} remaining={l.remaining}", file=sys.stderr)
    return 0


def cmd_settings(args: argparse.Namespace) -> int:
    json.dump(IntakeQClient().booking_settings(), sys.stdout, indent=2)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="intakeq_packages")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="build the package ledger from appointments + invoices")
    r.add_argument("--config", default="packages.json")
    r.add_argument("--since", help="yyyy-MM-dd; earliest appointment/invoice date to pull")
    r.add_argument("--until", help="yyyy-MM-dd")
    r.add_argument("--client", help="name or email filter (partial match)")
    r.add_argument("--practitioner", help="practitioner email filter")
    r.add_argument("--skip-invoices", action="store_true", help="save API calls; purchase date falls back to first booking")
    r.add_argument("--out", default="out")
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("settings", help="dump services / locations / practitioners")
    s.set_defaults(func=cmd_settings)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
