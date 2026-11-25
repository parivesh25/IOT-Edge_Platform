// Tinkercad TMP36/PIR showcase. Serial output is intended for Serial Monitor.
const int POT_PIN = A0;
const int LDR_PIN = A1;
const int TMP_PIN = A2;
const int PIR_PIN = 3;
const int BUZZER = 6;

const int POT_LED = 10;
const int LDR_LED = 7;
const int TMP_LED = 12;
const int PIR_LED = 4;
const int ALARM_LED = 11;

const int POT_THRESHOLD = 512;
const int LDR_THRESHOLD = 300;
const float TEMP_THRESHOLD = 30.0;
const bool USE_BUZZER = true;

unsigned long lastReport = 0;

void setup() {
  Serial.begin(9600);
  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(POT_LED, OUTPUT);
  pinMode(LDR_LED, OUTPUT);
  pinMode(TMP_LED, OUTPUT);
  pinMode(PIR_LED, OUTPUT);
  pinMode(ALARM_LED, OUTPUT);
}

void loop() {
  int potValue = analogRead(POT_PIN);
  int ldrValue = analogRead(LDR_PIN);
  float voltage = analogRead(TMP_PIN) * 5.0 / 1024.0;
  float tempC = (voltage - 0.5) * 100.0;
  bool motion = digitalRead(PIR_PIN) == HIGH;

  bool potHigh = potValue > POT_THRESHOLD;
  bool isDark = ldrValue < LDR_THRESHOLD;
  bool isHot = tempC > TEMP_THRESHOLD;
  unsigned long now = millis();
  bool blinkOn = (now / 250UL) % 2 == 0;

  digitalWrite(POT_LED, potHigh && blinkOn ? HIGH : LOW);
  digitalWrite(LDR_LED, isDark && blinkOn ? HIGH : LOW);
  digitalWrite(TMP_LED, isHot && blinkOn ? HIGH : LOW);
  digitalWrite(PIR_LED, motion && blinkOn ? HIGH : LOW);
  digitalWrite(ALARM_LED, potHigh || isDark || isHot || motion ? HIGH : LOW);

  if (USE_BUZZER && motion) {
    tone(BUZZER, 1000);
  } else {
    noTone(BUZZER);
  }

  if (now - lastReport >= 200UL) {
    lastReport = now;
    Serial.print("Pot: "); Serial.print(potValue);
    Serial.print(" | LDR: "); Serial.print(ldrValue);
    Serial.print(" | Temp: "); Serial.print(tempC, 1);
    Serial.print(" C | Motion: ");
    Serial.println(motion ? "YES" : "no");
  }
}
