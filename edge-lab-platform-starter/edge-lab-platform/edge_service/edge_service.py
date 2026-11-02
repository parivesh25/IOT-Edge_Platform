"""Minimal edge service: applies a rule and summarises data locally.

Subscribes to every device under lab/demo, raises an alert when a reading
crosses THRESHOLD, and publishes one summary per WINDOW_SIZE readings.
Nothing here needs the internet.
"""
import json
import time

import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
THRESHOLD = 3000      # tuned for the ESP32's 0-4095 readings; adjust per sensor
WINDOW_SIZE = 10
windows = {}          # recent readings, kept separately for each device


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("lab/demo/+/+")  # '+' matches exactly one topic level


def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    device, value = data["device"], data["value"]

    # Edge decision: made locally, in milliseconds
    if value > THRESHOLD:
        alert = {"device": device, "value": value, "ts": time.time()}
        client.publish(f"lab/alerts/{device}", json.dumps(alert))

    # Edge data reduction: send one summary instead of WINDOW_SIZE readings
    window = windows.setdefault(device, [])
    window.append(value)
    if len(window) >= WINDOW_SIZE:
        summary = {"device": device,
                   "avg": sum(window) / len(window),
                   "min": min(window), "max": max(window)}
        client.publish(f"lab/summary/{device}", json.dumps(summary))
        window.clear()


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, 1883)
client.loop_forever()
