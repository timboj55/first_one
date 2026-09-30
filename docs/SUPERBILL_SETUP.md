# Automatic superbills in PracticeQ: setup and operations

`superbill/` keeps one up-to-date superbill PDF in every patient's **Files** tab in PracticeQ
(IntakeQ). Each time a visit is completed, the patient's superbill is rebuilt from PracticeQ
records and the previous copy is replaced, so the file in the chart is always the current
itemized statement the patient can send to their insurer.

## What the automation does

```
every hour (n8n schedule, or cron / Cloud Run job)
  └─ superbill sync
       ├─ GET /appointments  (last 3 days + anything modified since yesterday)
       ├─ pick clients with a Confirmed visit whose end time has passed
       └─ for each client:
            ├─ GET client profile, appointments (episode window), invoices, diagnoses
            ├─ compute lines + totals  ──►  render PDF (fpdf2)
            ├─ skip if nothing changed since the last upload (fingerprint)
            ├─ DELETE any file named "Superbill - …" in the client's Files
            └─ POST the new "Superbill - <Patient Name>.pdf" to the client's Files
```

**"Completed"** = status `Confirmed` and end time in the past. Canceled, Missed, Declined and
future visits never appear. PracticeQ has no "completed" status or webhook for the moment a
visit ends, so a schedule is required; the existing appointment webhook (owned by the n8n
"IntakeQ Appointments -> GHL" workflow) is not touched. Cancelling or deleting a past visit
also refreshes the superbill (the sync also scans `updatedSince` yesterday).

## What is on the superbill

Everything on the original template, reorganized for a claims processor:

| Block | Source in PracticeQ |
|---|---|
| Practice name, address, phone, EIN, place of service | `superbill_config.json` |
| Statement date, dates of service, patient ID | computed / `ClientId` |
| Patient name, DOB, address, phone | client profile (`GET /clients?includeProfile=true`) |
| Rendering provider, credentials, NPI, license, taxonomy | config (`default_provider`, or `providers_by_email` keyed by the practitioner's PracticeQ email) |
| ICD-10 codes | `GET /client/{id}/diagnoses` (active codes); fallback: invoice `DiagnosisList` |
| One line per visit: date, description, CPT x units (+ modifiers), charge | appointment `Procedures` when PracticeQ has them, else `service_defaults` (today: `97530 x4`, "Therapeutic Activity"); charge = appointment `Price` |
| Total charges | sum of line charges |
| Provider discount | total charges - amount billed on invoices (package / plan pricing) |
| Amount billed to patient, total payments, account balance | invoices in the episode: `TotalAmount`, `AmountPaid` (statuses Paid / Unpaid / PastDue) |
| Payment statement | **paid in full** (no plan, balance 0), **payment plan** (any invoice has a `ClientPaymentPlanId`; shows payments to date and installments invoiced), or **balance due** |
| "NOT an insurance provider … PLEASE PROVIDE ANY PAYMENT DIRECTLY TO THE PATIENT" | config `text` |
| Provider signature line + date | optional `signature_image` (PNG path) drawn above the line |

Worked check against the template (Russ, payment plan): 18 visits x $399 = $7,182.00 charges,
$5,668.20 billed and paid, provider discount $1,513.80, balance $0.00, payment-plan wording.
Dana (paid in full, no plan) gets the "has paid in full" wording. Both are covered by
`tests/test_superbill.py`.

The **episode** (which visits are on the statement) is the last 365 days by default. To start
each statement at the most recent evaluation instead, set
`"episode": {"start_service_pattern": "(?i)eval"}` (regex on the service name).

## 1. Prerequisites

| Item | Where |
|---|---|
| PracticeQ API key | More > Settings > Integrations > Developer API (owner only). The account is on 20 req/min; a sync of 15 clients is about 120 calls, so keep the hourly cadence. |
| Somewhere to run Python 3.11+ | The cockpit's Google Cloud project (Cloud Run job + Cloud Scheduler) is the natural home; a small VM or the n8n host also works. |
| `SUPERBILL_SECRET` | only for `serve` mode (n8n calling the service): `openssl rand -hex 24` |

## 2. Configure

Edit `superbill_config.json`:

- `practice`, `default_provider`: already filled from the template (EIN, NPI, license, address).
- `providers_by_email`: add `{"<practitioner email in PracticeQ>": {"name": ..., "npi": ...}}` for each additional therapist; visits are attributed to the practitioner on the last visit.
- `service_defaults`: CPT/units used when an appointment carries no procedure codes. `"*"` is the catch-all; add exact service names (e.g. `"Initial Evaluation": {"cpt": "97163", "units": 1}`) as needed. Entering procedures on the appointment in PracticeQ always wins.
- `exclude_service_patterns`: regexes for services that must never be billed (e.g. `"(?i)cost .*availability"`).
- `signature_image`: path to a PNG of the provider's signature, if it should print on the form.
- `file.name_format`: `Superbill - {name}.pdf`; every existing file starting with `file.replace_prefix` is replaced on each refresh.

## 3. Try it before turning it on

```bash
pip install -r requirements.txt
cp .env.example .env            # INTAKEQ_API_KEY, INTAKEQ_MIN_SECONDS_BETWEEN_CALLS=3.2
python -m superbill preview --client-id 123 --out preview.pdf   # renders only, no upload
python -m superbill --dry-run sync --since-days 7                # lists what would be uploaded
python -m superbill rebuild --client-id 123                      # first real upload, one client
```

Check the file in that client's Files tab in PracticeQ. If the upload fails with HTTP 400, the
multipart field name may differ from `file`; it is set in `superbill/api.py` (`upload_file`).

## 4. Run it on a schedule

**Option A: cron / Cloud Run job (simplest, no service to host).** Run
`python -m superbill sync` hourly during clinic hours (or once nightly with `--since-days 3`).
State (`out/superbill_state.json`, the per-client fingerprints that avoid re-uploading an
unchanged PDF) is optional; without a persistent disk set `"state_path": ""` and every run
re-uploads for the clients it touches.

```
0 7-21 * * *  cd /opt/first_one && python -m superbill sync >> /var/log/superbill.log 2>&1
```

**Option B: n8n calls the service.** Run `python -m superbill serve` (or
`docker build -f Dockerfile.superbill -t superbill . && docker run -d --env-file .env -p 8080:8080 -v superbill_data:/data superbill`)
behind HTTPS, then import `n8n/superbill-sync.json`:

1. n8n Variables: `SUPERBILL_URL` = the service URL.
2. Credential (Header Auth) named `Superbill service (X-Superbill-Secret)`: header `X-Superbill-Secret`, value = `SUPERBILL_SECRET`.
3. Activate. The workflow POSTs `/sync?since_days=3` hourly, waits, reads `/status`, and has an "Any errors?" branch to wire to Gmail/Slack.

Service routes: `POST /sync`, `POST /rebuild/<clientId>` (immediate, e.g. a manual button),
`POST /webhook` (accepts a forwarded PracticeQ appointment webhook and refreshes that client
once the appointment has ended), `GET /status`, `GET /healthz`.

## 5. Operations

- `python -m superbill rebuild --client-id N` forces a refresh for one patient (after fixing a diagnosis, adding procedures, or voiding an invoice).
- Sync output is one JSON line per client (`uploaded`, `unchanged`, `no-visits`, `error`) and a summary; exit code 1 if any client errored.
- Rate limit: the client waits `INTAKEQ_MIN_SECONDS_BETWEEN_CALLS` between calls and retries on 429. Do not run two syncs at once.
- The service writes to PracticeQ (file delete + upload) only; it never changes appointments, invoices or client records.
