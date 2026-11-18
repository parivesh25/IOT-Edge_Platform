"""Small, shared validation functions. No network or database side effects."""
import json
import math
import re
import statistics

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
RESERVED = {"alerts", "summary", "status"}


class MessageProblem(ValueError):
    def __init__(self, problem, fix):
        super().__init__(problem)
        self.fix = fix


def valid_name(value):
    return isinstance(value, str) and bool(NAME.fullmatch(value))


def valid_sensor(value):
    # Built-in sensors chip_temp and wifi_rssi use underscores.
    return isinstance(value, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", value))


def number(value):
    # bool is a Python int subclass, but JSON true is not a sensor measurement.
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def parse_reading(topic, payload):
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != "lab" or not valid_name(parts[1]) or not valid_name(parts[2]) or not valid_sensor(parts[3]):
        raise MessageProblem("Topic must be lab/<project>/<device>/<sensor>.",
                             "Use four topic segments with lowercase letters, digits or hyphens (1-48 characters); sensors also allow underscores.")
    _, project, device, sensor = parts
    if project in RESERVED:
        raise MessageProblem("This project name is reserved for platform messages.", "Choose a different PROJECT name.")
    if len(payload) > 4096:
        raise MessageProblem("Payload is larger than 4096 bytes.", "Publish one small JSON reading per message.")
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeError):
        raise MessageProblem("Payload is not valid JSON.", "Use double quotes and send one JSON object, without a trailing comma.") from None
    if not isinstance(data, dict):
        raise MessageProblem("Payload must be a JSON object.", "Send an object containing device, sensor and value.")
    missing = [key for key in ("device", "sensor", "value") if key not in data]
    if missing:
        raise MessageProblem("Missing required fields: " + ", ".join(missing) + ".", "Add every required field to the sketch's JSON output.")
    if data["device"] != device:
        raise MessageProblem("Payload device does not match the topic device.", "Use the same DEVICE_ID in the topic and JSON.")
    if data["sensor"] != sensor:
        raise MessageProblem("Payload sensor does not match the topic sensor.", "Use the same SENSOR_ID in the topic and JSON.")
    if not number(data["value"]):
        raise MessageProblem("value must be a finite number, not text or a boolean.", "Publish a numeric measurement without quotes.")
    if "ts" in data and (not number(data["ts"]) or data["ts"] < 0):
        raise MessageProblem("ts must be a nonnegative Unix timestamp in seconds.", "Omit ts on boards without a clock.")
    if "simulated" in data and type(data["simulated"]) is not bool:
        raise MessageProblem("simulated must be true or false.", "Use JSON true for simulator readings.")
    # Keep only contract fields. Extra fields (including accidental secrets) are
    # never saved or logged. Raw-message panels explain this filtering.
    clean = {key: data[key] for key in ("device", "sensor", "value", "ts", "simulated") if key in data}
    return project, clean


def sample_statistics(values, total=None):
    total = len(values) if total is None else total
    return {"samples": len(values), "lost": total - len(values),
            "mean": statistics.mean(values) if values else None,
            "min": min(values) if values else None, "max": max(values) if values else None,
            "stddev": statistics.pstdev(values) if values else None}
