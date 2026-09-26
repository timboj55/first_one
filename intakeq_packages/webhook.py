"""Real-time feed: a tiny webhook receiver for IntakeQ appointment + invoice events.

Point More > Settings > Integrations > Developer API > Webhook URL at this (behind HTTPS).
Appointment events (AppointmentCreated / Rescheduled / Canceled / Missed / ...) include the
full appointment with AppointmentPackageId/Name, so a package booking or consumption is known
the moment it happens. Invoice events (InvoiceIssued / InvoicePaid / ...) reveal package sales.

Run standalone for testing:  python -m intakeq_packages.webhook 8080
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional

APPOINTMENT_EVENTS = {
    "AppointmentCreated", "AppointmentConfirmed", "AppointmentRescheduled",
    "AppointmentCanceled", "AppointmentDeclined", "AppointmentMissed", "AppointmentDeleted",
}
INVOICE_EVENTS = {
    "InvoiceIssued", "InvoicePaid", "InvoicePaymentPlanChargeFailed",
    "InvoiceAutoChargeFailed", "InvoiceCancelled", "InvoicePaymentRefunded",
}


def classify(payload: Dict[str, Any], package_names: Optional[set] = None) -> Optional[Dict[str, Any]]:
    """Return a normalised package-relevant event, or None if the payload has nothing to do with packages."""
    et = payload.get("EventType")
    if et in APPOINTMENT_EVENTS:
        appt = payload.get("Appointment") or {}
        if not appt.get("AppointmentPackageId"):
            return None
        return {
            "kind": "package_appointment",
            "event": et,
            "client_id": appt.get("ClientId"),
            "client_name": appt.get("ClientName"),
            "package_instance_id": appt["AppointmentPackageId"],
            "package_name": appt.get("AppointmentPackageName"),
            "appointment_id": appt.get("Id"),
            "status": appt.get("Status"),
            "start": appt.get("StartDateIso"),
            "invoice_id": appt.get("InvoiceId"),
            "invoice_number": appt.get("InvoiceNumber"),
            "by_client": payload.get("ActionPerformedByClient"),
        }
    if et in INVOICE_EVENTS:
        inv = payload.get("Invoice") or {}
        names = {n.lower() for n in (package_names or set())}
        hits = []
        for item in inv.get("Items") or []:
            desc = (item.get("Description") or "")
            if not names or any(n in desc.lower() for n in names):
                hits.append({"description": desc, "amount": item.get("TotalAmount", item.get("Price")), "units": item.get("Units")})
        if not hits:
            return None
        return {
            "kind": "package_invoice",
            "event": et,
            "client_id": inv.get("ClientIdNumber") or inv.get("ClientId"),
            "client_name": inv.get("ClientName"),
            "invoice_number": inv.get("Number"),
            "invoice_status": inv.get("Status"),
            "items": hits,
        }
    return None


def needs_enrichment(payload: Dict[str, Any]) -> bool:
    """True when an appointment event arrived without the package fields (the owner reports the
    webhook payload may omit them); the receiver should then GET /appointments/{id}."""
    if payload.get("EventType") not in APPOINTMENT_EVENTS:
        return False
    appt = payload.get("Appointment") or {}
    return "AppointmentPackageId" not in appt and bool(appt.get("Id"))


def enrich(payload: Dict[str, Any], fetch_appointment: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
    """Replace payload['Appointment'] with the full single-appointment object when needed."""
    if needs_enrichment(payload):
        full = fetch_appointment(str(payload["Appointment"]["Id"]))
        return {**payload, "Appointment": full}
    return payload


def make_handler(on_event: Callable[[Dict[str, Any]], None], package_names: Optional[set] = None,
                 secret_path: Optional[str] = None, fetch_appointment: Optional[Callable[[str], Dict[str, Any]]] = None):
    """secret_path: IntakeQ cannot send custom headers, so the shared secret lives in the URL path.
    Requests whose path does not end with it are rejected with 404."""
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            if secret_path and not self.path.rstrip("/").endswith(secret_path):
                self.send_response(404); self.end_headers(); return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self.send_response(400); self.end_headers(); return
            if fetch_appointment:
                try:
                    payload = enrich(payload, fetch_appointment)
                except Exception:  # noqa: BLE001  keep acknowledging; nightly job reconciles
                    pass
            evt = classify(payload, package_names)
            if evt:
                on_event(evt)
            self.send_response(200); self.end_headers()

        def log_message(self, *_):
            pass
    return Handler


def serve(port: int, on_event: Callable[[Dict[str, Any]], None], package_names: Optional[set] = None,
          secret_path: Optional[str] = None, fetch_appointment: Optional[Callable[[str], Dict[str, Any]]] = None) -> None:
    HTTPServer(("0.0.0.0", port), make_handler(on_event, package_names, secret_path, fetch_appointment)).serve_forever()


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8080, lambda e: print(json.dumps(e)))
