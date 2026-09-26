import datetime as dt
import io
import json
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager

from intakeq_packages import IntakeQClient, IntakeQError, PackageConfig, build_ledger
from intakeq_packages.webhook import classify

TODAY = dt.date(2026, 9, 26)
MS = 1000


def ts(y, m, d):
    return int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp()) * MS


def appt(id_, pkg_id, pkg_name, status, start, created=None, client_id=42):
    return {
        "Id": id_, "ClientId": client_id, "ClientName": "Pat Client", "ClientEmail": "pat@example.com",
        "Status": status, "StartDate": start, "DateCreated": created or start,
        "AppointmentPackageId": pkg_id, "AppointmentPackageName": pkg_name,
    }


CONFIG = PackageConfig.from_dict({
    "packages": {"6 Session Package": {"sessions": 6, "valid_days": 90, "expiry_basis": "booking"}},
})


class LedgerTests(unittest.TestCase):
    def test_counts_used_scheduled_remaining(self):
        appts = [
            appt("a1", "pkg-1", "6 Session Package", "Confirmed", ts(2026, 8, 1), created=ts(2026, 7, 30)),
            appt("a2", "pkg-1", "6 Session Package", "Missed", ts(2026, 8, 8)),
            appt("a3", "pkg-1", "6 Session Package", "Canceled", ts(2026, 8, 15)),      # consumed (not replenished)
            appt("a4", "pkg-1", "6 Session Package", "Confirmed", ts(2026, 10, 1)),     # future -> scheduled
            appt("a5", "pkg-1", "6 Session Package", "WaitingConfirmation", ts(2026, 10, 8)),
            appt("x1", None, None, "Confirmed", ts(2026, 8, 1)),                        # not a package appt
        ]
        [l] = build_ledger(appts, CONFIG, today=TODAY)
        self.assertEqual((l.used, l.scheduled, l.remaining), (3, 2, 1))
        self.assertEqual(l.status, "active")
        self.assertEqual(l.purchase_date, "2026-07-30")
        self.assertEqual(l.expires_on, "2026-10-28")
        self.assertFalse(l.expired)

    def test_invoice_gives_purchase_date_and_amount(self):
        appts = [appt("a1", "pkg-1", "6 Session Package", "Confirmed", ts(2026, 8, 1), created=ts(2026, 7, 30))]
        invoices = [
            {"Number": 101, "Id": "inv1", "ClientIdNumber": 42, "Status": "Paid", "IssuedDate": ts(2026, 7, 20),
             "Items": [{"Description": "6 Session Package", "TotalAmount": 540.0, "Units": 1}]},
            {"Number": 99, "Id": "inv0", "ClientIdNumber": 7, "Status": "Paid", "IssuedDate": ts(2026, 7, 1),
             "Items": [{"Description": "6 Session Package", "TotalAmount": 540.0}]},  # other client
        ]
        [l] = build_ledger(appts, CONFIG, invoices, today=TODAY)
        self.assertEqual(l.purchase_invoice_number, 101)
        self.assertEqual(l.purchase_amount, 540.0)
        self.assertEqual(l.purchase_date, "2026-07-20")
        self.assertEqual(l.expires_on, "2026-10-18")

    def test_canceled_not_counted_when_config_says_so(self):
        cfg = PackageConfig.from_dict({"packages": {"6 Session Package": {"sessions": 6}},
                                       "count_as_used": ["Confirmed", "Missed"]})
        appts = [appt("a1", "pkg-1", "6 Session Package", "Confirmed", ts(2026, 8, 1)),
                 appt("a2", "pkg-1", "6 Session Package", "Canceled", ts(2026, 8, 8))]
        [l] = build_ledger(appts, cfg, today=TODAY)
        self.assertEqual((l.used, l.remaining), (1, 5))

    def test_linked_invoice_id_wins_over_description_match(self):
        a = appt("a1", "pkg-1", "6 Session Package", "Confirmed", ts(2026, 8, 1), created=ts(2026, 7, 30))
        a["InvoiceId"] = "inv-linked"
        invoices = [
            {"Number": 200, "Id": "inv-desc", "ClientIdNumber": 42, "Status": "Paid", "IssuedDate": ts(2026, 7, 20),
             "Items": [{"Description": "6 Session Package", "TotalAmount": 540.0}]},
            {"Number": 201, "Id": "inv-linked", "ClientIdNumber": 42, "Status": "Paid", "IssuedDate": ts(2026, 7, 29),
             "TotalAmount": 500.0, "Items": [{"Description": "Prepaid bundle", "TotalAmount": 500.0}]},
        ]
        [l] = build_ledger([a], CONFIG, invoices, today=TODAY)
        self.assertEqual(l.purchase_invoice_number, 201)
        self.assertEqual(l.purchase_amount, 500.0)
        self.assertEqual(l.purchase_date, "2026-07-29")

    def test_expired_and_exhausted_and_unknown(self):
        old = [appt(f"a{i}", "pkg-old", "6 Session Package", "Confirmed", ts(2026, 1, i + 1)) for i in range(3)]
        done = [appt(f"b{i}", "pkg-done", "6 Session Package", "Confirmed", ts(2026, 8, i + 1)) for i in range(6)]
        unk = [appt("c1", "pkg-unk", "Mystery Bundle", "Confirmed", ts(2026, 8, 1))]
        by_id = {l.package_instance_id: l for l in build_ledger(old + done + unk, CONFIG, today=TODAY)}
        self.assertEqual(by_id["pkg-old"].status, "expired")
        self.assertEqual(by_id["pkg-done"].status, "exhausted")
        self.assertEqual(by_id["pkg-done"].remaining, 0)
        self.assertEqual(by_id["pkg-unk"].status, "unknown-definition")
        self.assertIsNone(by_id["pkg-unk"].remaining)
        self.assertTrue(by_id["pkg-unk"].warnings)

    def test_config_name_match_is_case_insensitive(self):
        self.assertEqual(CONFIG.definition(" 6 session package ").sessions, 6)


class WebhookTests(unittest.TestCase):
    def test_appointment_event_with_package(self):
        evt = classify({"EventType": "AppointmentCreated", "ActionPerformedByClient": True,
                        "Appointment": appt("a1", "pkg-1", "6 Session Package", "Confirmed", ts(2026, 10, 1))})
        self.assertEqual(evt["kind"], "package_appointment")
        self.assertEqual(evt["package_instance_id"], "pkg-1")
        self.assertIsNotNone(classify({"EventType": "AppointmentDeleted",
                                       "Appointment": appt("a1", "pkg-1", "6 Session Package", "Canceled", 0)}))

    def test_non_package_appointment_ignored(self):
        self.assertIsNone(classify({"EventType": "AppointmentCreated", "Appointment": appt("a1", None, None, "Confirmed", 0)}))

    def test_invoice_event_filters_by_package_name(self):
        payload = {"EventType": "InvoicePaid", "Invoice": {"Number": 5, "ClientIdNumber": 42, "Status": "Paid",
                   "Items": [{"Description": "Single session"}, {"Description": "6 Session Package", "TotalAmount": 540}]}}
        evt = classify(payload, {"6 Session Package"})
        self.assertEqual(len(evt["items"]), 1)
        self.assertIsNone(classify(payload, {"Other Package"}))


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class ClientTests(unittest.TestCase):
    def _client(self, pages):
        calls = []

        def opener(req):
            calls.append(req)
            body = pages.pop(0)
            if isinstance(body, int):
                raise urllib.error.HTTPError(req.full_url, body, "err", {}, io.BytesIO(b"limit"))
            return FakeResponse(json.dumps(body).encode())

        c = IntakeQClient(api_key="k", min_seconds_between_calls=0, opener=opener, sleep=lambda s: None)
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

    def test_retries_on_429_then_raises_other_errors(self):
        c, calls = self._client([429, {"Id": "ok"}])
        self.assertEqual(c.appointment("x")["Id"], "ok")
        c2, _ = self._client([401])
        with self.assertRaises(IntakeQError) as cm:
            c2.appointment("x")
        self.assertEqual(cm.exception.status, 401)


if __name__ == "__main__":
    unittest.main()
