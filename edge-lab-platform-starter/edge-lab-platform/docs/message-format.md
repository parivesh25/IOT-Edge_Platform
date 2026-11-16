# Message format and topic scheme

Every device on the platform follows this contract, so anything built
downstream (edge rules, storage, dashboards, benchmarks) works with any board.

## Topic scheme

    lab/<project>/<device>/<sensor>

Example: `lab/demo/esp32s3-1/analog0`

Reserved topics written by the edge service:

| Topic | Meaning |
|---|---|
| `lab/alerts/<device>/<sensor>` | A reading crossed a rule's threshold |
| `lab/summary/<device>/<sensor>` | Summary of 10 readings (avg, min, max, count) |

These reserved messages contain `project`, `device`, `sensor`, and Unix `ts`.
Alerts add numeric `value` and `limit`, and `direction` (`above` or `below`).
Summaries add numeric `avg`, `min`, `max`, and integer `count`. Both propagate
`simulated: true` when based on simulator data. The explicit `project` field
keeps events grouped correctly even though the reserved topic has no project segment.

## Message body (JSON, one reading per message)

| Field | Type | Required | Description |
|---|---|---|---|
| `device` | string | yes | Unique device ID, e.g. `esp32s3-1` |
| `sensor` | string | yes | Sensor name on that device, e.g. `analog0` |
| `value` | number | yes | The raw reading |
| `ts` | number | added by gateway/edge | Unix time in seconds. Devices without a clock leave it out and the gateway adds it |
| `simulated` | boolean | no | `true` marks generated test readings |

Example:

    {"device":"esp32s3-1","sensor":"analog0","value":2048}

## Rules

- One reading per message.
- Project/device/sensor names use 1-48 lowercase letters, digits or hyphens,
  beginning with a letter or digit. Project names `alerts`, `summary` and `status`
  are reserved. Topic and payload device/sensor names must match.
- Numbers must be finite, not quoted strings, booleans, NaN or infinity. Optional
  `ts` must be nonnegative Unix seconds. Maximum payload size is 4096 bytes.
- Extra JSON fields are ignored and not stored by the dashboard. Its raw viewer
  displays contract fields only. Invalid payload text is not stored.
- Publish live readings without MQTT retain. Retained historical readings may
  be displayed but do not complete the wizard or mark a project online.
- The generated Uno sketch includes a `project` field in its USB serial line.
  The gateway consumes that field to choose the MQTT topic, then removes it.
  The original Uno example without this field continues to use gateway `--project`
  (default `demo`). The MQTT reading contract still uses device/sensor/value.
- Keep `device` IDs unique across the lab (they are also the MQTT client ID on WiFi boards).
- Change this contract only by editing this file and telling everyone who builds on the platform.
