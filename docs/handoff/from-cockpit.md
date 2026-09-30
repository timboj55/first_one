# From the cockpit session

## 2026-09-30 (3) (relayed by the cloud session)

### Status
- Provisional purchases switched on in the cockpit (rules.PROVISIONAL_PURCHASES), commit 423def5 in ms-cockpit, cloud refresh image rebuilt, so the 3am run on 1 Oct is the first with the bridge on.
- Ledger gains a `provisional` column. Provisional rows are excluded from the UsedSessions comparison and never written to data/.
- STALE now comes from the ledger step: a provisional purchase older than 30 days, or a charge in the last 30 days still unplaced. The refresh's older export check is information only ("not yet in the export").
- On local 29 Sept data: 5 provisional rows (3 named invoices, 0 financed, 2 visits only), recent unplaceable charges 11 to 0, STALE currently on because the 2 visits-only rows are dated more than 30 days back.
- A one-time task on Tim's Mac messages you the 1 Oct counts at 8am ET.

### Decisions needed from Tim
- None.

### Questions for the cloud session
- None.

## 2026-09-30 (2) (relayed by the cloud session; the cockpit session still cannot push from the Mac)

### Status
- Tim gave the go for the measurement and a dry run only. Implemented in scripts/build_ledger.py behind --provisional-dry-run, off by default. Nothing written to data/, the ledger, the page or the bucket. Local data is the 29 Sept pull.
- With the switch off, the ledger is unchanged apart from the normal one-day cutoff move (only attended/booked/used/left columns differ from the 29 Sept file).
- Implementation note: invoice client matching uses ClientIdNumber (the numeric id the export and appointments use); ClientId on invoices is a GUID.

### Decisions needed from Tim
- Whether to switch provisional purchases on in the nightly refresh (cockpit chat).

### Answers to cloud questions (2026-09-30 reply)
2. InvoiceId vs interval-0: no link. 4,845 invoices, 175 payment plans, 174 of them with an interval-0 invoice. Of 14,029 package-charged appointments only 9 carry any InvoiceId, and none points at an interval-0 invoice; across all 2,378 appointments with an InvoiceId, none does. Interval-0 item descriptions: "Payment Plan (Month 1)" 171, "Payment Plan (Quarter 1)" 2, one "refund", one plan-name string. So 1d stays inference.
1. Dry run, 90-day lookback:
   Detector A (named sale): 38 candidate lines; 30 skipped as already a purchase in the export (same client and type within 14 days); 2 skipped Draft; 3 skipped Refunded (I also skip Refunded: a full refund drops a package per Tim's rule); 3 provisional rows created.
   Detector D (financed or unnamed): 4 recent groups of unplaceable charges; 2 already covered by an A row; 2 created, both dated at the first charge because no interval-0 invoice fell within 14 days (types: one 1-visit Maintenance Plan, one 3-months). No financed purchase in this window was missing from the export, since the export was merged 26 Sept.
   Newly assignable: charges in the last 30 days that cannot be placed go from 11 to 0.
   Counter comparison: provisional rows excluded, as specified.
   The two charge-only D rows are the weakest (no invoice evidence); they could be shared-family charges. I will flag D rows without an invoice separately in the STALE report.

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
