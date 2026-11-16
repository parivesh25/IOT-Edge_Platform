"""Apply rules and publish a summary after ten readings of each sensor."""
import json
import os
from pathlib import Path
import sys
import time
import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import MessageProblem, RESERVED, parse_reading
from edge_service.logic import RULES, Windows, breached


def main():
    windows = Windows()
    connected = False
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="edge-service")

    def on_connect(client, userdata, flags, reason, properties):
        nonlocal connected
        connected = not reason.is_failure
        if connected:
            client.subscribe("lab/+/+/+")

    def on_disconnect(client, userdata, flags, reason, properties):
        nonlocal connected
        connected = False

    def on_message(client, userdata, message):
        if message.topic.split("/")[1] in RESERVED:
            return  # Never feed our own alerts/summaries back into the rules.
        try:
            project, data = parse_reading(message.topic, message.payload)
        except MessageProblem:
            return  # The dashboard explains invalid messages; do not log payloads.
        base = dict(data, project=project, ts=time.time())
        if breached(data["sensor"], data["value"]):
            direction, limit = RULES[data["sensor"]]
            alert = dict(base, direction=direction, limit=limit)
            client.publish(f"lab/alerts/{data['device']}/{data['sensor']}", json.dumps(alert))
        summary = windows.add(project, data)
        if summary:
            client.publish(f"lab/summary/{data['device']}/{data['sensor']}", json.dumps(dict(base, **summary)))

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    client.reconnect_delay_set(1, 10)
    client.connect_async(os.getenv("BROKER_HOST", "localhost"), int(os.getenv("BROKER_PORT", "1883")))
    client.loop_start()
    try:
        while True:
            if connected:
                Path(os.getenv("EDGE_HEARTBEAT", "/tmp/edge-heartbeat")).write_text(str(time.time()))
            time.sleep(3)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
