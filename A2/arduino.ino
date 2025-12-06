// Assembly 3 - Arduino UNO (TEMP-02 / LM35-style sensor)
// Reads temperature in °C and sends it as text over Serial

const int TEMP_PIN = A0;
const unsigned long SEND_INTERVAL_MS = 1000;  // 1 second

unsigned long lastSend = 0;

void setup() {
  Serial.begin(9600);  // To ESP32 RX
}

void loop() {
  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;

    int raw = analogRead(TEMP_PIN);
    float voltage = raw * (5.0 / 1023.0);  // V
    float tempC = voltage * 100.0;         // 10mV per °C → 100x

    Serial.println(tempC);  // e.g. "24.56"
  }
}
