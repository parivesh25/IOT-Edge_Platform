# Phase 1 readiness audit - 16 November 2026

Phase 1 only. Do not begin the dashboard build until the student says `continue`.

## Git and worktree

- Verified origin is `https://github.com/parivesh25/IOT-Edge_Platform`.
- Fetched origin. Main and origin/main both pointed to `a719e3e`; neither was ahead.
- The main clone has no tracked edits, but is **not completely clean**: its existing
  `.codex/environments/environment.toml` is untracked. It was preserved unchanged.
- Created an isolated Codex worktree named `iot-dashboard`, then created branch
  `codex/dashboard` there. Main was not changed or merged.
- No local files or credentials were copied into the worktree. Only tracked
  `secrets.example.h` exists there; no `secrets.h` was created.

## Files changed in Phase 1

- Root `.gitignore`: excludes device secrets, local environment files, Python
  environments/caches, databases, local data, benchmark history and scratch files.
  Keeps `.env.example`, `secrets.example.h` and the shared Codex environment visible.
- `docker-compose.yml`: removes the fixed container name and makes the MQTT host
  port configurable with `${MQTT_PORT:-1883}:1883`. Only Mosquitto exists so far.
- Root `tools/workspace.ps1`: Windows setup/check/start/stop/test commands. Resolves
  the nested application directory and uses the root `.venv`. A short hash of the
  checkout path gives each checkout its own stable Compose project name.
- Root `.codex/environments/environment.toml`: uses the version-1 format observed
  in this installed app, with Windows setup/cleanup and Start/Stop/Run tests actions.
  The helper replaces commands that incorrectly assumed the app was at the Git root.
- This report: records evidence, commands, limitations and the next-phase blockers.

The configuration format was inspected before creating the worktree version.
OpenAI documents storing generated local environment configuration under `.codex`
and sharing it in Git: https://learn.chatgpt.com/docs/environments/local-environment
The action commands were executed directly in PowerShell; their display in the
app toolbar was not checked. Open dashboard is intentionally deferred to Phase 2.

## Checks run and observed

- `git status`, remotes, branches, worktree list, fetch and main/origin comparison.
- `git ls-files` and a redacted pattern scan of all 5 reachable commits / 17 unique
  file blobs. No sensitive filenames or credential-like literals were flagged;
  hits were documentation/code references and example placeholders. Values were
  never printed. This heuristic audit is not a guarantee against every secret format.
- `git check-ignore --no-index`: private paths are excluded; example files and the
  shared environment definition remain eligible for Git.
- PowerShell syntax parsing and `git diff --check`: passed.
- Docker Desktop engine responded; no Compose projects or containers were running
  before the test.
- `docker compose config` and `config --quiet`: passed against the real file.
  Default port resolved to 1883; an override resolved to 18884.
- Start action (`up -d --build`): downloaded `eclipse-mosquitto:2` and started the broker.
- `docker compose ps` and logs: broker running and listening on 1883.
- Host TCP connection to `localhost:1883`: passed.
- MQTT publish/subscribe inside the broker container delivered `phase1-ok` on
  `readiness/phase1`. This proves broker routing, not the unfinished edge service.
- Stop action (`down --remove-orphans`): passed; `ps --all` was empty afterwards.
  No host files or data volumes were deleted. The downloaded image remains cached.
- Run tests action correctly reports the missing `.venv`; no unit tests were run.

## Readiness blockers and README audit

1. The application is under `edge-lab-platform-starter/edge-lab-platform`, not the
   Git root. The original setup/actions therefore cannot find requirements/Compose
   when launched at the root. The new helper uses explicit paths.
2. No `.venv/Scripts/python.exe` was found anywhere in the original checkout or
   new worktree. No additional Python environment was created. Setup reuses `.venv`
   if present and creates it only in a fresh checkout, but its Python/pip steps
   were not executed under the instruction to use the existing environment.
3. There is no `tests/` directory or `tools/sim_device.py` yet. The test action
   points to `python -m unittest discover -s tests` through the root venv, and
   reports missing prerequisites instead of claiming success with zero tests.
4. `edge_service/edge_service.py` ends at a bare `return` in `breached()`. Known
   sensors return None; there is no MQTT client/callback/loop or summary processing.
   The per-sensor RULES table exists for pot, touch, chip_temp, wifi_rssi and
   simulated temperature, but the service is not functional.
5. The ESP32 sketch publishes pot, touch, chip_temp and wifi_rssi. Threshold rules
   belong to the Python edge service. Firmware compilation, pins, sensor readings,
   real WiFi, the hotspot and board flashing were not tested.
6. Compose currently starts only the broker: no edge/dashboard containers and no
   healthchecks. These remain Phase 2 work. The existing broker restart policy stays.
7. The README describes a future dashboard (Grafana), storage, benchmarking and
   time-to-first-data. None is implemented; all roadmap boxes remain unticked.
8. `docs/message-format.md` currently documents reserved topics without the sensor
   suffix (`lab/alerts/<device>` and `lab/summary/<device>`). Phase 2 must update that
   document when implementing per-sensor alert/summary topics. No contract changed here.
9. Anonymous MQTT access is enabled for development. There is no authentication or
   TLS. The broker publishes its host port on all interfaces; use a trusted lab network.

## Commands from the worktree Git root

```powershell
# Validate or start the current platform (broker only in Phase 1).
& .\tools\workspace.ps1 -Action Check
& .\tools\workspace.ps1 -Action Start

# Stop only this checkout's Compose project; preserve volumes and host files.
& .\tools\workspace.ps1 -Action Stop

# Once the existing root .venv and Phase 2 tests are available:
& .\tools\workspace.ps1 -Action Test
```

For a second concurrent checkout, set its port before Start:

```powershell
$env:MQTT_PORT = '18884'
& .\tools\workspace.ps1 -Action Start
```

The default remains 1883 for the ESP32. Different Compose project names prevent
container/network collisions; different host ports are still required concurrently.
Use the helper consistently for Start and Stop. Running bare Compose in the nested
app folder would use a different project name.

For a truly fresh worktree, the configured Setup action runs:

```powershell
& .\tools\workspace.ps1 -Action Setup
```

This creates a root `.venv` only when missing, installs the nested requirements,
and validates Compose. It copies no local files. Before testing Python here,
resolve the missing existing `.venv` location with the student.

## Student-only steps for the later hardware demo

- Join the laptop and ESP32 to the 2.4 GHz phone hotspot; do not automate a campus
  captive portal. Hotspot device isolation may still block board-to-laptop traffic.
- In the checkout used for flashing, copy `secrets.example.h` to `secrets.h` yourself.
  Enter WiFi settings and the laptop's LAN broker address locally. Never commit it.
- Allow inbound TCP 1883 through Windows Firewall for the intended trusted network.
- Flash the ESP32/Uno yourself and confirm real sensor readings. No hardware
  completion box should be ticked until that verification.

The missing venv and incomplete service are reported, not silently repaired in
Phase 1. No system/global Git/Docker settings were changed. Phase 2 remains paused.