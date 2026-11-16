"""Exercise a running stack with two simulators and an actual MQTT benchmark."""
import argparse
import json
import http.client
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--mqtt-port", default="1883")
    parser.add_argument("--cloud-host", default="test.mosquitto.org")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    def api(path, data=None):
        request = urllib.request.Request(args.url + path, data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    def wait_for(test, seconds=30):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                result = test()
            except (OSError, http.client.HTTPException):
                result = None  # A newly started web container may not be ready yet.
            if result:
                return result
            time.sleep(1)
        raise AssertionError("Timed out waiting for the expected dashboard result.")

    wait_for(lambda: api("/api/overview")["broker_connected"])
    suffix = uuid.uuid4().hex[:6]
    first, second = "smoke-" + suffix, "second-" + suffix
    api("/api/projects", {"project": first, "device": "sim-" + suffix, "sensor": "temperature", "board": "esp32"})
    for project, device in ((first, "sim-" + suffix), (second, "second-" + suffix)):
        subprocess.run([sys.executable, str(root / "tools/sim_device.py"), "--project", project, "--device", device,
                        "--count", "20", "--interval", "0.05", "--port", args.mqtt_port, "--malformed"], check=True)
    detail = wait_for(lambda: (result if result["project"]["first_data_seconds"] is not None and result["events"] else None)
                      if (result := api("/api/projects/" + first)) else None)
    assert detail["problems"] and any("finite number" in p["problem"] for p in detail["problems"])
    assert any(rows[-1]["simulated"] for rows in detail["series"].values())
    assert {first, second}.issubset({p["name"] for p in api("/api/overview")["projects"]})
    assert any(event["kind"] == "summary" for event in detail["events"])
    print("PASS: two projects, simulated readings, Problems, first-data detector and edge summaries.")
    run_id = api("/api/benchmarks", {"cloud_host": args.cloud_host})["id"]
    def completed():
        return next((r for r in api("/api/benchmarks")["runs"] if r["id"] == run_id and r["status"] != "running"), None)
    run = wait_for(completed, seconds=240)
    assert run["status"] == "complete", run["status"]
    assert run["result"]["local"]["samples"] > 0
    print("PASS: actual local benchmark:", json.dumps(run["result"]["local"]))
    print("Cloud stand-in result:", json.dumps(run["result"]["cloud"]))
    print("Inspect project:", args.url + "/projects/" + first)


if __name__ == "__main__":
    main()
