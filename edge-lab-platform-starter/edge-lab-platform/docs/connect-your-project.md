# Clone to first data

Allow about 30 minutes, plus first-time image downloads and Arduino package setup.
This is a target, not a measured guarantee for a new student.

1. Clone the repository and open PowerShell at its Git root.
2. Start Docker Desktop. Run `& .\tools\workspace.ps1 -Action Setup`, then
   `& .\tools\workspace.ps1 -Action Start`.
3. Open http://localhost:8080/new. Enter unique project/device names, a sensor,
   and your board type. The first-data timer starts with the checklist.
4. For a software-only test, run `.\.venv\Scripts\python.exe tools\sim_device.py
   --project YOUR-PROJECT --device YOUR-DEVICE`. Substitute the lowercase names
   you entered. The first-data indicator should turn green.
5. For ESP32, follow the wizard to create secrets.h locally, enter your WiFi
   settings yourself, select the laptop LAN address, and flash the generated
   sketch. Use the 2.4 GHz hotspot and allow inbound TCP 1883.
6. For Uno, flash its generated sketch, close Serial Monitor, and run
   `.\.venv\Scripts\python.exe gateway\serial_gateway.py COM3` with the actual port.
7. Open the project page for charts, Problems, exports and the rule editor.
   Rules persist in a Docker volume and reload without a service restart.
8. Open Lab overview for all projects, broker status and first-data measurements.
   Export those measurements for your report.

Optional: `.\.venv\Scripts\python.exe tools\new_project.py greenhouse` creates
a README under projects/greenhouse without overwriting existing files.

The dashboard cannot verify wiring, board WiFi or firewall reachability. See
network-notes.md. All network users can view/change projects in this lab version.
