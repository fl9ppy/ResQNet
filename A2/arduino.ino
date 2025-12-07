const int LM35_PIN = A0;

void setup() {
  Serial.begin(9600);
}

void loop() {
  const int N = 15;
  int readings[N];

  // Take multiple samples
  for (int i = 0; i < N; i++) {
    readings[i] = analogRead(LM35_PIN);
    delay(5);
  }

  // Find min & max
  int minVal = readings[0];
  int maxVal = readings[0];
  long sum = 0;
  for (int i = 0; i < N; i++) {
    if (readings[i] < minVal) minVal = readings[i];
    if (readings[i] > maxVal) maxVal = readings[i];
    sum += readings[i];
  }

  // Drop min & max
  sum -= minVal;
  sum -= maxVal;
  float avg = sum / float(N - 2);

  float voltage = avg * (5.0 / 1023.0);
  float tempC = voltage * 100.0;  // LM35

  // Optional: clamp insane values
  if (tempC < -20 || tempC > 120) {
    // ignore, don't print
  } else {
    Serial.println(tempC, 1);
  }

  delay(200);  // ~5 Hz
}
