# Spec: provisional package purchases from invoice lines (cockpit change)

Owner decision 2026-09-30: approved as a bridge between PracticeQ Packages exports. Implemented
in the cockpit (ms-cockpit), not in this repo. The cockpit session has reviewed the block
below; its amendments at the end supersede the conflicting lines. Go/no-go is Tim's, given in
the cockpit chat.

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


---

## Amendments from the cockpit session (2026-09-30), accepted by the cloud session

a. **No writes to `data/packages_all.csv`, no change to `merge_packages.py`.** That file feeds
   renewal vs new-patient classification, revenue buckets and Completed POC and stays pure
   PracticeQ data. `build_ledger.py` derives provisional purchases in memory on every build
   from invoices minus the export and writes them only as ledger rows flagged provisional.
   Stateless and self-healing: once a real row exists within 14 days for the same ClientId and
   package type, the provisional one is no longer generated. The "move the links at merge"
   step is withdrawn because appointment assignment is recomputed from scratch each build.
b. **Swap log** = diff against the previous night's ledger: a provisional Id present yesterday
   and gone today is reported with the real row's TotalSessions vs the default used.
c. **Match on package type, not exact name.** Every name seen under one AppointmentPackageId
   is one type (renames exist), as the ledger already groups.
d. **Second detector for financed purchases**, which never name the package on the invoice
   (about 1 in 5 new purchases, "Payment Plan (Month 1)" lines): a client with charged
   appointments of type T that cannot be placed on any purchase gets a provisional purchase of
   type T, dated at the matching invoice within 14 days (a plan's interval-0 invoice, i.e.
   `ClientPaymentPlanInterval == 0`, or a named line), else at the first unplaced charge.
   Default sessions by name as above. Invoices sharing a `ClientPaymentPlanId` are one plan; a
   plan whose interval-0 invoice predates the window is continuation billing, not a purchase.

Unchanged: stable provisional Id, default session counts, expiry rules, exclusion from
Completed POC test 1 and the counter comparison, the `provisional` column, STALE rules, skip of
Draft and Canceled invoices. The public API offers no plan-to-package mapping (verified
2026-09-30), so detector (d) is inference by design.

## Refinements from the dry run (cockpit session, 2026-09-30 (2))

- Skip invoices with Status Refunded as well as Draft and Canceled: a full refund drops a
  package.
- Match invoice clients on `ClientIdNumber` (the numeric id shared with the export and
  appointments); `ClientId` on invoices is a GUID.
- Detector D rows with no invoice evidence (dated at the first unplaced charge) are flagged
  separately in the STALE report; they may be shared-family charges.
- Measured: appointments on this tenant almost never carry an `InvoiceId` (9 of 14,029
  package-charged), and none points at a plan's interval-0 invoice, so detector D remains
  inference by design.
- Dry run over a 90-day lookback with the export merged four days earlier: 3 A rows, 2 D rows,
  unplaceable charges in the last 30 days 11 -> 0, counter comparison unaffected. Implemented
  behind `--provisional-dry-run` in `scripts/build_ledger.py`, off by default; switching it on
  in the nightly refresh is the owner's decision in the cockpit chat.

## Live (cockpit session, 2026-09-30 (3))

Switched on in the cockpit (`rules.PROVISIONAL_PURCHASES`, ms-cockpit commit 423def5, refresh
image rebuilt). First nightly run with the bridge on: 3am ET, 1 Oct 2026. STALE now comes from
the ledger step (a provisional purchase older than 30 days, or a charge in the last 30 days
still unplaced); the older export check is informational. On 29 Sept data: 5 provisional rows
(3 named invoices, 2 visits-only), unplaceable recent charges 11 -> 0.
