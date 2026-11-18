"""Generate sketches from the tracked examples, never from secrets.h."""
from pathlib import Path
import re

FIRMWARE = Path(__file__).resolve().parents[1] / "firmware"


def sketch(project):
    name, device, sensor = project["name"], project["device"], project["sensor"]
    if project["board"] == "esp32":
        source = (FIRMWARE / "esp32_publisher/esp32_publisher.ino").read_text()
        source = re.sub(r'const char\* DEVICE_ID\s*=.*', f'const char* DEVICE_ID = "{device}";', source)
        source = re.sub(r'const char\* PROJECT\s*=.*', f'const char* PROJECT = "{name}";\nconst char* SENSOR_ID = "{sensor}";', source)
        expression = {"pot": "analogRead(POT_PIN)", "touch": "touchRead(TOUCH_PIN)",
                      "chip_temp": "temperatureRead()", "wifi_rssi": "WiFi.RSSI()"}.get(sensor, "analogRead(POT_PIN)")
        start = source.index('  publishValue("pot"')
        end = source.index("  delay(1000);", start)
        return source[:start] + f"  // Custom sensor names use the potentiometer input; adjust this read if needed.\n  publishValue(SENSOR_ID, {expression});\n\n" + source[end:]
    source = (FIRMWARE / "uno_serial/uno_serial.ino").read_text()
    constants = f'const char* PROJECT = "{name}";\nconst char* DEVICE_ID = "{device}";\nconst char* SENSOR_ID = "{sensor}";\n\n'
    source = source.replace("void setup()", constants + "void setup()", 1)
    start = source.index("  Serial.print(")
    end = source.index("  Serial.print(value);", start)
    # The USB-only project field is consumed by the gateway, not sent as a reading field.
    output = '''  Serial.print("{\\"project\\":\\"");
  Serial.print(PROJECT);
  Serial.print("\\",\\"device\\":\\"");
  Serial.print(DEVICE_ID);
  Serial.print("\\",\\"sensor\\":\\"");
  Serial.print(SENSOR_ID);
  Serial.print("\\",\\"value\\":");
'''
    return source[:start] + output + source[end:]
