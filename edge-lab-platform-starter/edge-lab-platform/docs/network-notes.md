# Connecting boards to the lab

Use a 2.4 GHz phone hotspot for the laptop and ESP32. Campus WiFi commonly needs
a browser login (a captive portal), which the ESP32 sketch cannot complete. This
project does not automate that login. Client isolation on either campus WiFi or a
hotspot can still prevent a board from reaching the laptop.

From the Git root, run `.\.venv\Scripts\python.exe tools\show_ip.py` to see the
laptop's selected LAN IPv4 address. VPNs/multiple adapters can select another
route: check this against Windows network details. The Docker container address
and `localhost` are not the laptop address a WiFi board should use.

After you create `firmware/esp32_publisher/secrets.h` beside the example in the
nested application folder, `tools/show_ip.py --write` can update only BROKER_IP.
It will not create the file or change WIFI_SSID/WIFI_PASS. Never share the file.

Allow inbound TCP port 1883 in Windows Firewall for the intended trusted network.
This is a manual step; the application does not change firewall settings. Keep
the host MQTT port at 1883 for the supplied ESP32 sketch. A second worktree may
use another host port for software testing, but boards must be configured to match.

If no data arrives, check hotspot client isolation, the laptop address and the
firewall. Other options are asking IT to register the board's MAC address or
adding support for the wired Ethernet board later. Ethernet is not implemented.

The dashboard can see broker connections and messages only. It cannot diagnose
physical wiring, credentials entered on a board, or the board's WiFi connection.
