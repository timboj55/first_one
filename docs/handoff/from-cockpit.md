# From the cockpit session

## 2026-09-30 (relayed: the cockpit session could not push, no GitHub sign-in on the Mac; committed verbatim by the cloud session)

### Status
- Read PROTOCOL.md, from-cloud.md (2026-09-30) and docs/provisional-purchases-spec.md.
- Cockpit state: refresh runs in Google Cloud (Cloud Run job, 3am daily, plus refresh when the team page is opened more than 30 minutes stale). The Mac routine is disabled. The ledger is scripts/build_ledger.py, rebuilt every refresh into series/packages_ledger.csv.
- Nothing implemented from the spec yet. I take build instructions from Tim in the cockpit chat, not through this channel, so the provisional bridge starts when he says go there.

### Decisions needed from Tim
- Go/no-go on the provisional bridge, in the cockpit chat, with the design changes below.

### Answers to cloud questions (2026-09-30)
1. Mostly fits. Four changes before I implement:
   a. Do NOT write provisional rows into data/packages_all.csv or touch merge_packages.py. That file feeds more than the ledger (renewal vs new-patient classification, revenue buckets, Completed POC) and must stay pure PracticeQ data. Instead build_ledger.py derives provisional purchases in memory each night from invoices minus the export and writes them only as ledger rows flagged provisional. Stateless and self-healing: once a real row arrives within 14 days (same ClientId, same package type), the provisional one stops being generated. No "move the links" step, because appointment assignment is recomputed from scratch every build.
   b. Swap log: compare against the previous night's ledger; a provisional Id present yesterday and gone today is reported with the real row's TotalSessions vs the default.
   c. Match on package TYPE, not exact name: every name seen under one AppointmentPackageId is one type (renames exist), which is how the ledger already groups.
   d. Financed purchases are invisible to name matching (see 2). Add a second detector: a client with charged appointments of type T that cannot be placed on any purchase gets a provisional purchase of type T, dated at the matching invoice (Payment Plan Month 1 or a named line) within 14 days, else at the first unplaced charge. Default sessions by name as in the spec.
   Everything else in the spec stands: stable Id, default session counts, expiry rules, excluded from Completed POC and the counter comparison, provisional column, STALE rules. Data note: invoices_all.csv is one row per invoice with a joined Description; line items and ClientPaymentPlanId are in the raw API copy. Skip Status Draft and Canceled.

2. Last 90 days of invoices (from 2026-07-02): 141 invoices. Matched one of the eleven names: 38 lines (12-Visit 14, 8-Visit 10, 20-Visit 8, Complimentary Visit 2, 4-visit Extension 2, 2-visit Progression Plan 1, 1-visit Maintenance Plan 1). No Custom, 3-months or 2-months in the window. Distinct descriptions that do NOT match: Initial Consultation (61); Payment Plan (Month 1) 11, Month 2 7, Month 3 5, Month 4 4, Month 5 3, Month 6 4, Months 13, 14, 22, 23 one each, Payment Plan (Quarter 1) 1; refund 2, Refund 1. No aliases needed for package names. The real gap is "Payment Plan (Month 1)": 11 new financed purchases whose invoice never names the package (raw copy: one item, description only, AppointmentId null), about 1 in 5 new purchases. Hence 1d. Month 1 is also used by continuation billing, so it is a signal, not proof.

3. Yes, one docs lookup: is there an endpoint or field that maps ClientPaymentPlanId (on invoices) to the package it finances, or any invoice item field carrying a package Id? If so, financed purchases get named without the inference in 1d.

(Write dated entries at the top. See PROTOCOL.md.)
