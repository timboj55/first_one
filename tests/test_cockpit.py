import csv
import datetime as dt
import io
import json
import os
import tempfile
import unittest
import urllib.request

from intakeq_packages import IntakeQClient, PackageConfig, build_ledger
from intakeq_packages.ledger_export import merge_export_into_ledger, write_ledger_files
from intakeq_packages.nightly import run_nightly
from intakeq_packages.sources import ApptPackageMap, PackagesExport, detect_columns, EXPORT_FIELD_HINTS
from intakeq_packages.webhook import enrich, make_handler, needs_enrichment

MS = 1000
TODAY = dt.date(2026, 9, 26)
def ts(y, m, d): return int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp()) * MS

CONFIG = PackageConfig.load(os.path.join(os.path.dirname(__file__), "..", "packages.json"))

EXPORT_CSV = """Id,Client Id,Client Name,Package Name,Total Sessions,Unused Sessions,Purchase Date,Expiration Date,Practitioner
pkg-A,42,Pat Client,20-Visit Package,8,5,01/15/2026,01/14/2027,Dr. X
pkg-B,43,Sam Client,8-Visit Package,8,8,03/01/2026,,Dr. X
"""

def write(dirpath, name, content):
    p = os.path.join(dirpath, name)
    with open(p, "w", newline="") as f:
        f.write(content)
    return p


class SourcesTests(unittest.TestCase):
    def test_export_column_detection_and_parse(self):
        with tempfile.TemporaryDirectory() as d:
            e = PackagesExport.load(write(d, "packages_all.csv", EXPORT_CSV))
        self.assertEqual(e.mapping["package_id"], "Id")
        self.assertEqual(e.mapping["sessions_total"], "Total Sessions")
        self.assertEqual(e.mapping["sessions_unused"], "Unused Sessions")
        self.assertEqual(e.mapping["purchase_date"], "Purchase Date")
        a = e.by_package_id()["pkg-A"]
        self.assertEqual(a.sessions_total, 8)           # name says 20, purchase says 8
        self.assertEqual(a.purchase_date, dt.date(2026, 1, 15))
        self.assertEqual(a.expiry_date, dt.date(2027, 1, 14))
        self.assertEqual(e.missing_fields(), [])

    def test_detect_prefers_exact_over_substring(self):
        m = detect_columns(["Package Id", "Id", "Client Id"], EXPORT_FIELD_HINTS)
        self.assertEqual(m["package_id"], "Package Id")
        self.assertEqual(m["client_id"], "Client Id")

    def test_appt_map_shapes(self):
        as_dict = {"a1": {"AppointmentPackageId": "pkg-A", "AppointmentPackageName": "20-Visit Package", "ClientId": 42, "Status": "Confirmed", "StartDate": ts(2026, 2, 1)},
                   "a2": {"AppointmentPackageId": None, "ClientId": 42}}
        as_list = [{"appointmentId": "a1", "packageId": "pkg-A", "packageName": "20-Visit Package", "clientId": 42, "status": "Confirmed", "startDate": "2026-02-01"}]
        as_flat = {"a1": "pkg-A", "a2": None}
        with tempfile.TemporaryDirectory() as d:
            for i, shape in enumerate([as_dict, as_list, as_flat]):
                p = write(d, f"m{i}.json", json.dumps(shape))
                m = ApptPackageMap.load(p)
                appts = m.as_appointments()
                self.assertEqual([a["Id"] for a in appts], ["a1"], shape)
                self.assertEqual(appts[0]["AppointmentPackageId"], "pkg-A")
                # round trip keeps the top-level shape
                changed = m.upsert_from_appointment({"Id": "a9", "AppointmentPackageId": "pkg-B", "AppointmentPackageName": "8-Visit Package", "ClientId": 43, "Status": "Confirmed", "StartDate": ts(2026, 3, 5)})
                self.assertTrue(changed)
                m.save()
                back = json.load(open(p))
                self.assertEqual(type(back), type(shape))
                self.assertEqual(len(ApptPackageMap.load(p).records), len(m.records))


class LedgerExportTests(unittest.TestCase):
    def _ledgers(self):
        appts = [
            {"Id": f"a{i}", "ClientId": 42, "ClientName": "Pat Client", "Status": "Confirmed", "StartDate": ts(2026, 2, i + 1), "DateCreated": ts(2026, 1, 20),
             "AppointmentPackageId": "pkg-A", "AppointmentPackageName": "20-Visit Package"} for i in range(3)
        ] + [
            {"Id": "n1", "ClientId": 44, "ClientName": "New Client", "Status": "Confirmed", "StartDate": ts(2026, 9, 20), "DateCreated": ts(2026, 9, 10),
             "AppointmentPackageId": "pkg-NEW", "AppointmentPackageName": "12-Visit Package"},
        ]
        return build_ledger(appts, CONFIG, today=TODAY)

    def test_export_total_overrides_name_default_and_unused_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            export = PackagesExport.load(write(d, "packages_all.csv", EXPORT_CSV))
            derived = merge_export_into_ledger(self._ledgers(), export, CONFIG, today=TODAY)
            by = {x["package_id"]: x for x in derived}
            self.assertEqual(by["pkg-A"]["sessions_total"], 8)
            self.assertEqual(by["pkg-A"]["sessions_total_source"], "export")
            self.assertEqual(by["pkg-A"]["remaining_derived"], 5)
            self.assertEqual(by["pkg-A"]["unused_practiceq"], 5)
            self.assertEqual(by["pkg-A"]["expires_on"], "2027-01-14")
            self.assertEqual(by["pkg-B"]["source"], "export-only")
            self.assertEqual(by["pkg-B"]["remaining_derived"], 8)
            self.assertEqual(by["pkg-NEW"]["source"], "appointments-only")
            self.assertEqual(by["pkg-NEW"]["sessions_total"], 12)
            self.assertEqual(by["pkg-NEW"]["expires_on"], "2027-09-09")  # 364 days after first booking fallback
            paths = write_ledger_files(d, export, self._ledgers(), derived)
            rows = list(csv.DictReader(open(paths["ledger"])))
            self.assertEqual(list(rows[0].keys()), export.columns)           # identical columns
            a = next(r for r in rows if r["Id"] == "pkg-A")
            self.assertEqual(a["Unused Sessions"], "5")                        # PracticeQ counter untouched
            self.assertEqual(a["Total Sessions"], "8")
            new = next(r for r in rows if r["Id"] == "pkg-NEW")
            self.assertEqual(new["Package Name"], "12-Visit Package")
            self.assertEqual(new["Unused Sessions"], "")                       # never invented
            self.assertEqual(len(rows), 3)


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_client(routes):
    """routes: list of (substring-of-url, json) consumed in order of matching."""
    calls = []
    def opener(req):
        calls.append(req.full_url)
        for i, (frag, body) in enumerate(routes):
            if frag in req.full_url:
                routes.pop(i)
                return FakeResponse(json.dumps(body).encode())
        raise AssertionError("unexpected url " + req.full_url)
    return IntakeQClient(api_key="k", min_seconds_between_calls=0, opener=opener, sleep=lambda s: None), calls


class NightlyTests(unittest.TestCase):
    def test_nightly_fetches_details_updates_map_and_writes_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            appt_map = write(d, "appt_packages.json", json.dumps({"a1": {"AppointmentPackageId": "pkg-A", "AppointmentPackageName": "20-Visit Package", "ClientId": 42, "Status": "Confirmed", "StartDate": ts(2026, 2, 1)}}))
            export = write(d, "packages_all.csv", EXPORT_CSV)
            client, calls = fake_client([
                ("appointments?", [{"Id": "a2", "ClientId": 42, "Status": "Confirmed"}, {"Id": "a3", "ClientId": 42, "Status": "Canceled"}]),
                ("appointments/a2", {"Id": "a2", "ClientId": 42, "Status": "Confirmed", "StartDate": ts(2026, 9, 30), "AppointmentPackageId": "pkg-A", "AppointmentPackageName": "20-Visit Package"}),
                ("appointments/a3", {"Id": "a3", "ClientId": 42, "Status": "Canceled", "StartDate": ts(2026, 9, 1), "AppointmentPackageId": None}),  # released
            ])
            now = dt.datetime(2026, 9, 26, 3, 0, tzinfo=dt.timezone.utc)
            rep = run_nightly(client, CONFIG, appt_map, export, os.path.join(d, "out"), since="2026-09-25",
                              deadline=now + dt.timedelta(hours=1), now=now, clock=lambda: now)
            self.assertEqual(rep["changed_listed"], 2)
            self.assertEqual(rep["details_fetched"], 2)
            self.assertEqual(rep["api_calls"], 3)
            self.assertIn("updatedSince=2026-09-25", calls[0])
            m = ApptPackageMap.load(appt_map)
            self.assertEqual(m.records["a2"]["package_id"], "pkg-A")
            self.assertIsNone(m.records["a3"]["package_id"])
            derived = {r["package_id"]: r for r in csv.DictReader(open(rep["files"]["derived"]))}
            self.assertEqual(derived["pkg-A"]["used"], "1")
            self.assertEqual(derived["pkg-A"]["scheduled"], "1")
            self.assertEqual(derived["pkg-A"]["remaining_derived"], "6")
            state = json.load(open(os.path.join(d, "out", "nightly_state.json")))
            self.assertEqual(state["next_since"], "2026-09-25")

    def test_nightly_stops_at_deadline_and_carries_over(self):
        with tempfile.TemporaryDirectory() as d:
            appt_map = write(d, "appt_packages.json", "{}")
            client, calls = fake_client([("appointments?", [{"Id": "a1"}, {"Id": "a2"}])])
            now = dt.datetime(2026, 9, 26, 3, 0, tzinfo=dt.timezone.utc)
            rep = run_nightly(client, CONFIG, appt_map, None, os.path.join(d, "out"), since="2026-09-25",
                              deadline=now - dt.timedelta(seconds=1), now=now, clock=lambda: now)
            self.assertEqual(rep["details_fetched"], 0)
            self.assertEqual(sorted(rep["carried_over_ids"]), ["a1", "a2"])


class WebhookEnrichTests(unittest.TestCase):
    def test_needs_enrichment_and_enrich(self):
        thin = {"EventType": "AppointmentCreated", "Appointment": {"Id": "a1", "ClientId": 42}}
        self.assertTrue(needs_enrichment(thin))
        full = enrich(thin, lambda i: {"Id": i, "ClientId": 42, "AppointmentPackageId": "pkg-A", "AppointmentPackageName": "20-Visit Package", "Status": "Confirmed"})
        self.assertEqual(full["Appointment"]["AppointmentPackageId"], "pkg-A")
        self.assertFalse(needs_enrichment(full))

    def test_secret_path_rejects_wrong_url(self):
        import threading
        from http.server import HTTPServer
        got = []
        srv = HTTPServer(("127.0.0.1", 0), make_handler(got.append, None, secret_path="s3cr3t",
                                                        fetch_appointment=lambda i: {"Id": i, "AppointmentPackageId": "pkg-A", "AppointmentPackageName": "x", "Status": "Confirmed"}))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        body = json.dumps({"EventType": "AppointmentCreated", "Appointment": {"Id": "a1"}}).encode()
        def post(path):
            try:
                return urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method="POST")).status
            except urllib.error.HTTPError as e:
                return e.code
        self.assertEqual(post("/intakeq/wrong"), 404)
        self.assertEqual(post("/intakeq/s3cr3t"), 200)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["package_instance_id"], "pkg-A")  # enriched via single-appointment fetch
        srv.shutdown()


if __name__ == "__main__":
    unittest.main()
