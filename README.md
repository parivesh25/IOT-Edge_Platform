# EdgeLab - IoT edge computing lab

The application and firmware live in
[`edge-lab-platform-starter/edge-lab-platform`](edge-lab-platform-starter/edge-lab-platform).
Read its [project guide](edge-lab-platform-starter/edge-lab-platform/README.md)
for the architecture, message contract and hardware instructions.

Moving to another Windows PC? See the [migration guide](edge-lab-platform-starter/edge-lab-platform/docs/windows-migration.md).

From this Git root in **PowerShell**:

```powershell
& .\tools\workspace.ps1 -Action Setup
& .\tools\workspace.ps1 -Action Start
& .\tools\workspace.ps1 -Action Test
# Open http://localhost:8080
# When finished:
& .\tools\workspace.ps1 -Action Stop
```

Setup reuses `.venv` here, creating it only when missing. Start uses a separate
Compose project per checkout. A second running checkout also needs different
host ports, for example `$env:MQTT_PORT='18884'; $env:DASHBOARD_PORT='18080'`.

**Development only:** no logins. Anyone on the lab network can view and change
any project. The broker accepts anonymous connections. Use a trusted network.
No credentials belong in Git or in Docker images. You create `secrets.h` and
flash the boards yourself; the dashboard never asks for WiFi credentials.
