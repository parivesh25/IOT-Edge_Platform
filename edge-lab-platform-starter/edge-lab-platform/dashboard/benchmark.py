"""MQTT round trips: one perf_counter clock, one unique topic, no sensor data."""
import ipaddress
import re
import socket
import threading
import time
import uuid

import paho.mqtt.client as mqtt
from common import sample_statistics


def public_host(host):
    if not isinstance(host, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}", host):
        raise ValueError("Enter a public broker hostname, without a URL, port or credentials.")
    # The benchmark input must not become a way to probe private services.
    addresses = socket.getaddrinfo(host, 1883, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Cloud stand-ins must resolve to public IP addresses.")
    return addresses[0][4][0]


def measure(host, port=1883, count=100, timeout=1.0):
    topic = "iot-edge-benchmark/" + uuid.uuid4().hex
    connected, subscribed, echo = threading.Event(), threading.Event(), threading.Event()
    pending = {"payload": None, "start": 0.0, "latency": None}
    lock = threading.Lock()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bench-" + uuid.uuid4().hex[:16])
    client.connect_timeout = 4

    def on_connect(client, userdata, flags, reason, properties):
        if not reason.is_failure:
            connected.set()
            client.subscribe(topic, qos=0)

    def on_subscribe(client, userdata, mid, reasons, properties):
        if all(not reason.is_failure for reason in reasons):
            subscribed.set()

    def on_message(client, userdata, message):
        with lock:
            if message.topic == topic and message.payload == pending["payload"]:
                pending["latency"] = (time.perf_counter() - pending["start"]) * 1000
                echo.set()

    client.on_connect, client.on_subscribe, client.on_message = on_connect, on_subscribe, on_message
    values = []
    try:
        client.connect(host, port, keepalive=30)
        client.loop_start()
        if not connected.wait(5) or not subscribed.wait(5):
            raise OSError("Broker handshake did not finish.")
        for index in range(count + 1):
            # index zero is a warm-up and is excluded, even when it is lost.
            payload = str(index).encode("ascii")
            with lock:
                echo.clear()
                pending.update(payload=payload, start=time.perf_counter(), latency=None)
            client.publish(topic, payload, qos=0, retain=False)
            arrived = echo.wait(timeout)
            with lock:
                if arrived and index > 0:
                    values.append(pending["latency"])
                pending["payload"] = None
        return dict(sample_statistics(values, count), status="ok" if values else "unreachable")
    except (OSError, ValueError):
        return dict(sample_statistics(values, count), status="unreachable")
    finally:
        client.disconnect()
        client.loop_stop()


class Benchmarks:
    def __init__(self, store, local_host, local_port):
        self.store, self.local_host, self.local_port = store, local_host, local_port
        self.lock = threading.Lock()
        # An interrupted process must not leave the UI waiting forever.
        for run in store.benchmarks():
            if run["status"] == "running":
                store.benchmark_save(run["id"], run["started"], run["cloud_host"], "interrupted")

    def start(self, cloud_host):
        if not isinstance(cloud_host, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}", cloud_host):
            raise ValueError("Enter a public hostname, without a URL or credentials.")
        if not self.lock.acquire(blocking=False):
            raise ValueError("A benchmark is already running. Wait for its results.")
        run_id, started = uuid.uuid4().hex, time.time()
        self.store.benchmark_save(run_id, started, cloud_host, "running")

        def work():
            try:
                local = measure(self.local_host, self.local_port)
                try:
                    address = public_host(cloud_host)
                    cloud = measure(address)
                except (OSError, ValueError):
                    cloud = dict(sample_statistics([], 100), status="unreachable")
                self.store.benchmark_save(run_id, started, cloud_host, "complete", {"local": local, "cloud": cloud})
            except Exception:
                # No connection details or arbitrary payloads are logged.
                self.store.benchmark_save(run_id, started, cloud_host, "failed")
            finally:
                self.lock.release()

        threading.Thread(target=work, daemon=True).start()
        return run_id
