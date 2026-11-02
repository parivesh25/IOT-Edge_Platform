"""Serial-to-MQTT gateway for boards without WiFi (e.g. Arduino Uno).

Usage:  python gateway/serial_gateway.py COM3
        python gateway/serial_gateway.py /dev/ttyACM0
Close the Arduino Serial Monitor first: only one program can own the port.
"""
import json
import sys
import time

import paho.mqtt.client as mqtt
import serial

PROJECT = "demo"
BROKER_HOST = "localhost"
BAUD = 9600

if len(sys.argv) < 2:
    sys.exit("Usage: python gateway/serial_gateway.py <serial-port>")

ser = serial.Serial(sys.argv[1], BAUD, timeout=2)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER_HOST, 1883)
client.loop_start()                   # MQTT networking runs in the background

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue                      # skip garbled lines (common at startup)

    data["ts"] = time.time()          # the Uno has no clock, so add one here
    topic = f"lab/{PROJECT}/{data['device']}/{data['sensor']}"
    client.publish(topic, json.dumps(data))
    print("published", topic, data)
