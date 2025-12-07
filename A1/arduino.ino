// FINAL MQ3 ARDUINO CODE – clean numeric output only

void setup() {
  Serial.begin(9600);      // Must match ESP32 Serial1 baud
  delay(1000);
  Serial.println("MQ3 Arduino Ready");
}

void loop() {
  int rawValue = analogRead(A0);   // 0–1023

  // Human-readable debug:
  Serial.print("MQ3 Value: ");
  Serial.println(rawValue);

  // *** DATA TO ESP32 ***
  // The ESP32 sender will ONLY look at this pure number line.
  Serial.println(rawValue);

  delay(500);
}
