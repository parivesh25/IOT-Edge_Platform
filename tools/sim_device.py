"""Publish labelled, synthetic readings without needing a physical board."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time
import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge-lab-platform-starter/edge-lab-platform"))
from common import RESERVED, valid_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="demo")
    parser.add_argument("--device", default="sim-1")
    parser.add_argument("--sensor", default="temperature")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--malformed", action="store_true", help="Publish one deliberately invalid value first")
    args = parser.parse_args()
    if not all(valid_name(value) for value in (args.project, args.device, args.sensor)) or args.project in RESERVED:
        parser.error("Use lowercase names with digits/hyphens; do not use a reserved project.")
    if args.count < 1 or args.interval < 0:
        parser.error("count must be positive and interval must not be negative.")
    ready = threading.Event()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.device)
    client.on_connect = lambda client, userdata, flags, reason, properties: ready.set() if not reason.is_failure else None
    client.connect(args.host, args.port)
    client.loop_start()
    try:
        if not ready.wait(5):
            raise RuntimeError("Broker connection timed out.")
        topic = f"lab/{args.project}/{args.device}/{args.sensor}"
        if args.malformed:
            client.publish(topic, json.dumps({"device": args.device, "sensor": args.sensor, "value": "not-a-number", "simulated": True})).wait_for_publish(timeout=5)
        for index in range(args.count):
            data = {"device": args.device, "sensor": args.sensor, "value": 25 + index % 20,
                    "ts": time.time(), "simulated": True}
            client.publish(topic, json.dumps(data)).wait_for_publish(timeout=5)
            if index < args.count - 1:
                time.sleep(args.interval)
        print(f"Published {args.count} simulated readings to {topic}.")
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
