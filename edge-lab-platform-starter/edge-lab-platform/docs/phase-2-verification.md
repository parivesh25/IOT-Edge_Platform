# Priority build verification

## Real ESP32 follow-up, 18 November 2026

The student uploaded the sketch and supplied Serial Monitor output. The dashboard
API independently confirmed device esp32s3eth-1 online in project demo, receiving
pot, touch, chip_temp and wifi_rssi with simulated=0 at about four readings/second.
Real edge summaries were also observed. A validator bug rejecting underscores
in built-in sensor names was fixed; 20 unit tests passed including a regression
test for chip_temp/wifi_rssi. Sensor underscores are documented in the contract.
This supersedes the earlier ESP32 publishing verification limitation below.
Uno hardware and sensor calibration remain unverified.

Verified on 16 November 2026 using the isolated codex/dashboard worktree.

- 19 standard-library unit tests passed.
- Docker rebuilt successfully; broker, edge and dashboard report healthy.
- Two simulator projects, malformed numeric values, first-data detection,
  SQLite readings and edge summaries passed the real smoke test.
- Repeated actual MQTT client-ID takeovers appeared in Problems after supporting
  both Mosquitto 2.0 and 2.1 log wording.
- Browser inspection verified project cards, generated ESP32 checklist, the live
  first-data success indicator, sensor chart, simulated badges and benchmark table.
- A deliberately unreachable public hostname produced an unreachable result.
- A previous real public-broker run received 89/100 samples: local mean 0.22 ms,
  public mean 421.59 ms, with 11 public samples lost. Results vary with the network.

## File guide

Paths below are relative to the nested application unless marked Git root.

| Files | Purpose |
|---|---|
| Git-root tools/show_ip.py | Detect LAN IPv4; optionally change only BROKER_IP in an existing header |
| docs/network-notes.md | Hotspot, isolation, firewall and manual board instructions |
| Dockerfile, .dockerignore, docker-compose.yml | Build the Python services, exclude secrets, start three services with health checks |
| requirements.txt | Python dependencies; no JavaScript build tools |
| broker/mosquitto.conf | Development MQTT listener and notices used for collision detection |
| common.py | Shared topic, reading and numeric validation; statistics |
| edge_service/logic.py | Per-sensor thresholds and separate ten-reading windows |
| edge_service/edge_service.py | MQTT subscription, alerts, summaries and health heartbeat |
| dashboard/store.py | Bounded SQLite history, projects, problems and first-data measurements |
| dashboard/benchmark.py | Warm-up, 100 round trips, losses and asynchronous run history |
| dashboard/sketches.py | Generate sketches from tracked examples without reading secrets |
| dashboard/app.py | Flask routes, CSV export, SSE and MQTT listener |
| dashboard/templates/index.html | Accessible page structure and forms |
| dashboard/static/style.css | Responsive local styles |
| dashboard/static/app.js | Live updates, SVG charts, forms and copy buttons |
| firmware/esp32_publisher/esp32_publisher.ino | Larger buffers for validated long identifiers; unverified on hardware |
| gateway/serial_gateway.py | Validate serial readings and route generated Uno project names |
| Git-root gateway/serial_gateway.py | Short command wrapper for the nested gateway |
| Git-root tools/sim_device.py | Labelled synthetic readings and deliberately malformed test input |
| Git-root tools/smoke_test.py | Running-stack tests with two projects and a real benchmark |
| tests/test_logic.py, test_dashboard.py, test_benchmark.py | Unit tests without boards or internet |
| Git-root tools/workspace.ps1 | Correct paths, isolated Compose project and laptop IP passed to Docker |
| Git-root .codex/environments/environment.toml | Setup, cleanup, Start, Stop, Run tests and Open dashboard actions |
| Both README.md files | Start commands, architecture, limits and verified roadmap items |
| docs/message-format.md | Per-sensor reserved topics, validation and simulator extension |

Hardware flashing, firmware compilation, physical sensors, real board WiFi and
hotspot/firewall access from another device remain unverified. Hardware roadmap
items remain unticked. No credentials were copied or entered by the agent.

After the priority build was committed, project rule editing was added and tested:
saving a below-100 temperature rule produced real edge alerts without restarting
the edge service. The /lab overview returned successfully, and the scaffolder
created projects/scaffold-check/README.md, retained as an example test artifact.

Additional files: rules.py validates and atomically saves the shared rules file;
tools/new_project.py creates project READMEs; docs/connect-your-project.md provides
the student walkthrough. Compose mounts the rules volume read-only in the edge
service. The dashboard form and API save rules; the edge reloads on incoming
readings at most every three seconds. Invalid/missing files use built-in defaults.
Automatic loading of separate student rule files (the stretch item) is not included.

The repeat benchmark received 100/100 samples on both paths: local mean 0.28 ms,
public mean 157.81 ms. No merge to main is authorized.
