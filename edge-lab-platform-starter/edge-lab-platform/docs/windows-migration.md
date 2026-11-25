# Move EdgeLab to another Windows PC

The current platform lives on the `codex/dashboard` branch of [IOT-Edge_Platform](https://github.com/parivesh25/IOT-Edge_Platform/tree/codex/dashboard). Clone that branch to get the ESP32 and Uno sketches, USB gateway, broker and Compose configuration, edge service, dashboard, tests, and Windows helpers.

Install Git, Python (available as `python` in PowerShell), and Docker Desktop. Open Docker Desktop and wait for its Linux engine to start. Install Arduino IDE with the ESP32 board package and PubSubClient if you need to upload firmware.

```powershell
git clone --branch codex/dashboard https://github.com/parivesh25/IOT-Edge_Platform.git
Set-Location IOT-Edge_Platform
& .\tools\workspace.ps1 -Action Setup
& .\tools\workspace.ps1 -Action Test
& .\tools\workspace.ps1 -Action Start
```

Open [the dashboard](http://localhost:8080). MQTT uses TCP 1883 by default. The first setup rebuilds local Python and Docker dependencies. See [Connect your project](connect-your-project.md) for the wizard and the Uno gateway command. Use the Uno's new COM port and close Serial Monitor before starting the gateway.

## Reconnect the ESP32

In the new checkout, create `firmware/esp32_publisher/secrets.h` beside the sketch by copying the tracked example in that folder. Enter your WiFi settings locally. With the new PC connected to the intended network, run this from the Git root:

```powershell
.\.venv\Scripts\python.exe tools\show_ip.py --write
```

Confirm the result matches the new PC's hotspot adapter IPv4 address. If the ESP32 firmware still targets the previous PC's IP, upload the sketch yourself with the new address. On a trusted lab network, allow inbound TCP 1883 from the local subnet if needed. See [network notes](network-notes.md). Keep the filled header out of Git.

## Transfer dashboard data privately

Docker named volumes contain SQLite readings, project and benchmark history, and saved rule overrides. Each checkout has its own volume names. GitHub contains the code and configuration, while runtime data should travel through a private transfer. Use `docker volume ls` on both PCs to identify the matching `*_dashboard-data` and `*_rules-data` volumes. Do not assume the prefixes will match.

If you have a migration backup containing `readings.db` and `rules.json`, copy
the backup folder into the new checkout's ignored `data` directory. Start the
platform once to create the volumes and build the dashboard image. Before adding
any new data, stop the platform with `& .\tools\workspace.ps1 -Action Stop`.
Replace the three placeholders below with the new checkout's volume names and
dashboard image name (see `docker volume ls` and `docker image ls`). Adjust
`$backupPath` to the folder containing the backup files. This restores over the new
checkout's database, so keep a separate backup if that checkout has data to keep.

```powershell
$backupPath = (Resolve-Path .\data\windows-migration-2026-11-25).Path
$dbVolume = 'NEW_PROJECT_dashboard-data'
$rulesVolume = 'NEW_PROJECT_rules-data'
$dashboardImage = 'NEW_PROJECT-dashboard:latest'
$restore = @'
from pathlib import Path
import json
import shutil
import sqlite3

with sqlite3.connect("file:/backup/readings.db?mode=ro", uri=True) as source:
    if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit("Backup database failed integrity check.")
    with sqlite3.connect("/data/readings.db") as destination:
        source.backup(destination)

rules = Path("/backup/rules.json")
if rules.is_file():
    json.loads(rules.read_text())
    shutil.copyfile(rules, "/rules/rules.json")
'@
$restore | docker run --rm -i --network none --mount "type=bind,source=$backupPath,target=/backup,readonly" --mount "type=volume,source=$dbVolume,target=/data" --mount "type=volume,source=$rulesVolume,target=/rules" $dashboardImage python -
```

Start the platform again and check project history, benchmark history, and a saved
rule. Normal reading retention still applies after startup.

Your Tinkercad circuit lives in your Tinkercad account. Sign into that account on the new PC to reopen it. The separate [Uno showcase sketch](../firmware/uno_showcase/uno_showcase.ino) preserves the TMP36/PIR simulation sketch with its threshold LEDs and human-readable serial output. The standard Uno serial sketch is the gateway-ready template.
