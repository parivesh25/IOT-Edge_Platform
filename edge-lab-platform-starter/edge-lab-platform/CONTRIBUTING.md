# Contributing

Other students are welcome to build on this platform.

1. Read `docs/message-format.md`. Every device and rule must follow it.
2. Copy `firmware/esp32_publisher/` as the starting point for a new device.
3. Add your project under its own folder and topic: `lab/<your-project>/...`.
4. Never commit `secrets.h` or any password. Use `secrets.example.h` for templates.
5. Add a short README in your project folder: what it does, hardware used, how to run it.
6. Keep commit messages descriptive ("Add reconnect logic", not "update").
