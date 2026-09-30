"""HTTP surface. Stdlib ThreadingHTTPServer; put it behind HTTPS (Caddy/nginx/Cloudflare tunnel).

Routes (all JSON):
  GET  /healthz
  POST /webhooks/ghl/<GHL_WEBHOOK_SECRET>/new-lead            GHL workflow webhook: new lead
  POST /webhooks/ghl/<GHL_WEBHOOK_SECRET>/inbound-message     GHL workflow webhook: Customer Replied (SMS)
  POST /webhooks/ghl/<GHL_WEBHOOK_SECRET>/appointment-booked  GHL workflow webhook: appointment booked
  POST /voice/tools/<tool_name>                               Retell custom tool callback (signed)
  POST /voice/webhook                                         Retell call events (signed)
  POST /admin/<ADMIN_SECRET>/busy      {"on": true|false}
  GET  /admin/<ADMIN_SECRET>/status[?contact_id=...]
  POST /admin/<ADMIN_SECRET>/simulate/new-lead     same body as the GHL webhook (dry runs)
"""

from __future__ import annotations

import hmac
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .orchestrator import Orchestrator
from .scheduler import Scheduler
from .voice import parse_tool_request, verify_signature

log = logging.getLogger("lead_agent.server")


def make_handler(orch: Orchestrator, scheduler: Scheduler | None):
    secrets = orch.secrets

    class Handler(BaseHTTPRequestHandler):
        server_version = "lead-agent/0.1"

        def log_message(self, fmt: str, *args: Any) -> None:  # route through logging
            log.info("%s %s", self.address_string(), fmt % args)

        # ---- helpers ----
        def _json(self, code: int, obj: Any) -> None:
            data = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> tuple[str, dict[str, Any]]:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n).decode("utf-8", errors="replace") if n else ""
            if not raw.strip():
                return raw, {}
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                obj = {k: v[0] for k, v in parse_qs(raw).items()}
            return raw, obj if isinstance(obj, dict) else {"data": obj}

        def _secret_ok(self, given: str, expected: str) -> bool:
            return bool(expected) and hmac.compare_digest(given, expected)

        def _retell_ok(self, raw: str) -> bool:
            if not secrets.retell_api_key:
                return secrets.dry_run  # allow unsigned only in dry-run/local testing
            return verify_signature(raw, secrets.retell_api_key, self.headers.get("x-retell-signature"))

        # ---- routes ----
        def do_GET(self) -> None:
            u = urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            if parts == ["healthz"]:
                return self._json(200, {"ok": True, "busy_mode": orch.busy_mode()})
            if len(parts) == 3 and parts[0] == "admin" and parts[2] == "status":
                if not self._secret_ok(parts[1], secrets.admin_secret):
                    return self._json(404, {"error": "not found"})
                q = parse_qs(u.query)
                return self._json(200, orch.status((q.get("contact_id") or [None])[0]))
            return self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            u = urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            raw, body = self._body()
            try:
                if len(parts) == 4 and parts[:2] == ["webhooks", "ghl"]:
                    if not self._secret_ok(parts[2], secrets.ghl_webhook_secret):
                        return self._json(404, {"error": "not found"})
                    kind = parts[3]
                    if kind == "new-lead":
                        res = orch.handle_new_lead(body)
                    elif kind == "inbound-message":
                        res = orch.handle_inbound(body)
                    elif kind == "appointment-booked":
                        res = orch.handle_appointment_booked(body)
                    else:
                        return self._json(404, {"error": "unknown webhook"})
                    if scheduler:
                        scheduler.poke()
                    return self._json(200, res)

                if len(parts) == 3 and parts[:2] == ["voice", "tools"]:
                    if not self._retell_ok(raw):
                        return self._json(401, {"error": "bad signature"})
                    name, args, call = parse_tool_request(body, parts[2])
                    out = orch.handle_voice_tool(name, args, call)
                    return self._json(200, {"result": out})

                if parts == ["voice", "webhook"]:
                    if not self._retell_ok(raw):
                        return self._json(401, {"error": "bad signature"})
                    res = orch.handle_voice_event(body.get("event", ""), body.get("call") or {})
                    if scheduler:
                        scheduler.poke()
                    return self._json(200, res)

                if len(parts) >= 3 and parts[0] == "admin":
                    if not self._secret_ok(parts[1], secrets.admin_secret):
                        return self._json(404, {"error": "not found"})
                    if parts[2] == "busy":
                        on = body.get("on")
                        if isinstance(on, str):
                            on = on.lower() in ("1", "true", "on", "yes")
                        orch.set_busy(bool(on))
                        return self._json(200, {"ok": True, "busy_mode": orch.busy_mode()})
                    if parts[2:] == ["simulate", "new-lead"]:
                        res = orch.handle_new_lead(body)
                        if scheduler:
                            scheduler.poke()
                        return self._json(200, res)
                    if parts[2:] == ["simulate", "inbound-message"]:
                        res = orch.handle_inbound(body)
                        if scheduler:
                            scheduler.poke()
                        return self._json(200, res)
                return self._json(404, {"error": "not found"})
            except Exception as e:
                log.exception("request failed")
                return self._json(500, {"error": str(e)})

    return Handler


def serve(orch: Orchestrator, scheduler: Scheduler | None, host: str = "0.0.0.0", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(orch, scheduler))
    log.info("listening on %s:%d", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
