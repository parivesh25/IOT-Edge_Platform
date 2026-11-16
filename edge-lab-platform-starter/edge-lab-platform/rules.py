"""Small shared rules file. Invalid files fall back to the safe built-in table."""
import json
import os
from pathlib import Path
from common import number, valid_name
from edge_service.logic import RULES


def read_rules(path):
    try:
        if path.stat().st_size > 262144:
            return {}
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or len(data) > 1000:
            return {}
        for project, sensors in data.items():
            if not valid_name(project) or not isinstance(sensors, dict) or len(sensors) > 100:
                return {}
            for sensor, rule in sensors.items():
                if (not valid_name(sensor) or not isinstance(rule, list) or len(rule) != 2
                        or rule[0] not in ('above', 'below') or not number(rule[1])):
                    return {}
        return data
    except (OSError, ValueError):
        return {}


def rules_path():
    return Path(os.getenv('RULES_FILE', 'data/rules.json'))


def for_project(project, saved):
    return dict(RULES, **saved.get(project, {}))


def save_rule(project, sensor, direction, limit):
    if not valid_name(project) or not valid_name(sensor) or direction not in ('above', 'below') or not number(limit):
        raise ValueError('Choose a valid sensor name, above/below direction and finite numeric limit.')
    path = rules_path()
    saved = read_rules(path)
    if project not in saved and len(saved) >= 1000:
        raise ValueError('The rules file has reached its project limit.')
    sensors = saved.setdefault(project, {})
    if sensor not in sensors and len(sensors) >= 100:
        raise ValueError('A project can have at most 100 sensor overrides.')
    sensors[sensor] = [direction, limit]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(saved, indent=2), encoding='utf-8')
    temporary.replace(path)  # Atomic replacement prevents partially read JSON.
