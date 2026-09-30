import io
import json
import unittest
import urllib.error

from intakeq_packages import IntakeQClient, IntakeQError


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class ClientTests(unittest.TestCase):
    def _client(self, pages, api_key="k"):
        calls = []

        def opener(req):
            calls.append(req)
            body = pages.pop(0)
            if isinstance(body, int):
                raise urllib.error.HTTPError(req.full_url, body, "err", {}, io.BytesIO(b"limit"))
            return FakeResponse(json.dumps(body).encode())

        c = IntakeQClient(api_key=api_key, min_seconds_between_calls=0, opener=opener, sleep=lambda s: None)
        return c, calls

    def test_pagination_and_headers(self):
        page1 = [{"Id": str(i)} for i in range(100)]
        c, calls = self._client([page1, [{"Id": "last"}]])
        rows = list(c.appointments(start_date="2026-01-01"))
        self.assertEqual(len(rows), 101)
        self.assertEqual(calls[0].get_header("X-auth-key"), "k")
        self.assertIn("page=1", calls[0].full_url)
        self.assertIn("startDate=2026-01-01", calls[0].full_url)
        self.assertIn("page=2", calls[1].full_url)

    def test_proxy_injected_mode_sends_no_auth_header(self):
        import os
        old = os.environ.pop("INTAKEQ_API_KEY", None)
        try:
            c, calls = self._client([[{"Id": "p1"}]], api_key=None)
            self.assertEqual(len(c.practitioners()), 1)
            self.assertIsNone(calls[0].get_header("X-auth-key"))
        finally:
            if old is not None:
                os.environ["INTAKEQ_API_KEY"] = old

    def test_retries_on_429_then_raises_other_errors(self):
        c, calls = self._client([429, {"Id": "ok"}])
        self.assertEqual(c.appointment("x")["Id"], "ok")
        c2, _ = self._client([401])
        with self.assertRaises(IntakeQError) as cm:
            c2.appointment("x")
        self.assertEqual(cm.exception.status, 401)

    def test_invoice_filter_names_match_official_docs(self):
        c, calls = self._client([[]])
        list(c.invoices(client_id=5, last_updated_start_date="2026-01-01", number=7))
        self.assertIn("lastUpdatedStartDate=2026-01-01", calls[0].full_url)
        self.assertIn("clientId=5", calls[0].full_url)
        self.assertIn("number=7", calls[0].full_url)


if __name__ == "__main__":
    unittest.main()
