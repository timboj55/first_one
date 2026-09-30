"""Small HTTP surface so n8n (or anything with an HTTP node) can trigger a sync or one rebuild.

  GET  /healthz
  POST /sync?since_days=3          run a sync in the background (202); one at a time
  POST /rebuild/<clientId>         rebuild + upload one client's superbill now (200, JSON result)
  POST /webhook                    accepts the PracticeQ appointment webhook payload forwarded by
                                   n8n; refreshes that client if the appointment already ended
  GET  /status                     last sync summary

Every route except /healthz requires header  X-Superbill-Secret: <SUPERBILL_SECRET>
(or ?key=<secret>). Put it behind HTTPS.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .build import appointment_end
from .sync import SuperbillSync

log = logging.getLogger("superbill.server")


def make_handler(sync: SuperbillSync, secret: str):
    state: Dict[str, Any] = {"last": None, "running": False}
    lock = threading.Lock()

    def run_sync(since: Optional[int]) -> None:
        try:
            state["last"] = sync.sync(since).summary()
        except Exception as e:  # noqa: BLE001
            log.exception("sync failed")
            state["last"] = {"error": str(e)}
        finally:
            state["running"] = False

    class Handler(BaseHTTPRequestHandler):
        server_version = "superbill/0.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            log.info("%s %s", self.address_string(), fmt % args)

        def _json(self, code: int, obj: Any) -> None:
            data = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authed(self, query: Dict[str, list]) -> bool:
            given = self.headers.get("X-Superbill-Secret") or (query.get("key") or [""])[0]
            return bool(secret) and hmac.compare_digest(given, secret)

        def _body(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            try:
                obj = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return {}
            return obj if isinstance(obj, dict) else {}

        def do_GET(self) -> None:
            u = urlparse(self.path)
            if u.path == "/healthz":
                return self._json(200, {"ok": True})
            if not self._authed(parse_qs(u.query)):
                return self._json(401, {"error": "unauthorized"})
            if u.path == "/status":
                return self._json(200, {"running": state["running"], "last": state["last"]})
            return self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if not self._authed(q):
                return self._json(401, {"error": "unauthorized"})
            parts = [p for p in u.path.split("/") if p]
            if parts == ["sync"]:
                since = int(q["since_days"][0]) if q.get("since_days") else None
                with lock:
                    if state["running"]:
                        return self._json(409, {"error": "sync already running"})
                    state["running"] = True
                threading.Thread(target=run_sync, args=(since,), daemon=True).start()
                return self._json(202, {"started": True, "since_days": since})
            if len(parts) == 2 and parts[0] == "rebuild" and parts[1].isdigit():
                r = sync.refresh(int(parts[1]), force=True)
                return self._json(200 if r.action != "error" else 500, r.__dict__)
            if parts == ["webhook"]:
                body = self._body()
                appt = body.get("Appointment") or {}
                cid = body.get("ClientId") or appt.get("ClientId")
                if cid is None:
                    return self._json(400, {"error": "no ClientId in payload"})
                from datetime import datetime

                tz = ZoneInfo(sync.cfg["timezone"])
                ended = appointment_end(appt, tz)
                if ended is None or ended > datetime.now(tz):
                    return self._json(200, {"client_id": cid, "action": "deferred", "reason": "appointment not finished"})
                r = sync.refresh(int(cid), seed_appointment=appt)
                return self._json(200, r.__dict__)
            return self._json(404, {"error": "not found"})

    return Handler


def serve(sync: SuperbillSync, host: str = "0.0.0.0", port: Optional[int] = None) -> None:
    secret = os.environ.get("SUPERBILL_SECRET", "")
    if not secret:
        raise SystemExit("SUPERBILL_SECRET is required to serve (openssl rand -hex 24)")
    port = port or int(os.environ.get("PORT", "8080"))
    httpd = ThreadingHTTPServer((host, port), make_handler(sync, secret))
    log.info("superbill listening on %s:%s", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
