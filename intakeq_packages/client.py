"""Minimal stdlib-only client for the IntakeQ REST API (https://intakeq.com/api/v1).

Auth is a single ``X-Auth-Key`` header. Two modes:
  * INTAKEQ_API_KEY set in the environment: the client sends the header itself.
  * not set: the client sends no auth header and relies on the Claude Code environment's
    API-credential injection (the egress proxy adds X-Auth-Key for intakeq.com). This is how
    the practice's environment is configured; the key never appears as a shell variable.

Rate limits: this tenant is on 20 requests/minute. The client throttles itself (default one
call per 6 s) and paginates 100-row list endpoints for you. Read-only helpers only; nothing
here writes to PracticeQ.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Optional

BASE_URL = "https://intakeq.com/api/v1"
PAGE_SIZE = 100


class IntakeQError(RuntimeError):
    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"IntakeQ API {status} for {url}: {body[:300]}")
        self.status = status
        self.body = body
        self.url = url


class IntakeQClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
        min_seconds_between_calls: Optional[float] = None,
        max_retries: int = 4,
        opener: Optional[Callable[[urllib.request.Request], Any]] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or os.environ.get("INTAKEQ_API_KEY")  # None => proxy-injected mode
        self.base_url = base_url.rstrip("/")
        if min_seconds_between_calls is None:
            min_seconds_between_calls = float(os.environ.get("INTAKEQ_MIN_SECONDS_BETWEEN_CALLS", "6"))
        self.min_gap = min_seconds_between_calls
        self.max_retries = max_retries
        self._open = opener or urllib.request.urlopen
        self._sleep = sleep
        self._last_call = 0.0
        self.calls_made = 0

    # ---- transport -------------------------------------------------------------------

    def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Any = None) -> Any:
        query = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Auth-Key"] = self.api_key
        if data is not None:
            headers["Content-Type"] = "application/json"

        attempt = 0
        while True:
            self._throttle()
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with self._open(req) as resp:
                    raw = resp.read()
                self.calls_made += 1
                return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                self.calls_made += 1
                text = e.read().decode(errors="replace") if hasattr(e, "read") else ""
                if e.code == 429 and attempt < self.max_retries:
                    attempt += 1
                    self._sleep(min(60.0, 10.0 * attempt))
                    continue
                raise IntakeQError(e.code, text, url) from None

    def _throttle(self) -> None:
        if self.min_gap <= 0:
            return
        wait = self.min_gap - (time.monotonic() - self._last_call)
        if wait > 0:
            self._sleep(wait)
        self._last_call = time.monotonic()

    def _paged(self, path: str, params: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            rows = self.request("GET", path, {**params, "page": page}) or []
            for row in rows:
                yield row
            if len(rows) < PAGE_SIZE:
                return
            page += 1

    # ---- appointments ------------------------------------------------------------------

    def appointments(
        self,
        client: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        practitioner_email: Optional[str] = None,
        updated_since: Optional[str] = None,
        deleted_only: Optional[bool] = None,
    ) -> Iterator[Dict[str, Any]]:
        """GET /appointments. Dates are yyyy-MM-dd. ``client`` matches name or email (partial)."""
        return self._paged(
            "appointments",
            {
                "client": client,
                "startDate": start_date,
                "endDate": end_date,
                "status": status,
                "practitionerEmail": practitioner_email,
                "updatedSince": updated_since,
                "deletedOnly": str(deleted_only).lower() if deleted_only is not None else None,
            },
        )

    def appointment(self, appointment_id: str) -> Dict[str, Any]:
        return self.request("GET", f"appointments/{appointment_id}")

    def booking_settings(self) -> Dict[str, Any]:
        """GET /appointments/settings: Services, Locations, Practitioners (no packages)."""
        return self.request("GET", "appointments/settings")

    def practitioners(self) -> List[Dict[str, Any]]:
        """GET /practitioners: the smallest read-only call, used for auth verification."""
        return self.request("GET", "practitioners") or []

    # ---- invoices ----------------------------------------------------------------------

    def invoices(
        self,
        client_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        practitioner_email: Optional[str] = None,
        number: Optional[int] = None,
        last_updated_start_date: Optional[str] = None,
        last_updated_end_date: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """GET /invoices. Package purchases show up as line items whose Description names the package.

        Parameter names follow the official Invoice API page (lastUpdatedStartDate / lastUpdatedEndDate).
        """
        return self._paged(
            "invoices",
            {
                "clientId": client_id,
                "startDate": start_date,
                "endDate": end_date,
                "status": status,
                "practitionerEmail": practitioner_email,
                "number": number,
                "lastUpdatedStartDate": last_updated_start_date,
                "lastUpdatedEndDate": last_updated_end_date,
            },
        )

    def invoice(self, invoice_id: str) -> Dict[str, Any]:
        return self.request("GET", f"invoices/{invoice_id}")

    # ---- clients -----------------------------------------------------------------------

    def clients(self, search: Optional[str] = None, include_profile: bool = False) -> Iterator[Dict[str, Any]]:
        """GET /clients. With include_profile the row carries CreditBalance, CustomFields, Tags, etc. No package fields."""
        return self._paged("clients", {"search": search, "includeProfile": "true" if include_profile else None})

