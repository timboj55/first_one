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
| Appointments | `GET /appointments` (filters: `client`, `startDate`, `endDate`, `status`, `practitionerEmail`, `updatedSince`, `deletedOnly`, `page`), `GET /appointments/{id}`, `POST/PUT /appointments`, `POST /appointments/cancellation`, `GET /appointments/settings` | **`AppointmentPackageId`** (unique per purchased package instance) and **`AppointmentPackageName`** on every appointment, plus `ClientId`, `Status`, `StartDate`, `DateCreated`, `Price`, **`InvoiceId` / `InvoiceNumber`** (the invoice the appointment was billed on, which for prepaid package appointments is the package sale), `FullCancellationReason`, `CancellationDate`, `LastModified` |
| Invoices | `GET /invoices` (filters: `clientId`, `startDate`, `endDate`, `status`, `practitionerEmail`, `number`, `lastUpdatedStartDate`, `lastUpdatedEndDate`, `page`), `GET /invoices/{id}` | Line `Items[]` with `Description`, `Price`, `Units`, `TotalAmount`, `ProductId`, `AppointmentId`; `Status`, `IssuedDate`, `Payments[]`, `ClientPaymentPlanId` (set when the package is on a recurring payment plan). A package sale is a line item whose Description names the package. |
| Clients | `GET /clients` (`search`, `includeProfile`, `page`), `POST /clients`, `POST/DELETE /clientTags`, `GET /client/{id}/diagnoses` | No package fields. `CreditBalance` is exposed. Tags are useful as an *output*: tag clients "package-1-left" and let PracticeQ automations act on it. |
| Intakes, Notes, Files, Claims, Practitioners, Questionnaires | documented separately | nothing package related |
| Webhooks (same settings page) | `AppointmentCreated/Confirmed/Rescheduled/Canceled/Declined/Missed/Deleted`, `InvoiceIssued/Paid/Cancelled/PaymentRefunded/PaymentPlanChargeFailed/AutoChargeFailed`, intake submitted, note locked | Appointment events carry the **full appointment object including the package fields**; invoice events carry the full invoice. This is the real-time path. |
| Booking widget JS | `intakeqPackageSignUp` DOM event | fires in the browser when a visitor buys a package; front-end only |

What is **not** exposed anywhere: the package *definitions* (sessions per package, price,
expiry window), per-client expiry overrides made on the Package List page, and PracticeQ's
own "sessions remaining" counter that drives its Package Sessions About to End email.
`GET /appointments/settings` returns Services, Locations and Practitioners only.

## How to get to 100% automation anyway

1. **Mirror the package definitions once** in `packages.json` (name -> sessions, validity).
   They change rarely and only you change them.
2. **Group appointments by `AppointmentPackageId`.** Each id is one purchased package
   instance. Past `Confirmed` + `Missed` = used; future `Confirmed` / `WaitingConfirmation` =
   scheduled; `Declined` is free. **`Canceled` counts as used**: PracticeQ's own docs say a
   canceled package appointment is not replenished unless staff add the slot back. If your
   staff always re-add slots, drop `Canceled` from `count_as_used` in `packages.json`.
   `remaining = sessions - used - scheduled`.
3. **Join the sale from invoices.** First choice is the `InvoiceId` on the package
   appointments themselves; fallback is same client + line-item Description containing the
   package name, closest issue date before the first booking. That gives purchase date,
   invoice number and amount. Expiry = purchase date + validity days.
4. **Keep it live with webhooks.** Every package booking, cancellation, no-show and sale
   arrives as a POST within seconds, so the ledger never needs a full re-pull. Use the
   nightly `report` run only as reconciliation.
5. **Write results back** as client tags or into your cockpit's datastore.

Caveat on step 2: sessions a client bought but has not yet scheduled do not exist as
appointments, which is exactly why the definition mirror in step 1 is required. If you
sell packages with flexible session counts, the invoice `Units` field is the next best
signal.

## Cockpit integration requirements (from the practice owner, 2026-09-26)

- **Session counts come from each purchase, not the package name.** The PracticeQ Packages
  export (`data/packages_all.csv` in the cockpit repo) is the source of truth for a package
  instance's total; `packages.json` holds name-level defaults only as a fallback.
- **Cancellations and no-shows count as consumed only while still linked to the package.**
  Released cancellations lose their `AppointmentPackageId` and drop out of the ledger on
  their own; charged ones keep it and count. This is what `count_as_used` including
  `Canceled` and `Missed` implements. Since Jan 2025: 77 of 845 cancellations and 21 of 36
  no-shows stayed linked.
- **Output is a CSV with the same columns as the PracticeQ Packages export**, so the cockpit
  can diff it against the current file before adopting it. PracticeQ's own `UnusedSessions`
  is never overwritten: it counts bookings and feeds the cockpit's Completed POC logic.
- **The cockpit already maintains `data/appt_packages.json`** (appointment to package, 20k
  rows, topped up nightly). Reuse it rather than re-pulling history.
- **Per-appointment package fields may only be on `GET /appointments/{id}`**, not the list
  endpoint or the webhook payload. To be confirmed on the live run; if true, the webhook
  handler and the nightly job must fetch each changed appointment individually.
- **Real time via self-hosted n8n** with a secret-protected webhook URL, plus a nightly
  reconciliation pull finishing before 4:00am ET. The tenant's API limit is 20 requests per
  minute, shared with the cockpit refresh at 4:06am ET. Any new n8n workflow needs the
  owner's approval before activation, and the ledger's storage location is agreed first.

## This implementation

```
intakeq_packages/
  client.py         throttled, paginated, retrying client for /appointments, /invoices, /clients, /clientTags
  packages.py       build_ledger(appointments, config, invoices) -> per-package-instance ledger
  sources.py        tolerant loaders for the cockpit's packages_all.csv and appt_packages.json
  ledger_export.py  export-compatible packages_ledger.csv + packages_ledger_derived.csv sidecar
  nightly.py        incremental reconciliation with pacing, call budget and 03:55 ET hard stop
  webhook.py        receiver: secret URL path, enrich thin payloads via GET /appointments/{id}
  cli.py            report | ledger | nightly | inspect | settings
n8n/
  intakeq-package-webhook-receiver.json        importable draft (inactive)
  intakeq-package-nightly-reconciliation.json  importable draft (inactive)
  push_workflows.py                            create/update both via the n8n public API, inactive
docs/RUNBOOK.md   setup, storage, budgets, approval steps
tests/            19 unit tests on synthetic payloads (python -m unittest discover -s tests)
packages.json     the practice's package defaults (fallback; per-purchase totals come from the export)
```

Offline, with the cockpit files present:

```bash
python3 -m intakeq_packages inspect --export data/packages_all.csv --appt-map data/appt_packages.json
python3 -m intakeq_packages ledger --appt-map data/appt_packages.json --export data/packages_all.csv --out data
```

Quick start (ad-hoc API pull):

```bash
cp .env.example .env                                             # set INTAKEQ_API_KEY
export $(grep -v '^#' .env | xargs)
python -m intakeq_packages settings                              # sanity-check the key
python -m intakeq_packages report --since 2026-01-01 --out out   # writes out/packages.{json,csv}
python -m intakeq_packages.webhook 8080                          # prints normalised package events
```

Ledger row fields: `client_name, client_email, client_id, package_name, status
(active|exhausted|expired|unknown-definition), sessions_total, used, scheduled, remaining,
purchase_date, expires_on, purchase_invoice_number, purchase_amount, first_booked,
last_appointment, package_instance_id, appointment_ids, warnings`.

Request budget: a practice with 3,000 appointments and 1,500 invoices a year is about 45
calls for a full annual pull, well inside 500/day. Use `--since` and the `updatedSince`
filter for incremental runs.

## Not yet run against a live account

Endpoints, fields, parameter names, event types and timestamp units were checked against
the official support articles (Appointments API updated Aug 2026, Invoice API Jun 2025,
Rate Limits Sep 2026, Appointment Packages May 2026). The code has not yet been run against
a real PracticeQ tenant. First live run should confirm: that prepaid package appointments
carry the package sale's `InvoiceId`, the exact `Description` PracticeQ writes on a package
invoice line, and whether re-added canceled slots create a new appointment while the
canceled one keeps its `AppointmentPackageId` (which would double count under the default
cancellation rule).

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
