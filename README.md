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

Both keys are stored as **API credentials** in the "Default" cloud environment, not as shell
variables. The egress proxy injects them into requests for their scoped hosts, so code sends no
auth header itself:

| Credential | Scoped host(s) | Header the API needs | Status (2026-09-30) |
|---|---|---|---|
| `N8N_API_KEY` | n8n.movementsolutions-sc.com | `X-N8N-API-KEY: <key>` | working: `GET /api/v1/workflows` returns 200 |
| `INTAKEQ_API_KEY` | intakeq.com, support.intakeq.com | `X-Auth-Key: <key>` | **not working**: `GET /api/v1/practitioners` returns 401 |

The 401 means the IntakeQ credential is not being sent as `X-Auth-Key` (a default such as
`Authorization: Bearer` will not authenticate against IntakeQ). Fix: edit the credential in the
environment so the header name is exactly `X-Auth-Key` with the bare key as value, no prefix.
Then `python -m intakeq_packages verify` makes one `GET /practitioners` and reports the status.

`IntakeQClient` also accepts an `INTAKEQ_API_KEY` environment variable and sends the header
itself when one is present, for use outside this environment.

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
