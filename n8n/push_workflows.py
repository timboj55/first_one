#!/usr/bin/env python3
"""Create or update the two IntakeQ package workflows on a self-hosted n8n via its public API.

Workflows are always pushed INACTIVE. Activation is a manual, approved step in the n8n UI.

Env:
  N8N_BASE_URL   e.g. https://n8n.movementsolutions-sc.com  (no trailing slash)
  N8N_API_KEY    an n8n public API key (Settings > n8n API). Never printed.

Usage:
  python3 n8n/push_workflows.py            # push both drafts
  python3 n8n/push_workflows.py --list     # list existing workflows (id, name, active)
  python3 n8n/push_workflows.py --secret   # also fill the webhook path secret from N8N_WEBHOOK_SECRET
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["intakeq-package-webhook-receiver.json", "intakeq-package-nightly-reconciliation.json"]
# Fields n8n's public API accepts on create/update; everything else in the export is dropped.
ALLOWED = {"name", "nodes", "connections", "settings", "staticData"}


def api(method: str, path: str, body=None):
    base = os.environ["N8N_BASE_URL"].rstrip("/")
    key = os.environ["N8N_API_KEY"]
    req = urllib.request.Request(f"{base}/api/v1{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-N8N-API-KEY": key, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise SystemExit(f"n8n API {e.code} on {method} {path}: {detail}") from None


def list_workflows():
    out, cursor = [], None
    while True:
        q = "?limit=100" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        page = api("GET", "/workflows" + q)
        out.extend(page.get("data", []))
        cursor = page.get("nextCursor")
        if not cursor:
            return out


def push(path: str, secret: str | None):
    with open(path) as f:
        wf = json.load(f)
    if secret:
        for n in wf["nodes"]:
            if n["type"] == "n8n-nodes-base.webhook":
                n["parameters"]["path"] = n["parameters"]["path"].replace("REPLACE_WITH_LONG_RANDOM_SECRET", secret)
    body = {k: v for k, v in wf.items() if k in ALLOWED}
    existing = {w["name"]: w for w in list_workflows()}
    if wf["name"] in existing:
        wid = existing[wf["name"]]["id"]
        res = api("PUT", f"/workflows/{wid}", body)
        action = "updated"
    else:
        res = api("POST", "/workflows", body)
        action = "created"
        wid = res["id"]
    if res.get("active"):
        api("POST", f"/workflows/{wid}/deactivate")  # never leave a pushed draft active
    print(f"{action}: {wf['name']}  id={wid}  active=False")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--secret", action="store_true", help="fill webhook path from N8N_WEBHOOK_SECRET env var")
    args = ap.parse_args()
    for var in ("N8N_BASE_URL", "N8N_API_KEY"):
        if not os.environ.get(var):
            sys.exit(f"{var} is not set")
    if args.list:
        for w in list_workflows():
            print(f"{w['id']:>6}  active={str(w.get('active')):5}  {w['name']}")
        return
    secret = os.environ.get("N8N_WEBHOOK_SECRET") if args.secret else None
    if args.secret and not secret:
        sys.exit("--secret given but N8N_WEBHOOK_SECRET is not set")
    for name in FILES:
        push(os.path.join(HERE, name), secret)


if __name__ == "__main__":
    main()
