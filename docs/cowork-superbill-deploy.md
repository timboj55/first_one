# Cowork task: deploy the superbill automation (n8n host + n8n workflow)

Goal: the superbill service from `superbill/` runs as a Docker container next to n8n, and the
n8n workflow `n8n/superbill-sync.json` triggers it hourly. Everything below is on branch
`claude/adoring-sagan-zcc77i` of `timboj55/first_one`. Read `docs/SUPERBILL_SETUP.md` first.

Rules: never paste patient names, emails or the API keys into chat or into any file in the
repo. Report counts and HTTP status codes only. Do the dry run before the first real upload.

## 0. What you need on the Mac

- SSH access to the server that runs n8n (`ssh <user>@<host>`). If n8n is on a managed
  platform instead (Railway, Elestio, Hostinger...), stop and tell Tim; the container has to be
  deployed through that platform's UI instead of step 1.
- The PracticeQ API key: More > Settings > Integrations > Developer API (owner only).
- Either a login to n8n at https://n8n.movementsolutions-sc.com (UI route) or an n8n API key
  (Settings > n8n API) for the curl route in step 2.

## 1. On the n8n server: start the container

```bash
ssh <user>@<host>
git clone https://github.com/timboj55/first_one.git && cd first_one
git checkout claude/adoring-sagan-zcc77i
cp .env.example .env
# edit .env: INTAKEQ_API_KEY=<PracticeQ key>   SUPERBILL_SECRET=$(openssl rand -hex 24)
docker network ls                                   # the network n8n is on, e.g. n8n_default
N8N_NETWORK=<that network> docker compose -f deploy/docker-compose.superbill.yml up -d --build
curl -s http://127.0.0.1:8090/healthz               # expect {"ok": true}
docker exec superbill python -m intakeq_packages verify        # expect HTTP 200 (auth works)
docker exec superbill python -m superbill --dry-run sync --since-days 7
```

The dry run prints one JSON line per client (`uploaded` = would upload) and a summary. If it
shows `error` lines, read `docker logs superbill` and stop.

First real upload, one patient only (pick a client id from the dry-run output):

```bash
docker exec superbill python -m superbill rebuild --client-id <id>
```

Expect `"action": "uploaded"`. Then open that client in PracticeQ > Files and confirm
`Superbill - <name>.pdf` is there and opens. If the upload returns HTTP 400/415, the multipart
field name in `superbill/api.py` (`upload_file`, `name="file"`) needs to match what PracticeQ
expects; report the status code and response body (no patient data) to Tim.

## 2. In n8n: credential + workflow

UI route:

1. Credentials > Add credential > **Header Auth**. Name: `Superbill service (X-Superbill-Secret)`.
   Header name `X-Superbill-Secret`, value = `SUPERBILL_SECRET` from the server's `.env`.
2. Workflows > Add workflow > ... > Import from file > `n8n/superbill-sync.json` (from the repo
   checkout on the Mac). Open the two HTTP Request nodes ("Start superbill sync", "Read sync
   result") and select the credential above if it is not already attached.
3. Click "Execute workflow" once. "Start superbill sync" should return `{"started": true}`;
   after the wait, "Read sync result" shows the summary. Then toggle **Active** on.

API route (same result, no clicking), with `N8N_KEY` = an n8n API key:

```bash
H='X-N8N-API-KEY: '"$N8N_KEY"; B=https://n8n.movementsolutions-sc.com/api/v1
CRED=$(curl -s -H "$H" -H 'Content-Type: application/json' -X POST $B/credentials -d '{"name":"Superbill service (X-Superbill-Secret)","type":"httpHeaderAuth","data":{"name":"X-Superbill-Secret","value":"<SUPERBILL_SECRET>"}}')
CID=$(echo "$CRED" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
python3 - "$CID" <<'PY' > /tmp/wf.json
import json,sys
w=json.load(open('n8n/superbill-sync.json'))
for n in w['nodes']:
    if 'credentials' in n: n['credentials']['httpHeaderAuth']={'id':sys.argv[1],'name':'Superbill service (X-Superbill-Secret)'}
json.dump({k:w[k] for k in ('name','nodes','connections','settings')},sys.stdout)
PY
WF=$(curl -s -H "$H" -H 'Content-Type: application/json' -X POST $B/workflows -d @/tmp/wf.json)
WID=$(echo "$WF" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
curl -s -H "$H" -X POST $B/workflows/$WID/activate | head -c 200
```

## 3. Verify and report

- On the server: `curl -s -H "X-Superbill-Secret: <secret>" http://127.0.0.1:8090/status`
  after the first scheduled run (hourly at :20) shows `last` with counts.
- In PracticeQ: a patient who had a visit today has a fresh `Superbill - ...pdf` in Files.
- Report to Tim: container healthy (yes/no), verify call status, dry-run counts, first rebuild
  result, workflow id and active state, first scheduled run summary. No patient identifiers.

## If something is off

- `no-visits` for a client who clearly had visits: their visits are not `Confirmed`, or the
  service name matches `exclude_service_patterns`, or the charge is 0 (see `include_zero_charge`).
- CPT or description wrong: add the service name to `service_defaults` in
  `superbill_config.json` on the server, then `docker compose ... up -d --build`.
- Too many API calls (HTTP 429 in logs): keep `INTAKEQ_MIN_SECONDS_BETWEEN_CALLS=3.2` and the
  hourly cadence; do not run `sync` by hand while the schedule is active.
