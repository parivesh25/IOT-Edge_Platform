"""Per-sensor rules and count-based windows, easy to test without MQTT."""
from collections import OrderedDict
from common import sample_statistics

RULES = {"pot": ("above", 3000), "touch": ("above", 50000),
         "chip_temp": ("above", 50), "wifi_rssi": ("below", -75),
         "temperature": ("above", 35)}


def breached(sensor, value, rules=None):
    rule = (RULES if rules is None else rules).get(sensor)
    if rule is None:
        return False
    direction, limit = rule
    return value > limit if direction == "above" else value < limit


class Windows:
    def __init__(self, size=10, max_series=1000):
        self.size, self.max_series = size, max_series
        self.series = OrderedDict()

    def add(self, project, data):
        key = (project, data["device"], data["sensor"])
        values = self.series.setdefault(key, [])
        self.series.move_to_end(key)
        while len(self.series) > self.max_series:
            self.series.popitem(last=False)
        values.append(data["value"])
        if len(values) < self.size:
            return None
        stats = sample_statistics(values)
        self.series[key] = []
        return {"avg": stats["mean"], "min": stats["min"], "max": stats["max"], "count": stats["samples"]}
