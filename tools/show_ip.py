"""Print the IPv4 address used by this laptop's current network route.

--write changes only an existing BROKER_IP definition. WiFi fields are never read
into output, and this helper never creates or copies a credentials file.
"""
import argparse
import ipaddress
from pathlib import Path
import re
import socket

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "edge-lab-platform-starter/edge-lab-platform/firmware/esp32_publisher/secrets.h"


def lan_ip():
    # UDP connect chooses a route; no packet is sent to this address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 80))
            address = sock.getsockname()[0]
        if not ipaddress.ip_address(address).is_loopback:
            return address
    except OSError:
        pass
    raise RuntimeError("No LAN IPv4 route found. Connect the laptop to your hotspot first.")


def replace_broker_ip(content, address):
    """Work on bytes so every other byte, including WiFi lines, stays identical."""
    ipaddress.IPv4Address(address)
    pattern = rb'(?m)^(\s*#define[ \t]+BROKER_IP[ \t]+)"[^"\r\n]*"'
    if len(re.findall(pattern, content)) != 1:
        raise ValueError("Expected exactly one quoted BROKER_IP definition; nothing changed.")
    return re.sub(pattern, lambda m: m.group(1) + b'"' + address.encode("ascii") + b'"', content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        address = lan_ip()
        if args.write:
            if not SECRETS.is_file():
                raise ValueError("secrets.h does not exist. Create it yourself from secrets.example.h.")
            original = SECRETS.read_bytes()
            updated = replace_broker_ip(original, address)
            if updated != original:
                SECRETS.write_bytes(updated)
        print(address)
    except (OSError, ValueError, RuntimeError) as error:
        # Errors never include the contents of the credentials file.
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
