"""Minimal edge service: applies per-sensor rules and summarises data locally.

Subscribes to every device under lab/demo, raises an alert when a reading
crosses that sensor's limit (see RULES), and publishes one summary per
WINDOW_SIZE readings. Nothing here needs the internet.
"""
import json
import time

import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
WINDOW_SIZE = 10

# sensor name -> (direction, limit). Calibrate from what you see in MQTT Explorer.
RULES = {
    "pot":         ("above", 3000),    # ADC reads 0-4095
    "touch":       ("above", 50000),   # adjust to your board's touched vs untouched values
    "chip_temp":   ("above", 50),
    "wifi_rssi":   ("below", -75),
    "temperature": ("above", 35),      # the simulated device
}
windows = {}   # recent readings, kept separately for each (device, sensor)


def breached(sensor, value):
    rule = RULES.get(sensor)
    if rule is None:
        return False                   # no rule for this sensor: never alert
    direction, limit = rule
    return
