import io
import json
import re
import unittest
import urllib.error
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from superbill.api import SuperbillAPI
from superbill.build import build_superbill, is_completed
from superbill.config import load_config
from superbill.render import render_pdf
from superbill.sync import SuperbillSync

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=TZ)


def ms(d: date, hour: int = 9) -> int:
    return int(datetime(d.year, d.month, d.day, hour, tzinfo=TZ).timestamp() * 1000)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeIntakeQ:
    """Routes urllib requests to canned data; records writes."""

    def __init__(self, appointments, invoices, profile, diagnoses, files=None):
        self.appointments = appointments
        self.invoices = invoices
        self.profile = profile
        self.diagnoses = diagnoses
        self.files = files or []
        self.deleted = []
        self.uploads = []
        self.calls = []

    def __call__(self, req):
        url = req.full_url
        self.calls.append((req.get_method(), url))
        path = url.split("/api/v1/")[1].split("?")[0]
        if req.get_method() == "DELETE":
            self.deleted.append(path.split("/")[-1])
            return FakeResponse(b"")
        if req.get_method() == "POST" and path.startswith("files/"):
            self.uploads.append((path.split("/")[-1], req.get_header("Content-type"), req.data))
            return FakeResponse(b"")
        if path == "appointments/settings":
            return FakeResponse(json.dumps({"Services": [
                {"Id": "svc-fu", "Name": "Follow-Up", "Price": 399.0},
                {"Id": "svc-comp", "Name": "Complimentary Visit", "Price": 0.0},
            ]}).encode())
        if path == "appointments":
            rows = self.appointments
            if "page=2" in url:
                rows = []
            return FakeResponse(json.dumps(rows).encode())
        if path == "invoices":
            return FakeResponse(json.dumps(self.invoices if "page=1" in url else []).encode())
        if path == "clients":
            return FakeResponse(json.dumps([self.profile]).encode())
        if path.endswith("/diagnoses"):
            return FakeResponse(json.dumps(self.diagnoses).encode())
        if path == "files":
            return FakeResponse(json.dumps(self.files).encode())
        raise urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO(b""))


def appt(d: date, status="Confirmed", price=399.0, client_id=101, procedures=None, service="Follow-Up"):
    return {
        "Id": f"a-{d.isoformat()}-{client_id}",
        "ClientId": client_id,
        "ClientName": "Russ DonRussello",
        "ClientEmail": "russ@example.com",
        "Status": status,
        "StartDate": ms(d),
        "EndDate": ms(d) + 3_600_000,
        "Duration": 60,
        "ServiceName": service,
        "Price": price,
        "PractitionerEmail": "pt@example.com",
        "Procedures": procedures if procedures is not None else [{"ProcedureCode": "97530", "Price": 99.75, "Units": 4}],
        "LastModified": ms(d),
    }


PROFILE = {
    "ClientId": 101, "Name": "Russ DonRussello", "Email": "russ@example.com",
    "DateOfBirth": 73699200000,  # 1972-05-03 UTC midnight
    "StreetAddress": "12 Oak St", "City": "Greenville", "StateShort": "SC", "PostalCode": "29601",
}


def make(appointments, invoices, diagnoses=None, files=None, profile=PROFILE):
    fake = FakeIntakeQ(appointments, invoices, profile, diagnoses or [], files)
    api = SuperbillAPI(api_key="k", min_seconds_between_calls=0, opener=fake, sleep=lambda s: None)
    return api, fake


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config("superbill_config.json")

    def test_only_confirmed_past_visits_count(self):
        past = appt(date(2026, 9, 1))
        canceled = appt(date(2026, 9, 3), status="Canceled")
        missed = appt(date(2026, 9, 5), status="Missed")
        future = appt(date(2026, 10, 2))
        today_later = dict(appt(date(2026, 9, 30)), StartDate=ms(date(2026, 9, 30), 15), EndDate=ms(date(2026, 9, 30), 16))
        self.assertTrue(is_completed(past, NOW, self.cfg, TZ))
        for a in (canceled, missed, future, today_later):
            self.assertFalse(is_completed(a, NOW, self.cfg, TZ))

    def test_payment_plan_totals_match_template(self):
        dates = [date(2026, 6, 5), date(2026, 6, 8), date(2026, 6, 17), date(2026, 6, 19), date(2026, 6, 24), date(2026, 7, 1),
                 date(2026, 7, 6), date(2026, 7, 10), date(2026, 7, 15), date(2026, 7, 20), date(2026, 7, 23), date(2026, 7, 29),
                 date(2026, 7, 31), date(2026, 8, 7), date(2026, 8, 14), date(2026, 8, 28), date(2026, 8, 31), date(2026, 9, 7)]
        appts = [appt(d) for d in dates] + [appt(date(2026, 9, 12), status="Canceled"), appt(date(2026, 10, 5))]
        invoices = [{"Number": 10 + i, "Status": "Paid", "TotalAmount": 944.70, "AmountPaid": 944.70, "ClientPaymentPlanId": "plan1", "ClientPaymentPlanInterval": i} for i in range(6)]
        invoices.append({"Number": 99, "Status": "Canceled", "TotalAmount": 5000, "AmountPaid": 0})  # ignored
        api, _ = make(appts, invoices, [{"Code": "M54.2", "Date": "2026-06-05", "EndDate": None}, {"Code": "M99.9", "EndDate": "2025-01-01"}])
        data = build_superbill(api, 101, self.cfg, now=NOW)
        self.assertEqual(len(data.lines), 18)
        self.assertEqual(data.total_charges, 7182.00)
        self.assertEqual(data.total_billed, 5668.20)
        self.assertEqual(data.total_payments, 5668.20)
        self.assertEqual(data.provider_discount, 1513.80)
        self.assertEqual(data.balance, 0.0)
        self.assertTrue(data.payment_plan)
        self.assertFalse(data.paid_in_full)
        self.assertEqual(data.installments_billed, 6)
        self.assertEqual(data.diagnosis_codes, ["M54.2"])
        self.assertEqual(data.client_dob, date(1972, 5, 3))
        self.assertEqual(data.lines[0].procedure_label(), "97530 x4")
        self.assertEqual(data.lines[0].description, "Therapeutic Activity")
        self.assertEqual(data.episode_start, date(2026, 6, 5))
        self.assertEqual(data.episode_end, date(2026, 9, 7))

    def test_paid_in_full_and_balance_due(self):
        appts = [appt(date(2026, 8, 3)), appt(date(2026, 8, 10))]
        api, _ = make(appts, [{"Number": 1, "Status": "Paid", "TotalAmount": 700, "AmountPaid": 700, "ClientPaymentPlanId": None, "DiagnosisList": ["M25.561"]}])
        data = build_superbill(api, 101, self.cfg, now=NOW)
        self.assertTrue(data.paid_in_full)
        self.assertEqual(data.provider_discount, 98.0)
        self.assertEqual(data.diagnosis_codes, ["M25.561"])  # falls back to the invoice diagnosis list
        api2, _ = make(appts, [{"Number": 1, "Status": "Unpaid", "TotalAmount": 700, "AmountPaid": 300, "ClientPaymentPlanId": None}])
        data2 = build_superbill(api2, 101, self.cfg, now=NOW)
        self.assertFalse(data2.paid_in_full)
        self.assertEqual(data2.balance, 400.0)

    def test_service_defaults_when_no_procedures_and_zero_charge_skipped(self):
        appts = [appt(date(2026, 8, 3), procedures=[]), appt(date(2026, 8, 5), price=0, procedures=[], service="Complimentary Visit")]
        api, _ = make(appts, [])
        data = build_superbill(api, 101, self.cfg, now=NOW)
        self.assertEqual(len(data.lines), 1)
        self.assertEqual(data.lines[0].procedure_label(), "97530 x4")

    def test_zero_price_package_visits_use_service_list_price(self):
        appts = [
            appt(date(2026, 8, 3), price=97.0, procedures=[], service="Initial Consultation"),
            appt(date(2026, 8, 5), price=0, procedures=[], service="Follow-Up"),
            dict(appt(date(2026, 8, 7), price=0, procedures=[], service="Renamed"), ServiceId="svc-fu"),
            appt(date(2026, 8, 9), price=0, procedures=[], service="Complimentary Visit"),
        ]
        api, fake = make(appts, [{"Number": 1, "Status": "Paid", "TotalAmount": 97.0, "AmountPaid": 97.0}])
        data = build_superbill(api, 101, self.cfg, now=NOW)
        self.assertEqual([l.charge for l in data.lines], [97.0, 399.0, 399.0])
        self.assertEqual(data.total_charges, 895.0)
        self.assertEqual(sum(1 for m, u in fake.calls if "appointments/settings" in u), 1)

    def test_prepaid_package_is_prorated_to_visits_used(self):
        appts = [
            appt(date(2026, 8, 3), price=97.0, procedures=[], service="Initial Consultation"),
            appt(date(2026, 8, 5), price=0, procedures=[], service="Follow-Up"),
            appt(date(2026, 8, 7), price=0, procedures=[], service="Follow-Up"),
        ]
        invoices = [
            {"Number": 2, "Status": "Paid", "TotalAmount": 3998.0, "AmountPaid": 3998.0, "IssuedDate": ms(date(2026, 8, 4)),
             "Items": [{"Description": "12-Visit Package", "Units": 1, "Price": 4788.0, "TotalAmount": 3998.0}]},
            {"Number": 1, "Status": "Paid", "TotalAmount": 97.0, "AmountPaid": 97.0, "IssuedDate": ms(date(2026, 8, 3)),
             "Items": [{"Description": "Initial Consultation", "Units": 1, "Price": 97.0, "TotalAmount": 97.0}]},
        ]
        api, _ = make(appts, invoices)
        data = build_superbill(api, 101, self.cfg, now=NOW)
        self.assertEqual(data.total_charges, 895.0)
        self.assertAlmostEqual(data.total_billed, 97.0 + 3998.0 / 12 * 2, places=2)
        self.assertAlmostEqual(data.total_payments, data.total_billed, places=2)
        self.assertAlmostEqual(data.provider_discount, 895.0 - data.total_billed, places=2)
        self.assertEqual(data.balance, 0.0)
        self.assertEqual(data.invoice_numbers, [1, 2])

    def test_zero_price_list_price_can_be_turned_off(self):
        cfg = dict(self.cfg, zero_price_uses_list_price=False)
        api, _ = make([appt(date(2026, 8, 3), price=97.0, procedures=[]), appt(date(2026, 8, 5), price=0, procedures=[])], [])
        data = build_superbill(api, 101, cfg, now=NOW)
        self.assertEqual([l.charge for l in data.lines], [97.0])

    def test_no_visits_returns_none_and_other_clients_filtered(self):
        api, _ = make([appt(date(2026, 8, 3), client_id=202)], [])
        self.assertIsNone(build_superbill(api, 101, self.cfg, now=NOW))

    def test_episode_starts_at_latest_evaluation_when_configured(self):
        cfg = load_config("superbill_config.json")
        cfg["episode"]["start_service_pattern"] = "(?i)eval"
        appts = [appt(date(2026, 2, 1), service="Evaluation"), appt(date(2026, 2, 8)), appt(date(2026, 8, 1), service="Re-Evaluation"), appt(date(2026, 8, 8))]
        api, _ = make(appts, [])
        data = build_superbill(api, 101, cfg, now=NOW)
        self.assertEqual([l.date for l in data.lines], [date(2026, 8, 1), date(2026, 8, 8)])

    def test_render_produces_pdf(self):
        api, _ = make([appt(date(2026, 8, 3))], [{"Number": 1, "Status": "Paid", "TotalAmount": 399, "AmountPaid": 399}])
        data = build_superbill(api, 101, self.cfg, now=NOW)
        pdf = render_pdf(data, self.cfg)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1500)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config("superbill_config.json")
        self.cfg["sync"]["state_path"] = ""

    def test_refresh_replaces_previous_superbill(self):
        files = [{"Id": "old1", "FileName": "Superbill - Russ DonRussello.pdf"}, {"Id": "keep", "FileName": "insurance card.png"}]
        api, fake = make([appt(date(2026, 8, 3))], [{"Number": 1, "Status": "Paid", "TotalAmount": 399, "AmountPaid": 399}], files=files)
        s = SuperbillSync(api, self.cfg)
        r = s.refresh(101)
        self.assertEqual(r.action, "uploaded")
        self.assertEqual(r.file_name, "Superbill - Russ DonRussello.pdf")
        self.assertEqual(fake.deleted, ["old1"])
        self.assertEqual(len(fake.uploads), 1)
        client_id, ctype, body = fake.uploads[0]
        self.assertEqual(client_id, "101")
        self.assertTrue(ctype.startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="file"; filename="Superbill - Russ DonRussello.pdf"', body)
        self.assertIn(b"%PDF", body)
        # second run with identical data: fingerprint matches, nothing re-uploaded
        r2 = s.refresh(101)
        self.assertEqual(r2.action, "unchanged")
        self.assertEqual(len(fake.uploads), 1)

    def test_dry_run_never_writes(self):
        api, fake = make([appt(date(2026, 8, 3))], [], files=[{"Id": "old1", "FileName": "Superbill - x.pdf"}])
        r = SuperbillSync(api, self.cfg, dry_run=True).refresh(101)
        self.assertEqual(r.action, "uploaded")
        self.assertEqual(fake.deleted, [])
        self.assertEqual(fake.uploads, [])

    def test_sync_picks_clients_with_completed_visits_in_window(self):
        appts = [appt(date(2026, 9, 29), client_id=101), appt(date(2026, 10, 3), client_id=303), appt(date(2026, 9, 28), client_id=404, status="Canceled")]
        api, fake = make(appts, [])
        s = SuperbillSync(api, self.cfg)
        cands = s.candidates(3, NOW)
        self.assertIn(101, cands)
        self.assertNotIn(303, cands)  # future
        self.assertIn(404, cands)  # canceled past visit shows up via updatedSince (superbill may shrink)
        res = s.sync(3, NOW)
        self.assertEqual(res.candidates, 2)
        actions = {r.client_id: r.action for r in res.results}
        self.assertEqual(actions[101], "uploaded")
        self.assertEqual(actions[404], "no-visits")
        self.assertTrue(any("updatedSince=2026-09-29" in u for _, u in fake.calls))


class ServerTests(unittest.TestCase):
    def test_auth_and_routes(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import Request, urlopen

        from superbill.server import make_handler

        api, fake = make([appt(date(2026, 8, 3))], [])
        cfg = load_config("superbill_config.json")
        cfg["sync"]["state_path"] = ""
        s = SuperbillSync(api, cfg, dry_run=True)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(s, "sekrit"))
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            self.assertEqual(json.load(urlopen(base + "/healthz"))["ok"], True)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urlopen(Request(base + "/rebuild/101", method="POST"))
            self.assertEqual(cm.exception.code, 401)
            r = json.load(urlopen(Request(base + "/rebuild/101", method="POST", headers={"X-Superbill-Secret": "sekrit"})))
            self.assertEqual(r["action"], "uploaded")
            payload = json.dumps({"EventType": "AppointmentConfirmed", "ClientId": 101, "Appointment": appt(date(2026, 10, 9))}).encode()
            r = json.load(urlopen(Request(base + "/webhook", data=payload, method="POST", headers={"X-Superbill-Secret": "sekrit", "Content-Type": "application/json"})))
            self.assertEqual(r["action"], "deferred")
            r = json.load(urlopen(Request(base + "/sync?since_days=2", method="POST", headers={"X-Superbill-Secret": "sekrit"})))
            self.assertTrue(r["started"])
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
