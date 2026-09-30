"""IntakeQ endpoints the superbill needs beyond the read-only package client.

Adds: client profile by id, diagnoses, and the Files API (list / upload / delete). The upload is
a multipart/form-data POST to /files/{clientId} with one file part, as the Files API article
describes ("a file stream and the headers properly set").
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from intakeq_packages.client import IntakeQClient


class SuperbillAPI(IntakeQClient):
    # ---- clients ---------------------------------------------------------------------

    def client_profile(self, client_id: int) -> Optional[Dict[str, Any]]:
        """GET /clients?search=<id>&includeProfile=true, exact match on ClientId."""
        rows = self.request("GET", "clients", {"search": str(client_id), "includeProfile": "true"}) or []
        for row in rows:
            if str(row.get("ClientId")) == str(client_id):
                return row
        return rows[0] if len(rows) == 1 else None

    def diagnoses(self, client_id: int) -> List[Dict[str, Any]]:
        """GET /client/{id}/diagnoses (Code, Description, Date, EndDate, NoteId)."""
        try:
            return self.request("GET", f"client/{client_id}/diagnoses") or []
        except Exception:  # noqa: BLE001 - a missing diagnosis list must not block the superbill
            return []

    def appointments_for_client(self, client_id: int, search: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """All appointments for one client in a date window. The list endpoint filters by name/email
        (``search``), so rows are re-filtered on ClientId."""
        rows = self.appointments(client=search, start_date=start_date, end_date=end_date)
        return [r for r in rows if str(r.get("ClientId")) == str(client_id)]

    def invoices_for_client(self, client_id: int, start_date: Optional[str] = None) -> List[Dict[str, Any]]:
        return list(self.invoices(client_id=client_id, start_date=start_date))

    # ---- services --------------------------------------------------------------------

    def service_list_prices(self) -> Dict[str, float]:
        """Service list prices from GET /appointments/settings, keyed by service Id and by
        lower-cased name. Fetched once per API instance; {} if the call fails."""
        cached = getattr(self, "_service_prices", None)
        if cached is not None:
            return cached
        prices: Dict[str, float] = {}
        try:
            settings = self.booking_settings() or {}
        except Exception:  # noqa: BLE001 - missing list prices must not block the superbill
            settings = {}
        for svc in settings.get("Services") or []:
            try:
                price = float(svc.get("Price") or 0)
            except (TypeError, ValueError):
                continue
            if svc.get("Id"):
                prices["id:" + str(svc["Id"])] = price
            if svc.get("Name"):
                prices["name:" + str(svc["Name"]).strip().lower()] = price
        self._service_prices = prices
        return prices

    # ---- files -----------------------------------------------------------------------

    def files(self, client_id: int) -> List[Dict[str, Any]]:
        return self.request("GET", "files", {"clientId": client_id}) or []

    def delete_file(self, file_id: str) -> None:
        self.request("DELETE", f"files/{file_id}", decode_json=False)

    def upload_file(self, client_id: int, filename: str, data: bytes, content_type: str = "application/pdf") -> Any:
        boundary = "----superbill" + uuid.uuid4().hex
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        tail = f"\r\n--{boundary}--\r\n".encode()
        body = head + data + tail
        return self.request(
            "POST",
            f"files/{client_id}",
            raw=body,
            content_type=f"multipart/form-data; boundary={boundary}",
            decode_json=False,
        )
