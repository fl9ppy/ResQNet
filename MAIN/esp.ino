// Assembly 1 - ESP32 End-Node Receiver
// Receives ESP-NOW packets and forwards them via Serial (USB) to Raspberry Pi

#include <WiFi.h>
#include <esp_now.h>

typedef struct struct_message {
  char nodeId[8];
  float value;
} struct_message;

struct_message incomingData;

void OnDataRecv(const uint8_t *mac, const uint8_t *incomingDataBytes, int len) {
  if (len == sizeof(struct_message)) {
    memcpy(&incomingData, incomingDataBytes, sizeof(incomingData));

    // Ensure nodeId is null-terminated
    incomingData.nodeId[sizeof(incomingData.nodeId) - 1] = '\0';

    Serial.print(incomingData.nodeId);
    Serial.print(":");
    Serial.println(incomingData.value, 2); // two decimal places
  } else {
    Serial.println("Received unknown packet size");
  }
}

void setup() {
  Serial.begin(115200);  // to Raspberry Pi (USB)

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);
}

void loop() {
  // Nothing here; all work done in OnDataRecv callback
}
