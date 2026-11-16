// ESP32 publisher: reads an analog pin once per second and publishes
// a JSON message to the MQTT broker (see docs/message-format.md).
#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"

const char* DEVICE_ID = "esp32s3eth-1";   // new unique ID for this board
const char* PROJECT   = "demo";
const int POT_PIN   = 1;   // GPIO1 = ADC1, header pin 25
const int TOUCH_PIN = 2;   // GPIO2 = touch pad 2, header pin 26

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}

void connectMqtt() {
  while (!mqtt.connected()) {
    mqtt.connect(DEVICE_ID);
    if (!mqtt.connected()) delay(2000);
  }
}

void publishValue(const char* sensor, float value) {
  // The contract allows names up to 48 characters; leave room for all three.
  char t[160], msg[256];
  snprintf(t, sizeof(t), "lab/%s/%s/%s", PROJECT, DEVICE_ID, sensor);
  snprintf(msg, sizeof(msg),
           "{\"device\":\"%s\",\"sensor\":\"%s\",\"value\":%.1f}",
           DEVICE_ID, sensor, value);
  mqtt.publish(t, msg);
  Serial.println(msg);
}

void setup() {
  Serial.begin(115200);
  connectWifi();
  mqtt.setServer(BROKER_IP, 1883);
  mqtt.setBufferSize(512);   // topic + JSON must fit in one MQTT packet
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  publishValue("pot", analogRead(POT_PIN));        // 0-4095
  publishValue("touch", touchRead(TOUCH_PIN));
  publishValue("chip_temp", temperatureRead());    // delete if it won't compile
  publishValue("wifi_rssi", WiFi.RSSI());

  delay(1000);
}
