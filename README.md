# PracticeQ / IntakeQ package data via API

**Short answer:** IntakeQ's public API has **no packages endpoint**. There is no way to ask
"what packages does client X own and how many sessions are left". But package data *is*
reachable through two documented feeds, and from those a full per-client package ledger can be
rebuilt automatically. This repo contains the findings and a working, stdlib-only Python
implementation that does it.

## What the public API exposes (verified)

Base URL `https://intakeq.com/api/v1`, header `X-Auth-Key: <key>`. Key is under
**More > Settings > Integrations > Developer API**. Standard plan: **10 requests/minute,
500/day**, list endpoints return **100 rows per page** (`page=N`). Higher limits on request
to PracticeQ support.

| Resource | Endpoints | Package-relevant data |
|---|---|---|
| Appointments | `GET /appointments` (filters: `client`, `startDate`, `endDate`, `status`, `practitionerEmail`, `updatedSince`, `deletedOnly`, `page`), `GET /appointments/{id}`, `POST/PUT /appointments`, `POST /appointments/cancellation`, `GET /appointments/settings` | **`AppointmentPackageId`** (unique per purchased package instance) and **`AppointmentPackageName`** on every appointment, plus `ClientId`, `Status`, `StartDate`, `DateCreated`, `Price` |
| Invoices | `GET /invoices` (filters: `clientId`, `startDate`, `endDate`, `status`, `practitionerEmail`, `lastUpdateStartDate`, `lastUpdateEndDate`, `page`), `GET /invoices/{id}` | Line `Items[]` with `Description`, `Price`, `Units`, `TotalAmount`, `ProductId`, `AppointmentId`; `Status`, `IssuedDate`, `Payments[]`. A package sale is a line item whose Description names the package. |
| Clients | `GET /clients` (`search`, `includeProfile`, `page`), `POST /clients`, `POST/DELETE /clientTags` | No package fields. Tags are useful as an *output*: tag clients "package-1-left" and let PracticeQ automations act on it. |
| Intakes, Notes, Files, Claims, Practitioners, Questionnaires | documented separately | nothing package related |
| Webhooks (same settings page) | `AppointmentCreated/Confirmed/Rescheduled/Canceled/Declined/Missed`, `InvoiceIssued/Paid/Cancelled/PaymentRefunded/PaymentPlanChargeFailed/AutoChargeFailed`, intake submitted, note locked | Appointment events carry the **full appointment object including the package fields**; invoice events carry the full invoice. This is the real-time path. |
| Booking widget JS | `intakeqPackageSignUp` DOM event | fires in the browser when a visitor buys a package; front-end only |

What is **not** exposed anywhere: the package *definitions* (sessions per package, price,
expiry window) and PracticeQ's own "sessions remaining" counter. `GET /appointments/settings`
returns Services, Locations and Practitioners only.

## How to get to 100% automation anyway

1. **Mirror the package definitions once** in `packages.json` (name -> sessions, validity).
   They change rarely and only you change them.
2. **Group appointments by `AppointmentPackageId`.** Each id is one purchased package
   instance. Past `Confirmed` + `Missed` = used; future `Confirmed` / `WaitingConfirmation` =
   scheduled; `Canceled` / `Declined` are free. `remaining = sessions - used - scheduled`.
3. **Join the sale from invoices** (same client, line item Description contains the package
   name, closest issue date before the first booking) for purchase date, invoice number and
   amount. Expiry = purchase date + validity days.
4. **Keep it live with webhooks.** Every package booking, cancellation, no-show and sale
   arrives as a POST within seconds, so the ledger never needs a full re-pull. Use the
   nightly `report` run only as reconciliation.
5. **Write results back** as client tags or into your cockpit's datastore.

Caveat on step 2: sessions a client bought but has not yet scheduled do not exist as
appointments, which is exactly why the definition mirror in step 1 is required. If you
sell packages with flexible session counts, the invoice `Units` field is the next best
signal.

## This implementation

```
intakeq_packages/
  client.py    throttled, paginated, retrying client for /appointments, /invoices, /clients, /clientTags
  packages.py  build_ledger(appointments, config, invoices) -> per-package-instance ledger
  cli.py       python -m intakeq_packages report --config packages.json --since 2026-01-01 --out out/
  webhook.py   stdlib HTTP receiver that normalises appointment/invoice events into package events
tests/         unit tests on synthetic API payloads (python -m unittest discover -s tests)
packages.example.json  copy to packages.json and fill in your real package names
.env.example           INTAKEQ_API_KEY, INTAKEQ_MIN_SECONDS_BETWEEN_CALLS
```

Quick start:

```bash
cp .env.example .env && cp packages.example.json packages.json   # edit both
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

## Not tested against a live account

This code was written from the API documentation and two open-source clients, not run
against a real PracticeQ tenant (no key in this environment). Two things to confirm on the
first live run: whether `StartDate`/`DateCreated`/`IssuedDate` arrive in milliseconds or
seconds (the code handles both), and the exact `Description` text PracticeQ writes on a
package invoice line so the name match in `packages.json` lines up.

## Alternatives considered

- **Ask PracticeQ for a packages endpoint or higher rate limit**: support is the only route
  for both; the API reference has a changelog and they do add fields.
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
- Booking widget JS events: https://support.intakeq.com/article/243-booking-widget-javascript-events
- Community OpenAPI profile: https://github.com/api-evangelist/intakeq
- TypeScript client with full field typings: https://github.com/LifeBac/intakeq-api
