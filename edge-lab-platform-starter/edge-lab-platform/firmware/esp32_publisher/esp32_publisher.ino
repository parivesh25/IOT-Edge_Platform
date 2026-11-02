// ESP32 publisher: reads an analog pin once per second and publishes
// a JSON message to the MQTT broker (see docs/message-format.md).
#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"

const char* DEVICE_ID = "esp32s3-1";
const char* SENSOR_ID = "analog0";
const char* PROJECT   = "demo";
const int   SENSOR_PIN = 4;          // GPIO4 is on ADC1 (safe to use with WiFi)

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
char topic[80];

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}

void connectMqtt() {
  while (!mqtt.connected()) {
    mqtt.connect(DEVICE_ID);          // client ID must be unique per device
    if (!mqtt.connected()) delay(2000);
  }
}

void setup() {
  Serial.begin(115200);
  snprintf(topic, sizeof(topic), "lab/%s/%s/%s", PROJECT, DEVICE_ID, SENSOR_ID);
  connectWifi();
  mqtt.setServer(BROKER_IP, 1883);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();                        // keep-alive and incoming messages

  int value = analogRead(SENSOR_PIN); // 0-4095 (12-bit ADC, 0-3.3 V)

  char msg[120];
  snprintf(msg, sizeof(msg),
           "{\"device\":\"%s\",\"sensor\":\"%s\",\"value\":%d}",
           DEVICE_ID, SENSOR_ID, value);
  mqtt.publish(topic, msg);
  Serial.println(msg);

  delay(1000);
}
