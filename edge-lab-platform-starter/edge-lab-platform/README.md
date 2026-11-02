# [PLATFORM NAME]

A reusable edge computing platform for our lab: connect a sensor, run logic
on an edge device, and see live data, using ready-made templates instead of
setting everything up from scratch. It also measures its own performance
(latency, data sent) so every project gets benchmark numbers.

**Status:** work in progress (course project, [semester/year]).

## Architecture

    Sensor -> Board -> (WiFi, or USB serial + gateway) -> MQTT broker -> Edge service -> Dashboard

See `docs/architecture.md` and `docs/message-format.md`.

## Supported hardware

| Board | Connection | Folder |
|---|---|---|
| ESP32-S3 (N16R8) | WiFi, direct MQTT | `firmware/esp32_publisher/` |
| Arduino Uno R3 | USB serial via gateway | `firmware/uno_serial/` + `gateway/` |

## Quick start

1. **Start the broker** (needs Docker): `docker compose up -d`
2. **Watch messages** with MQTT Explorer: connect to `localhost`, port `1883`.
3. **ESP32:** copy `firmware/esp32_publisher/secrets.example.h` to `secrets.h`,
   fill in your WiFi name, password, and your computer's LAN IP, then upload the sketch
   (board: ESP32S3 Dev Module, PSRAM: OPI, Flash: 16MB).
4. **Uno (optional):** upload `firmware/uno_serial/uno_serial.ino`, close the Serial Monitor, then run
   `pip install -r requirements.txt` and `python gateway/serial_gateway.py <port>`.
5. **Edge service:** `python edge_service/edge_service.py`

## Roadmap

- [ ] ESP32 publishes to the broker
- [ ] Uno joins through the serial gateway
- [ ] Edge service: rules and summaries
- [ ] Local storage (SQLite)
- [ ] Dashboard (Grafana)
- [ ] Latency benchmark: edge vs cloud
- [ ] Plug-in system for student rules
- [ ] Time-to-first-data test with a new student

## Reference and differences

Based on the NoteLab reference architecture (arXiv:2103.11396, "Engineering an
IoT-Edge-Cloud Computing System Architecture: Lessons Learnt from An
Undergraduate Lab Course"). Added here: a standard message format, a gateway for
boards without WiFi, edge rules, and built-in benchmarking.

## License

MIT License
