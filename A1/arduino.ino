// Assembly 2 - Arduino UNO (MQ-3 sensor)
// Reads MQ-3 on A0 and sends the value over Serial to ESP32

const int MQ3_PIN = A0;
const unsigned long SEND_INTERVAL_MS = 1000;  // 1 second

unsigned long lastSend = 0;

void setup() {
  Serial.begin(9600); // This goes to ESP32 RX
}

void loop() {
  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;

    int raw = analogRead(MQ3_PIN); // 0–1023
    // Optional: convert to voltage for debug:
    // float voltage = raw * (5.0 / 1023.0);

    // Send just the raw value as integer text
    Serial.println(raw);
  }
}
