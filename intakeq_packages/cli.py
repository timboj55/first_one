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
from .ledger_export import merge_export_into_ledger, write_ledger_files
from .packages import PackageConfig, PackageLedger, build_ledger
from .sources import ApptPackageMap, PackagesExport

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


def cmd_ledger(args: argparse.Namespace) -> int:
    """Offline: rebuild the cockpit ledger from data/appt_packages.json + data/packages_all.csv. No API calls."""
    config = PackageConfig.load(args.config)
    appt_map = ApptPackageMap.load(args.appt_map)
    export = PackagesExport.load(args.export) if args.export else None
    ledgers = build_ledger(appt_map.as_appointments(), config)
    derived = merge_export_into_ledger(ledgers, export, config)
    paths = write_ledger_files(args.out, export, ledgers, derived)
    summary = {"appt_map_records": len(appt_map.records), "appt_map_mapping": appt_map.mapping,
               "export_rows": len(export.rows) if export else 0, "export_mapping": export.mapping if export else None,
               "export_missing_fields": export.missing_fields() if export else None,
               "package_instances": len(derived), "files": paths}
    json.dump(summary, sys.stderr, indent=2); print(file=sys.stderr)
    return 0


def cmd_nightly(args: argparse.Namespace) -> int:
    from .nightly import run_nightly
    config = PackageConfig.load(args.config)
    client = IntakeQClient(min_seconds_between_calls=args.pace)
    report = run_nightly(client, config, args.appt_map, args.export, args.out, since=args.since,
                         max_calls=args.max_calls, fetch_details=not args.trust_list)
    json.dump(report, sys.stdout, indent=2, default=str); print()
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Show how the cockpit files' columns/keys were detected, so the mapping can be pinned."""
    out = {}
    if args.export:
        e = PackagesExport.load(args.export)
        out["export"] = {"columns": e.columns, "mapping": e.mapping, "rows": len(e.rows), "missing": e.missing_fields()}
    if args.appt_map:
        m = ApptPackageMap.load(args.appt_map)
        out["appt_map"] = {"mapping": m.mapping, "records": len(m.records),
                           "with_package": sum(1 for r in m.records.values() if r.get("package_id"))}
    json.dump(out, sys.stdout, indent=2); print()
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

    def data_args(sp):
        sp.add_argument("--config", default="packages.json")
        sp.add_argument("--appt-map", default="data/appt_packages.json", help="cockpit appointment->package file")
        sp.add_argument("--export", default=None, help="PracticeQ Packages export CSV (data/packages_all.csv)")
        sp.add_argument("--out", default="data")

    lg = sub.add_parser("ledger", help="offline rebuild of the cockpit ledger CSVs (no API calls)")
    data_args(lg); lg.set_defaults(func=cmd_ledger)

    ni = sub.add_parser("nightly", help="incremental reconciliation via API, then rebuild ledger")
    data_args(ni)
    ni.add_argument("--since", help="yyyy-MM-dd; default = last run minus a day, or 2 days ago")
    ni.add_argument("--pace", type=float, default=8.0, help="seconds between API calls (8 = 7.5/min)")
    ni.add_argument("--max-calls", type=int, default=300)
    ni.add_argument("--trust-list", action="store_true", help="skip per-id GETs when list rows carry package fields")
    ni.set_defaults(func=cmd_nightly)

    ins = sub.add_parser("inspect", help="show detected column/key mapping for the cockpit files")
    ins.add_argument("--export"); ins.add_argument("--appt-map"); ins.set_defaults(func=cmd_inspect)

    s = sub.add_parser("settings", help="dump services / locations / practitioners")
    s.set_defaults(func=cmd_settings)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
