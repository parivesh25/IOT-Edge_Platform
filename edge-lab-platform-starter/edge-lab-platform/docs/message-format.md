# Message format and topic scheme

Every device on the platform follows this contract, so anything built
downstream (edge rules, storage, dashboards, benchmarks) works with any board.

## Topic scheme

    lab/<project>/<device>/<sensor>

Example: `lab/demo/esp32s3-1/analog0`

Reserved topics written by the edge service:

| Topic | Meaning |
|---|---|
| `lab/alerts/<device>` | A reading crossed a rule's threshold |
| `lab/summary/<device>` | Windowed summary (avg, min, max) |

## Message body (JSON, one reading per message)

| Field | Type | Required | Description |
|---|---|---|---|
| `device` | string | yes | Unique device ID, e.g. `esp32s3-1` |
| `sensor` | string | yes | Sensor name on that device, e.g. `analog0` |
| `value` | number | yes | The raw reading |
| `ts` | number | added by gateway/edge | Unix time in seconds. Devices without a clock leave it out and the gateway adds it |

Example:

    {"device":"esp32s3-1","sensor":"analog0","value":2048}

## Rules

- One reading per message.
- Keep `device` IDs unique across the lab (they are also the MQTT client ID on WiFi boards).
- Change this contract only by editing this file and telling everyone who builds on the platform.
