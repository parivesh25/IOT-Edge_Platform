import json
import time
import unittest
from dashboard.app import create_app
from dashboard.sketches import sketch
from dashboard.store import Store


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:", max_rows=5, retention_seconds=60)
        self.client = create_app(self.store).test_client()

    def tearDown(self):
        self.store.close()

    def reading(self, project="demo", value=42, retained=False, now=None):
        self.store.ingest(f"lab/{project}/board/pot", json.dumps({"device": "board", "sensor": "pot", "value": value, "simulated": True}), retained=retained, now=now)

    def test_first_data_ignores_invalid_and_retained(self):
        response = self.client.post("/api/projects", json={"project": "demo", "device": "board", "sensor": "pot", "board": "esp32"})
        self.assertEqual(response.status_code, 201)
        self.reading(value="bad")
        self.reading(retained=True)
        self.assertIsNone(self.store.project("demo")["first_data_seconds"])
        self.assertFalse(self.store.project("demo")["online"])
        self.reading()
        project = self.store.project("demo")
        self.assertGreaterEqual(project["first_data_seconds"], 0)
        self.assertTrue(project["online"])
        self.assertFalse(self.store.projects(now=time.time()+16)[0]["online"])

    def test_two_projects_and_problem_api(self):
        self.reading("one")
        self.reading("two")
        self.reading("one", value="not-a-number")
        self.assertEqual({p["name"] for p in self.client.get("/api/overview").json["projects"]}, {"one", "two"})
        detail = self.client.get("/api/projects/one").json
        self.assertIn("finite number", detail["problems"][0]["problem"])
        self.assertEqual(len(detail["series"]["board/pot"]), 1)
        self.assertEqual(detail["series"]["board/pot"][0]["simulated"], 1)

    def test_retention_age_and_row_limit(self):
        now = time.time()
        for index in range(12):
            self.reading(now=now + index / 10)
        self.assertEqual(len(self.store.rows("SELECT * FROM readings")), 5)
        self.store.prune(now + 70)
        self.assertEqual(self.store.rows("SELECT * FROM readings"), [])

    def test_collision_evidence_requires_repetition(self):
        self.reading()
        payload = b'Client board already connected, closing old connection.'
        self.store.ingest("$SYS/broker/log/N", payload, now=100)
        self.assertEqual(self.store.rows("SELECT * FROM problems"), [])
        self.store.ingest("$SYS/broker/log/N", payload, now=101)
        self.assertIn("replacing device ID", self.store.rows("SELECT * FROM problems")[0]["problem"])

    def test_mosquitto_21_takeover_wording(self):
        self.reading()
        payload = b'Client board [192.0.2.1:4000] disconnected: session taken over.'
        self.store.ingest("$SYS/broker/log/N", payload, now=100)
        self.store.ingest("$SYS/broker/log/N", payload, now=101)
        self.assertIn("replacing device ID", self.store.rows("SELECT * FROM problems")[0]["problem"])

    def test_csv_and_safe_name_validation(self):
        self.reading()
        response = self.client.get("/api/projects/demo/readings.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("simulated", response.text)
        response = self.client.post("/api/projects", json={"project": "../bad", "device": "board", "sensor": "pot", "board": "uno"})
        self.assertEqual(response.status_code, 400)

    def test_generated_sketches_fill_identifiers(self):
        for board in ("esp32", "uno"):
            project = {"name": "greenhouse", "device": "board-2", "sensor": "light", "board": board}
            source = sketch(project)
            for value in ("greenhouse", "board-2", "light"):
                self.assertIn('"' + value + '"', source)
            self.assertIn("void setup()", source)
            self.assertIn("void loop()", source)

    def test_pages_and_same_origin_write_guard(self):
        for path in ("/", "/new", "/benchmark"):
            self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.post("/api/projects", json={}, headers={"Origin": "https://unrelated.example"})
        self.assertEqual(response.status_code, 403)

    def test_platform_events_keep_project_separation(self):
        self.store.ingest("lab/alerts/board/pot", json.dumps({"project": "one", "device": "board", "sensor": "pot", "value": 4000, "limit": 3000, "direction": "above"}))
        self.assertEqual(self.store.project_detail("one")["events"][0]["kind"], "alerts")
        self.assertIsNone(self.store.project("alerts"))
