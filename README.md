# PracticeQ / IntakeQ package data via API

**Short answer:** IntakeQ's public API has **no packages endpoint**. There is no way to ask
"what packages does client X own and how many sessions are left". But package data *is*
reachable through two documented feeds, and from those a full per-client package ledger can be
rebuilt automatically. This repo contains the findings and a working, stdlib-only Python
implementation that does it.

## What the public API exposes (verified against the official docs, Sept 2026)

Base URL `https://intakeq.com/api/v1`, header `X-Auth-Key: <key>`. Key is under
**More > Settings > Integrations > Developer API** (main account owner only, paid plan only,
one active key at a time; generating a new key invalidates the old one). Timestamps are
**Unix milliseconds**. The API category on the support site lists exactly nine articles
(Questionnaire, Client, Appointments, Partner, Notes, Invoice, Rate Limits, Claims, Files).
None is a packages API.

Rate limits: **10 requests/minute, 500/day** included. Self-service upgrade under
Developer API > Settings > Select Maximum Requests: **$25/month per extra 10 req/min, no
daily cap once upgraded, max 250 req/min**, changeable once a month. List endpoints return
**100 rows per page** (`page=N`). **Webhooks are not rate limited**, but only one webhook
URL is supported, so fan out from your own receiver.

| Resource | Endpoints | Package-relevant data |
|---|---|---|
| Appointments | `GET /appointments` (filters: `client`, `startDate`, `endDate`, `status`, `practitionerEmail`, `updatedSince`, `deletedOnly`, `page`), `GET /appointments/{id}`, `POST/PUT /appointments`, `POST /appointments/cancellation`, `GET /appointments/settings` | **`AppointmentPackageId`** and **`AppointmentPackageName`** are present on `GET /appointments/{id}` only; the list endpoint returns no package fields (measured live on this tenant: 44 fields on the list, 49 on the single). **The id is the package *type*, not the purchase**: 19 distinct ids across 20,210 appointments, none matching a purchase id in the PracticeQ export, and one id carries several names after a rename. Also `InvoiceId` / `InvoiceNumber`, `FullCancellationReason`, `CancellationDate`, `LastModified` |
| Invoices | `GET /invoices` (filters: `clientId`, `startDate`, `endDate`, `status`, `practitionerEmail`, `number`, `lastUpdatedStartDate`, `lastUpdatedEndDate`, `page`), `GET /invoices/{id}` | Line `Items[]` with `Description`, `Price`, `Units`, `TotalAmount`, `ProductId`, `AppointmentId`; `Status`, `IssuedDate`, `Payments[]`, `ClientPaymentPlanId` (set when the package is on a recurring payment plan). A package sale is a line item whose Description names the package. |
| Clients | `GET /clients` (`search`, `includeProfile`, `page`), `POST /clients`, `POST/DELETE /clientTags`, `GET /client/{id}/diagnoses` | No package fields. `CreditBalance` is exposed. Tags are useful as an *output*: tag clients "package-1-left" and let PracticeQ automations act on it. |
| Intakes, Notes, Files, Claims, Practitioners, Questionnaires | documented separately | nothing package related |
| Webhooks (same settings page) | `AppointmentCreated/Confirmed/Rescheduled/Canceled/Declined/Missed/Deleted`, `InvoiceIssued/Paid/Cancelled/PaymentRefunded/PaymentPlanChargeFailed/AutoChargeFailed`, intake submitted, note locked | Appointment events carry the **full appointment object including the package fields**; invoice events carry the full invoice. This is the real-time path. |
| Booking widget JS | `intakeqPackageSignUp` DOM event | fires in the browser when a visitor buys a package; front-end only |

What is **not** exposed anywhere: the **purchase** itself (the export's `Id`), sessions sold
on that purchase (`TotalSessions`, wrong by name on 54 of 1,137 packages), PracticeQ's own
`UsedSessions` / `UnusedSessions` counters, and the purchase `Status`. Package definitions and
per-client expiry overrides are also UI-only. `GET /appointments/settings` returns Services,
Locations and Practitioners only. `GET /packages` and `GET /client-packages` return 404.

## What can and cannot be automated (reconciled with the cockpit, 2026-09-30)

Automated already, by the cockpit: per-purchase usage, inferred by assigning each charged
appointment (from `GET /appointments/{id}`) to the same client's oldest purchase of that
package type with sessions left, plus the ledger built from that and the export.

Not automatable through the API: the PracticeQ Packages export (`data/packages_all.csv`),
because the purchase record, its sold-session count, PracticeQ's used/unused counters and
its cancellation status exist only there. The export is a rolling 2,000-row window, so it
must be merged, never copied. Today it is downloaded by hand and merged with
`scripts/merge_packages.py`; the nightly refresh prints STALE when a package charged in the
last 30 days is missing.

Routes considered:

- **Support request for a packages endpoint** (`docs/intakeq-support-request.md`): the only
  route that removes the manual export. **Sent by the owner on 2026-09-30.** Reply pending.
- **Provisional purchase rows from invoice lines** the night the invoice appears, with a
  name-based session count, replaced by the real record at the next export. Narrows the
  export to monthly housekeeping. Costs: name-based count wrong about 5% of the time, about
  11% of purchases have no matching invoice line, and provisional rows carry no PracticeQ
  counters so Completed POC still waits for the export. Implemented in the cockpit's
  `build_ledger.py` (spec and dry-run results in `docs/provisional-purchases-spec.md`);
  **owner approved switching it on in the nightly refresh on 2026-09-30.**
- **Headless browser download of the export at 4am**: closes the gap but needs a stored
  PracticeQ login with full patient access, breaks silently on UI changes, and the refresh
  now runs in Google Cloud, not on the Mac. Rejected.

## Status

Handed over to the cockpit on 2026-09-30. Nothing runs from this repository; it is the
reference for the IntakeQ API surface and the record of how the packages question was
settled (`docs/handoff/`, `docs/provisional-purchases-spec.md`,
`docs/intakeq-support-request.md`).

## Decisions (practice owner, 2026-09-30)

- The package ledger is built by the cockpit itself (`gs://ms-cockpit-data/series/packages_ledger.csv`,
  rebuilt at 3am and when a page is more than 30 minutes stale). Session counts are **not**
  re-derived here, and that file is not read from outside Google Cloud without approval.
- No real-time package signal. The existing n8n workflow "IntakeQ Appointments -> GHL" owns the
  PracticeQ appointment webhook; nothing is added to it and no receiver is built.
- The ledger builder, nightly reconciliation, webhook receiver, n8n drafts and Cowork task that
  were drafted earlier are superseded and removed. They remain in git history at commit
  `db839bf` if ever needed.
- Live use of the API from Claude Code is read-only.

## What remains in this repo

```
intakeq_packages/client.py   throttled, paginated, retrying read-only client (appointments,
                             invoices, clients, practitioners, booking settings)
intakeq_packages/cli.py      python -m intakeq_packages verify | settings
tests/                       4 unit tests (python -m unittest discover -s tests)
```

## Credentials in the Claude Code environment

Decision (2026-09-30): no Claude cloud session has any remaining reason to call PracticeQ or
n8n for this project. The cockpit holds its own PracticeQ key in Google Secret Manager
(`cockpit-intakeq-key`) and needs nothing from the Claude Code environment.

Done 2026-09-30 by the owner:
- `INTAKEQ_API_KEY` API credential removed from the "Default" environment. It was never sent
  as `X-Auth-Key` (one read-only `GET /practitioners` returned 401).
- `N8N_API_KEY` API credential removed (it worked: one read-only workflow list returned 200).
- The unused n8n Header Auth credential "IntakeQ API (X-Auth-Key)" deleted in n8n.
- `N8N_BASE_URL` environment variable and the Trusted network setting left unchanged.
- A separate API credential named "IntakeQ/PracticeQ" of unknown origin also existed in the
  environment; recommended for removal on the same least-privilege grounds. Any future cloud
  project that needs PracticeQ adds its own credential with header `X-Auth-Key`.

If a cloud project ever needs PracticeQ again: add an API credential scoped to intakeq.com
with header name exactly `X-Auth-Key` and the bare key as value, then run
`python -m intakeq_packages verify` (one read-only call). `IntakeQClient` also accepts an
`INTAKEQ_API_KEY` environment variable and sends the header itself, for use elsewhere.

## Tenant facts

- PracticeQ Developer API: "Enable API access" on; no IP allow-list field on the page; the
  account is on 20 requests/minute. The appointment webhook URL points at the n8n workflow
  "IntakeQ Appointments -> GHL" (all 8 events); intake, note and invoice webhooks go to
  listen.partyline.to. None of these are to be changed.
- n8n 2.20.9 self-hosted; Data Table and Read/Write Files from Disk nodes exist, Execute Command
  does not. A Header Auth credential "IntakeQ API (X-Auth-Key)" exists in n8n and is unused.
- The cockpit is a local folder on the owner's Mac (`ms-cockpit`), refreshed by the local Claude
  desktop routine "Cockpit nightly refresh, 4am".

## Alternatives considered

- **Ask PracticeQ for a packages endpoint**: support is the only route; they do extend the
  API (cancellation fields Dec 2024, Claims API Oct 2023, Resend Intake). Rate limit
  increases are self-service now, see above.
- **Per Client Summary CSV export / Bookings > Packages page scraped with a headless
  browser**: gives PracticeQ's own remaining count, but it is brittle, session-cookie based
  and not something to build a 100% automated pipeline on. Fallback only.
- **Zapier / Make / n8n**: none has an official IntakeQ app; they all end up calling the
  same REST endpoints above, so they do not unlock anything extra.

## Sources

- IntakeQ API index: https://support.intakeq.com/category/560-api
- Appointments API: https://support.intakeq.com/article/204-intakeq-appointments-api
- Invoice API: https://support.intakeq.com/article/385-intakeq-invoice-api
- Client API: https://support.intakeq.com/article/251-intakeq-client-api
- Appointment Packages (product behaviour): https://support.intakeq.com/article/78-appointment-packages
- API Rate Limits: https://support.intakeq.com/article/711-api-rate-limits
- Automated Package Emails: https://support.intakeq.com/article/223-automated-package-emails
- Booking widget JS events: https://support.intakeq.com/article/243-booking-widget-javascript-events
- Community OpenAPI profile: https://github.com/api-evangelist/intakeq
- TypeScript client with full field typings: https://github.com/LifeBac/intakeq-api

---

# Lead follow-up agent (after hours + busy hours) for GoHighLevel

`lead_agent/` is a separate service in this repo: it texts and calls new GHL leads when the
team can't, and books the Cost & Availability call on the GHL calendar. SMS runs on Claude
through the GHL Conversations API; voice runs on Retell AI with the same booking tools.
Setup, GHL workflow wiring, Retell setup, compliance notes and testing steps are in
[docs/LEAD_AGENT_SETUP.md](docs/LEAD_AGENT_SETUP.md).

```
lead_agent/
  orchestrator.py  engage-now decision (after hours / busy / team silent), cadence, stop rules
  brain.py         Claude SMS conversation with tools (slots, book, hand off, outcome)
  tools.py         the booking tools, shared by text and voice
  voice.py         Retell: outbound calls, agent definition from config, signed webhooks
  ghl.py           GHL API client (contacts, SMS, free slots, appointments, notes, tags)
  hours.py         business hours, quiet hours, call window, lead-local time
  server.py        webhooks: /webhooks/ghl/<secret>/{new-lead,inbound-message,appointment-booked}, /voice/*
  scheduler.py     job runner (deferred touches, retries)
agent_config.json  practice config: tone, FAQ, hours, cadence, tags, voice settings
tests/test_lead_agent.py  29 tests with fake GHL / Claude / Retell
```

```bash
pip install -r requirements.txt
python3 -m lead_agent check        # env + calendar sanity check
python3 -m lead_agent serve        # webhooks + scheduler
python3 -m lead_agent setup-voice  # create/update the Retell agent from agent_config.json
python3 -m lead_agent simulate     # chat with the SMS brain locally
```

---

# Booking summary PDF (n8n)

`n8n/appointment-summary/` is an importable n8n workflow that uploads a PDF of all a patient's
upcoming appointments to their PracticeQ client file (replacing the previous one), 30 minutes after their last booking or
schedule change (the buffer for catching scheduling mistakes). It is separate from the
"IntakeQ Appointments -> GHL" workflow and does not touch the PracticeQ webhook. Setup and
behaviour: [docs/APPOINTMENT_SUMMARY_SETUP.md](docs/APPOINTMENT_SUMMARY_SETUP.md).
Tests: `node --test n8n/appointment-summary/test.mjs`.
