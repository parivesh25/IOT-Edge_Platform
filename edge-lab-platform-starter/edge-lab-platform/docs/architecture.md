# Architecture

    Sensor -> Board -> (WiFi, or USB serial + gateway) -> MQTT broker -> Edge service -> Dashboard / storage

| Layer | Component | Where it lives |
|---|---|---|
| IoT | ESP32 (WiFi), Arduino Uno (serial) | `firmware/` |
| Gateway | Serial-to-MQTT bridge for boards without WiFi | `gateway/` |
| Edge | Mosquitto broker, edge service (rules, summaries) | `broker/`, `edge_service/` |
| Cloud | Optional, for the edge-vs-cloud comparison | not built yet |

Reference design: the NoteLab three-layer IoT-edge-cloud architecture
(arXiv:2103.11396). Differences from NoteLab are listed in the README.
