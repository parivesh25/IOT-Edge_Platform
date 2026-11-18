"""Run from the application folder with unittest; no broker/hardware needed."""
import importlib.util
import json
from pathlib import Path
import unittest
from common import MessageProblem, parse_reading, sample_statistics
from edge_service.logic import Windows, breached


class MessageTests(unittest.TestCase):
    def test_builtin_sensor_names_with_underscores(self):
        for sensor in ('chip_temp', 'wifi_rssi'):
            project, data = parse_reading(f'lab/demo/board/{sensor}', json.dumps({'device':'board', 'sensor':sensor, 'value':12}))
            self.assertEqual(data['sensor'], sensor)

    def test_good_reading_and_extra_field_filter(self):
        project, data = parse_reading("lab/demo/board/pot", b'{"device":"board","sensor":"pot","value":12,"ignored":"example"}')
        self.assertEqual(project, "demo")
        self.assertEqual(data, {"device": "board", "sensor": "pot", "value": 12})

    def test_invalid_messages_explain_the_problem(self):
        good = {"device": "board", "sensor": "pot", "value": 10}
        cases = [("lab/demo", good, "Topic"), ("lab/demo/board/pot", {}, "Missing"),
                 ("lab/demo/board/pot", dict(good, value=True), "finite number"),
                 ("lab/demo/board/pot", dict(good, value="10"), "finite number"),
                 ("lab/demo/board/pot", dict(good, value=float("inf")), "finite number"),
                 ("lab/demo/board/pot", dict(good, device="other"), "device does not match"),
                 ("lab/demo/board/pot", dict(good, sensor="other"), "sensor does not match"),
                 ("lab/demo/board/pot", dict(good, ts=-1), "timestamp"),
                 ("lab/demo/board/pot", dict(good, simulated="yes"), "simulated"),
                 ("lab/alerts/board/pot", good, "reserved")]
        for topic, payload, phrase in cases:
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(MessageProblem, phrase):
                    parse_reading(topic, json.dumps(payload))
        with self.assertRaisesRegex(MessageProblem, "valid JSON"):
            parse_reading("lab/demo/board/pot", b'{broken')

    def test_huge_numeric_literal_is_rejected(self):
        with self.assertRaises(MessageProblem):
            parse_reading("lab/demo/board/pot", json.dumps({"device": "board", "sensor": "pot", "value": 10**400}))


class RuleTests(unittest.TestCase):
    def test_direction_and_boundary(self):
        self.assertFalse(breached("pot", 3000))
        self.assertTrue(breached("pot", 3001))
        self.assertTrue(breached("wifi_rssi", -76))
        self.assertFalse(breached("wifi_rssi", -75))
        self.assertFalse(breached("unknown", 1e10))

    def test_windows_do_not_mix_projects(self):
        windows = Windows(size=2)
        data = {"device": "board", "sensor": "pot", "value": 10}
        self.assertIsNone(windows.add("one", data))
        self.assertIsNone(windows.add("two", dict(data, value=100)))
        self.assertEqual(windows.add("one", dict(data, value=20)), {"avg": 15, "min": 10, "max": 20, "count": 2})
        self.assertIsNone(windows.add("one", data))

    def test_statistics_and_losses(self):
        self.assertEqual(sample_statistics([1, 3], 3), {"samples": 2, "lost": 1, "mean": 2, "min": 1, "max": 3, "stddev": 1})
        self.assertIsNone(sample_statistics([], 100)["mean"])
        self.assertEqual(sample_statistics([], 100)["lost"], 100)


class AddressHelperTests(unittest.TestCase):
    def test_only_broker_definition_changes(self):
        root = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location("show_ip", root / "tools/show_ip.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = b'#define WIFI_SSID "<example>"\r\n#define WIFI_PASS "<example>"\r\n#define BROKER_IP "192.0.2.1" // comment\r\n'
        after = module.replace_broker_ip(before, "192.0.2.2")
        self.assertEqual(after, before.replace(b'192.0.2.1', b'192.0.2.2'))
        with self.assertRaises(ValueError):
            module.replace_broker_ip(b'// no broker definition', "192.0.2.2")
