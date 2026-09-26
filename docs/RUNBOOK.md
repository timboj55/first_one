# Runbook: IntakeQ package ledger for the cockpit

## Components

| Piece | Where it runs | What it does |
|---|---|---|
| `intakeq_packages` (Python, stdlib only) | n8n host (nightly) and anywhere for ad-hoc runs | API client, ledger builder, export-compatible CSV writer, nightly reconciliation |
| `n8n/intakeq-package-webhook-receiver.json` | n8n | Receives IntakeQ webhooks on a secret URL, fetches the full appointment, writes one event file per package event |
| `n8n/intakeq-package-nightly-reconciliation.json` | n8n, 03:00 ET | Pulls cockpit repo, runs the nightly job, commits ledger files |
| `n8n/push_workflows.py` | anywhere with `N8N_API_KEY` | Creates/updates both workflows **inactive** via the n8n public API |

## Storage (agreed location)

Inside the cockpit repo, written by the nightly job:

- `data/packages_ledger.csv`: exact columns of the PracticeQ Packages export. Existing rows pass through verbatim, `UnusedSessions` untouched. New instances discovered from appointments get a row with API-sourced fields and a blank `UnusedSessions`.
- `data/packages_ledger_derived.csv`: per package instance: `sessions_total` (export first, config default second), `used`, `scheduled`, `remaining_derived`, `unused_practiceq`, `expires_on`, `status`, warnings such as a PracticeQ counter disagreeing with the derived count.
- `data/appt_packages.json`: the cockpit's existing appointment-to-package file, updated in place in whatever shape it already has.
- `data/nightly_state.json`: last run, next `updatedSince`, ids carried over past the deadline.

Real-time events land on the n8n volume at `/home/node/.n8n-files/intakeq/events/*.json` (PHI stays on the HIPAA host; nothing is committed per event).

## One-time setup

1. **PracticeQ**: More > Settings > Integrations > Developer API. Enable API access, no IP allow-list (or allow the n8n host's egress IP). Rate limit is 20 req/min on this tenant.
2. **n8n credentials**: create a Header Auth credential named exactly `IntakeQ API (X-Auth-Key)` with header name `X-Auth-Key` and the API key as value.
3. **n8n container env**: `INTAKEQ_API_KEY`, `COCKPIT_REPO_URL` (HTTPS URL containing a deploy token with write access to the cockpit repo), and `N8N_RESTRICT_FILE_ACCESS_TO=/home/node/.n8n-files` if file access is restricted. Ensure `git` and `python3` (3.9+) exist in the container image.
4. **Folders on the n8n volume**: `mkdir -p /home/node/.n8n-files/intakeq/events`.
5. **Webhook secret**: `openssl rand -hex 32`. Put it in the receiver workflow's Webhook node path (`intakeq/<secret>`), or export `N8N_WEBHOOK_SECRET` and run `python3 n8n/push_workflows.py --secret`.
6. **Import workflows**: either import the two JSON files in the n8n UI, or `N8N_BASE_URL=https://n8n.movementsolutions-sc.com N8N_API_KEY=... python3 n8n/push_workflows.py`. Both arrive inactive.
7. **Review and approve** each workflow in the n8n UI. Only then activate.
8. **Point IntakeQ at the receiver**: paste the production webhook URL (`https://n8n.movementsolutions-sc.com/webhook/intakeq/<secret>`) into the Developer API settings and tick the appointment and invoice events.

## Offline checks (no API calls)

```bash
python3 -m intakeq_packages inspect --export data/packages_all.csv --appt-map data/appt_packages.json
python3 -m intakeq_packages ledger --config packages.json --appt-map data/appt_packages.json --export data/packages_all.csv --out /tmp/ledger
```

`inspect` prints how each column and key was detected. If a mapping is wrong, pin it: the export loader accepts a `mapping_override` and the same will be exposed as a config block once the real headers are known.

## Nightly job by hand

```bash
python3 -m intakeq_packages nightly --config packages.json \
  --appt-map data/appt_packages.json --export data/packages_all.csv --out data \
  --pace 8 --max-calls 300
```

Budget: `updatedSince` list (1 call per 100 changed) + 1 call per changed appointment at 7.5/min, hard stop 03:55 ET. Anything left is carried to the next night and `next_since` is set to the run date minus one day so a missed night is covered.

## Rules the code enforces

- A canceled or missed appointment counts as consumed only while it still carries `AppointmentPackageId`. Released cancellations disappear from the ledger automatically.
- Session totals come from the export row for that purchase; the package name is a fallback only.
- `UnusedSessions` is PracticeQ's; the derived count lives in the sidecar with a warning when they differ.

## Secrets

Never in chat, JSON, git or logs. IntakeQ key: environment variable only. n8n key: `N8N_API_KEY` only. Webhook secret: only in the Webhook node path and the PracticeQ settings page.
