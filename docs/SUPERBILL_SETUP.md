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
| One line per visit: date, description, CPT x units (+ modifiers), charge | appointment `Procedures` when PracticeQ has them, else `service_defaults` (today: `97530 x4`, "Therapeutic Activity"); charge = appointment `Price`; a $0 (package-covered) visit is charged at the service's list price from PracticeQ settings (`zero_price_uses_list_price`) |
| Total charges | sum of line charges |
| Totals: paid in full shows total charges, provider discount and total after discount; payment plan or balance due shows total charges only | invoices in the episode: `TotalAmount`, `AmountPaid` (statuses Paid / Unpaid / PastDue) |
| Payment statement | **paid in full** (no plan, balance 0), **payment plan** (any invoice has a `ClientPaymentPlanId`), or **balance due** |
| "NOT an insurance provider … PLEASE PROVIDE ANY PAYMENT DIRECTLY TO THE PATIENT" | config `text` |
| Provider signature line + date | off by default (`show_signature`); optional `signature_image` (PNG path) drawn above the line when on |

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
- `zero_price_uses_list_price` (default true): a visit booked at $0 because a package covers it is charged at the service's PracticeQ list price, so it appears on the superbill; the package savings show as the provider discount. Services whose list price is also $0 (e.g. Complimentary Visit) stay off.
- `prorate_packages` (default true): a prepaid package item (description matches `package_pattern`, e.g. "12-Visit Package") counts toward amount billed/paid only for the visits used so far (item amount / visits x visits used), so the provider discount reflects the package savings. Payment-plan installments are not pro-rated.
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

## 4. Run it on the n8n host (chosen setup)

The service runs as one Docker container next to n8n; n8n triggers it hourly. Nothing is
exposed to the internet, so no domain or certificate is needed.

```bash
# on the n8n server
git clone https://github.com/timboj55/first_one.git && cd first_one
cp .env.example .env                 # set INTAKEQ_API_KEY and SUPERBILL_SECRET (openssl rand -hex 24)
docker network ls                    # note the network n8n runs on, e.g. n8n_default
N8N_NETWORK=n8n_default docker compose -f deploy/docker-compose.superbill.yml up -d --build
curl -s http://127.0.0.1:8090/healthz                          # {"ok": true}
docker exec superbill python -m superbill --dry-run sync       # what would be uploaded, no writes
docker exec superbill python -m superbill rebuild --client-id 123   # first real upload, one patient
```

Then in n8n:

1. The two HTTP nodes in the workflow already point at `http://superbill:8080`; edit both if the container runs elsewhere.
2. Credentials > new **Header Auth** named `Superbill service (X-Superbill-Secret)`: name `X-Superbill-Secret`, value = the `SUPERBILL_SECRET` from `.env`.
3. Workflows > Import from file > `n8n/superbill-sync.json`, open it, run once manually, then activate. It POSTs `/sync?since_days=3` hourly at :20, waits 12 minutes, reads `/status`, and has an "Any errors?" branch to wire to a Gmail or Slack node.

Updating later: `git pull && docker compose -f deploy/docker-compose.superbill.yml up -d --build`.
Per-client fingerprints live on the `superbill_data` volume so unchanged superbills are not re-uploaded.

Alternatives (not set up): a plain cron line running `python -m superbill sync` hourly, or a
Cloud Run job in the cockpit's Google Cloud project. The code is the same; only the trigger differs.

## 5. Operations

- `python -m superbill rebuild --client-id N` forces a refresh for one patient (after fixing a diagnosis, adding procedures, or voiding an invoice).
- Sync output is one JSON line per client (`uploaded`, `unchanged`, `no-visits`, `error`) and a summary; exit code 1 if any client errored.
- Rate limit: the client waits `INTAKEQ_MIN_SECONDS_BETWEEN_CALLS` between calls and retries on 429. Do not run two syncs at once.
- The service writes to PracticeQ (file delete + upload) only; it never changes appointments, invoices or client records.
