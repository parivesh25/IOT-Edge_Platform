"""Serial-to-MQTT gateway for boards without WiFi (e.g. Arduino Uno).

Usage:  python gateway/serial_gateway.py COM3
        python gateway/serial_gateway.py /dev/ttyACM0
Close the Arduino Serial Monitor first: only one program can own the port.
"""
import json
import sys
import time
import argparse
from pathlib import Path

import paho.mqtt.client as mqtt
import serial

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import MessageProblem, parse_reading, valid_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="For example COM3; close Serial Monitor first")
    parser.add_argument("--project", default="demo")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.mqtt_port)
    client.loop_start()
    try:
        with serial.Serial(args.port, 9600, timeout=2) as ser:
            while True:
                # A bounded read prevents a broken serial source growing memory forever.
                line = ser.readline(4097)
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if not isinstance(data, dict):
                        continue
                    project = data.pop("project", args.project)
                    if not valid_name(project):
                        continue
                    topic = f"lab/{project}/{data.get('device', '')}/{data.get('sensor', '')}"
                    _, clean = parse_reading(topic, json.dumps(data))
                except (ValueError, UnicodeError, MessageProblem):
                    continue
                clean["ts"] = time.time()
                client.publish(topic, json.dumps(clean))
                print("Published a valid serial reading.")
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
