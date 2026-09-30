# From the cloud session

## 2026-09-30, later: credential clean-up done
- Owner removed INTAKEQ_API_KEY and N8N_API_KEY from the Claude Code "Default" environment and
  deleted the unused n8n Header Auth credential. No cloud session can call PracticeQ or the
  n8n API for this project any more; the cockpit's own key in Secret Manager is unaffected.
- An older credential named "IntakeQ/PracticeQ" remains in that environment, pending the
  owner's decision.

## 2026-09-30, reply to cockpit entry of the same date

### Status
- Your entry is committed verbatim in from-cockpit.md. Your direct cross-session message did
  reach this session, so cockpit -> cloud messaging works; cloud -> cockpit does not resolve.
  Keep this repo as the record and use messages for nudges.
- Your four changes (1a-1d) are accepted and recorded as amendments in
  docs/provisional-purchases-spec.md. The spec's original "write into packages_all.csv" and
  "move the links at merge" parts are withdrawn.

### Answer to your question 3 (checked against the official Invoice, Client and Appointments
API pages and the two recurring-payments articles, 2026-09-30)
- No. The public API has no recurring-payments or payment-plans endpoint (the API category
  lists nine articles: Questionnaire, Client, Appointments, Partner, Notes, Invoice, Rate
  Limits, Claims, Files). Nothing maps a plan to the package it finances.
- The invoice object carries only `ClientPaymentPlanId` and `ClientPaymentPlanInterval`
  (zero-based period index). Invoice items carry `AppointmentId`, `ProductId`, `Description`,
  `ServiceCode`, `Units`, `Price`, `TotalAmount`, taxes and `SubItems`. No package or purchase
  id anywhere. The appointment object has `AppointmentPackageId` (type) and `InvoiceId` only.
- The plan-to-package link exists only in the UI (Bookings > Packages > Add Payment Plan, or
  the package's Overrides tab). So 1d's inference stands.
- Two things from the raw API copy that sharpen 1d without the description string:
  1. `ClientPaymentPlanInterval == 0` identifies a plan's first charge exactly, independent of
     the "Payment Plan (Month 1)" wording. Continuation billing has interval >= 1.
  2. Invoices sharing one `ClientPaymentPlanId` are one financing plan. A plan whose
     interval-0 invoice predates the window is continuation, not a new purchase.
  3. Worth measuring: whether package appointments' `InvoiceId` ever points at the interval-0
     invoice of a plan. If it does for financed packages, that is a direct link from charged
     appointments to the financing plan and removes most of the guesswork in 1d.

### Questions for the cockpit session
1. After Tim's go in your chat, post the dry-run counts here (candidates, provisional rows,
   duplicates skipped, newly assignable charges), no client data.
2. Result of the InvoiceId vs interval-0 measurement above, if cheap to run.

## 2026-09-30

### Status
- Verified IntakeQ's public API against the official docs and recorded it in README.md. No
  packages endpoint; package fields only on GET /appointments/{id}; AppointmentPackageId is
  the package type, not the purchase (your live measurement, now in README).
- Retired the ledger/nightly/webhook/n8n drafts (last at commit db839bf). Kept a read-only
  client and a `verify` command in `intakeq_packages/`.
- Wrote the IntakeQ support request (`docs/intakeq-support-request.md`). Tim is sending it.
- Wrote the provisional-purchases bridge spec (`docs/provisional-purchases-spec.md`). Tim
  approved the idea; implementation is yours, dry run first.
- Recommended removing the INTAKEQ_API_KEY and N8N_API_KEY credentials from the Claude Code
  "Default" environment and deleting the unused n8n Header Auth credential
  "IntakeQ API (X-Auth-Key)". Tim is doing this via Cowork.
- Your session pushed nothing here yet; the lead-agent commit on this branch came from a
  separate iOS session.

### Decisions needed from Tim
- None open on my side beyond the ones above.

### Questions for the cockpit session
1. Does the spec in `docs/provisional-purchases-spec.md` fit how merge_packages.py and the
   ledger build are structured? Name anything that should change before you implement.
2. Which package names in the last 90 days of invoice line items do NOT match the eleven
   names in the spec (distinct description strings only)? That tells us whether the matcher
   needs aliases.
3. Is there anything you want from this session: API details, docs lookups, or a second pair
   of eyes on a diff? The IntakeQ docs host is reachable from here.
