# Spec: provisional package purchases from invoice lines (cockpit change)

Owner decision 2026-09-30: approved as a bridge between PracticeQ Packages exports. Implemented
in the cockpit (ms-cockpit), not in this repo. Paste the block below into the
"Movement Solutions Cockpit repo" session.

---

Implement provisional package purchases as a bridge between Packages exports. Dry run first,
report counts, and do not write anything until I approve.

Goal: the night a package sale appears on an invoice, create a placeholder purchase so
appointments can be assigned to it, then replace it with the real PracticeQ row at the next
export merge. Never overwrite or invent PracticeQ's UsedSessions/UnusedSessions.

Detection, in the nightly refresh after the invoice pull:
- Candidate = an invoice line item whose Description contains one of the known package names
  (case-insensitive): 20-Visit Package, 12-Visit Package, 8-Visit Package, Custom,
  4-visit Extension, 2-visit Progression Plan, Quarterly Check-in w/ Programming,
  1-visit Maintenance Plan, Complimentary Visit, 3-months, 2-months.
- Skip if the invoice Status is Draft or Canceled.
- Skip if a purchase already exists for the same ClientIdNumber and PackageName with
  DateCreated within 14 days of the invoice IssuedDate, whether real or provisional.

Provisional row, same columns as the export:
- Id: "prov:" + invoice Id + ":" + line index (stable across nights)
- ClientId, ClientName: from the invoice
- PackageName: the matched name
- DateCreated: invoice IssuedDate
- Status: "Provisional"
- Paid: true if invoice Status is Paid, else false
- InvoiceNumbers: the invoice Number
- TotalSessions: default by name: 20, 12, 8, Custom 10, 4, 2, 1, 1, 1, 3-months 16,
  2-months 12
- UsedSessions, UnusedSessions: empty
- ExpiryDate: DateCreated + 364 days for 20-Visit, 12-Visit, 8-Visit and Custom;
  DateCreated + 95 days for 3-months; empty for the rest
- Practitioner: invoice practitioner if the invoice carries one, else empty

Use in the ledger:
- Provisional rows take part in appointment assignment exactly like real purchases (same
  client, oldest purchase of that type with sessions left, 14 days before purchase to expiry).
- Add a boolean column provisional to packages_ledger.csv.
- Exclude provisional rows from Completed POC test 1 and from the PracticeQ counter comparison;
  those wait for the export.

Replacement at export merge (scripts/merge_packages.py):
- A real export row with the same ClientId and PackageName and DateCreated within 14 days of
  the provisional row's DateCreated supersedes it: move the provisional row's appointment links
  to the real Id, delete the provisional row, and log the swap including any difference in
  TotalSessions.
- If no real row matches after 45 days, keep the provisional row and list it in the STALE
  report as "provisional, unmatched".

STALE signal: keep printing STALE when a package charged in the last 30 days has no purchase,
real or provisional. A provisional row older than 30 days also triggers STALE, so the export
stays monthly.

Report on the dry run: candidate lines found, provisional rows that would be created,
skipped-as-duplicate count, and how many of the last 30 days' charged packages would become
assignable. No client names in the report.
