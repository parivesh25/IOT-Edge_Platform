// Arduino Uno: prints one JSON reading per line over USB serial.
// The Python gateway (gateway/serial_gateway.py) forwards it to MQTT.
void setup() {
  Serial.begin(9600);                 // must match the gateway's baud rate
}

void loop() {
  int value = analogRead(A0);         // 0-1023 (10-bit ADC, 0-5 V)

  Serial.print("{\"device\":\"uno1\",\"sensor\":\"analog0\",\"value\":");
  Serial.print(value);
  Serial.println("}");

  delay(1000);
}
