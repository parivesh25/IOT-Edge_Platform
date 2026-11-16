# EdgeLab - Student IoT workspace

A reusable edge computing platform for our lab: connect a sensor, run logic
on an edge device, and see live data, using ready-made templates instead of
setting everything up from scratch. It also measures its own performance
(latency, data sent) so every project gets benchmark numbers.

**Status:** course project; software verification is recorded below. Real-board
and hotspot verification must be done by the student.

## Architecture

    Sensor -> Board -> (WiFi, or USB serial + gateway) -> MQTT broker -> Edge service -> Dashboard

See `docs/architecture.md` and `docs/message-format.md`.

## Supported hardware

| Board | Connection | Folder |
|---|---|---|
| ESP32-S3 (N16R8) | WiFi, direct MQTT | `firmware/esp32_publisher/` |
| Arduino Uno R3 | USB serial via gateway | `firmware/uno_serial/` + `gateway/` |

## Quick start

Run commands from the **Git root**, two folders above this README, in PowerShell:

```powershell
& .\tools\workspace.ps1 -Action Setup
& .\tools\workspace.ps1 -Action Start
# Dashboard: http://localhost:8080
.\.venv\Scripts\python.exe tools\sim_device.py --project demo --device sim-1
& .\tools\workspace.ps1 -Action Test
& .\tools\workspace.ps1 -Action Stop
```

The helper uses the root `.venv` and this folder's requirements and Compose file.
It installs nothing system-wide. Setup needs internet once for packages/images;
the local dashboard has no CDN or internet dependency after installation.
The public-broker benchmark needs internet and can report `unreachable`.

For a second concurrent worktree, set `$env:MQTT_PORT='18884'` and
`$env:DASHBOARD_PORT='18080'` before Start; pass `--port 18884` to the simulator.
The default MQTT port stays 1883 for the ESP32. Each checkout has its own Compose
project name and data volume. Use the same helper for Start and Stop.

If running Compose directly from this application folder, `docker compose up -d
--build` also starts all services, but it uses a different project name from the
helper. Do not mix the two methods for the same running stack.

### Manual board steps (not verified on hardware)

1. **Start the platform** using the root helper above (Docker Desktop required).
2. **Watch messages** with MQTT Explorer: connect to `localhost`, port `1883`.
3. **ESP32:** copy `firmware/esp32_publisher/secrets.example.h` to `secrets.h`,
   fill in your WiFi name, password, and your computer's LAN IP, then upload the sketch
   (board: ESP32S3 Dev Module, PSRAM: OPI, Flash: 16MB).
4. **Uno (optional):** upload `firmware/uno_serial/uno_serial.ino`, close the Serial Monitor, then run
   `.\.venv\Scripts\python.exe gateway\serial_gateway.py COM3` from the Git root.
   The generated wizard sketch carries its project name over USB; the original
   Uno example defaults to `demo`, or use `--project your-project` on the gateway.
5. **Network:** connect the laptop and ESP32 to the 2.4 GHz phone hotspot, allow
   inbound TCP 1883 in Windows Firewall, and use the laptop LAN address as BROKER_IP.
   See [network notes](docs/network-notes.md). Never automate a captive portal.

### What the software does

- Flask serves plain HTML/CSS/JavaScript; it is simpler to explain here than an
  asynchronous API framework. Waitress runs one process with 16 threads and works
  on Windows. Eight server-sent-event slots leave threads for normal requests;
  five-second polling is the fallback. Charts are small SVG plots, with no JS library.
- MQTT readings automatically create project cards. Online means a valid live
  reading arrived within 15 seconds. Rates use a 15-second average.
- SQLite retains up to 100,000 readings or 24 hours, whichever is smaller. Also
  bounded: 10,000 recent messages/events, 500 problems, 100 benchmark runs, and
  1,000 project records. Cleanup runs on ingestion and every minute while idle.
  SQLite reuses freed pages, and the main database has a 512 MiB page limit.
  Docker logs rotate at 5 MB with two files per service. These limits bound this
  application's data; they cannot prevent other programs filling the disk.
- The wizard records elapsed seconds to the first valid live reading. Retained
  old readings and invalid messages do not complete the timer. Reopening the
  same project preserves its original timing measurement.
- Problems explain invalid topics/JSON/fields/numbers/ID mismatches. Repeated
  duplicate-client notices from Mosquitto flag possible DEVICE_ID collisions;
  they cannot identify physical boards or prove WiFi/wiring faults.
- Edge rules use a per-sensor RULES table. Each project/device/sensor has its own
  ten-reading summary window. See [the contract](docs/message-format.md) for
  updated per-sensor alert/summary topics.
- The benchmark uses a unique topic, one `time.perf_counter` clock, one discarded
  warm-up and 100 sequential MQTT QoS-0 round trips per broker. Statistics use
  received samples only; standard deviation is population standard deviation.
  Each sample times out after one second. Lost messages are reported separately.
  The configurable public broker defaults to `test.mosquitto.org` on port 1883.
  Only generated numbers are published. This measures **network path only**,
  not cloud compute, and the shared public broker's results vary.

### Security and demo limits

**There are no logins. Anyone on the lab network can view and change any project.**
Mosquitto allows anonymous connections for development only. Do not expose these
ports to the internet. This is not a production or multi-tenant security design.
The dashboard never receives credentials. Unknown JSON fields and invalid payload
text are omitted from storage and the raw-message viewer to avoid accidental leaks.
Only secrets.example.h is tracked; secrets.h and .env files are ignored and
excluded from Docker builds. Create/fill secrets.h yourself in your flashing checkout.

### Reproducible software checks

```powershell
# Run from the Git root; the smoke test needs the running stack.
& .\tools\workspace.ps1 -Action Test
.\.venv\Scripts\python.exe tools\smoke_test.py
```

The smoke test creates two clearly named simulator projects, publishes malformed
data, checks the Problems API, first-data timer and edge summaries, then runs a
real benchmark. Simulator projects/history remain visible as test evidence.
Hardware, firmware compilation, actual WiFi/hotspot connectivity and firewall
reachability from another device are not verified by these software tests.

## Roadmap

- [ ] ESP32 publishes to the broker
- [ ] Uno joins through the serial gateway
- [x] Edge service: rules and summaries (simulator verified)
- [x] Local storage (SQLite)
- [x] Dashboard (Flask student workspace)
- [x] Latency benchmark: edge vs cloud (network path only)
- [ ] Plug-in system for student rules
- [ ] Time-to-first-data test with a new student

## Reference and differences

Based on the NoteLab reference architecture (arXiv:2103.11396, "Engineering an
IoT-Edge-Cloud Computing System Architecture: Lessons Learnt from An
Undergraduate Lab Course"). Added here: a standard message format, a gateway for
boards without WiFi, edge rules, and built-in benchmarking.

## License

MIT License
