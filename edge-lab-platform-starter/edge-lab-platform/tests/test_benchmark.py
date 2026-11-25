import unittest
from unittest.mock import patch
from dashboard.benchmark import public_host, measure


class BenchmarkTests(unittest.TestCase):
    def test_private_addresses_are_not_public_stand_ins(self):
        with patch("dashboard.benchmark.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 1883))]):
            with self.assertRaisesRegex(ValueError, "public IP"):
                public_host("localhost")
        with self.assertRaises(ValueError):
            public_host("https://example.com:1883")

    def test_unreachable_broker_reports_losses_without_crashing(self):
        with patch("dashboard.benchmark.mqtt.Client") as factory:
            factory.return_value.connect.side_effect = OSError("not reachable")
            result = measure("example.invalid")
        self.assertEqual(result["status"], "unreachable")
        self.assertEqual(result["lost"], 100)
        self.assertIsNone(result["mean"])

    def test_warmup_is_excluded(self):
        # A tiny fake MQTT loop echoes immediately, exercising real measurement
        # code without making a unit test depend on the public internet.
        class Reason:
            is_failure = False

        class EchoClient:
            def connect(self, *args, **kwargs):
                self.on_connect(self, None, None, Reason(), None)

            def subscribe(self, topic, qos):
                self.topic = topic
                self.on_subscribe(self, None, 1, [Reason()], None)

            def publish(self, topic, payload, qos, retain):
                message = type("Message", (), {"topic": topic, "payload": payload})()
                self.on_message(self, None, message)

            def loop_start(self): pass
            def loop_stop(self): pass
            def disconnect(self): pass

        with patch("dashboard.benchmark.mqtt.Client", return_value=EchoClient()):
            result = measure("unused", count=100)
        self.assertEqual(result["samples"], 100)
        self.assertEqual(result["lost"], 0)
        self.assertEqual(result["status"], "ok")
