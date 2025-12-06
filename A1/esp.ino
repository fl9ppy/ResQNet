#include <WiFi.h>
#include <esp_now.h>

// Message structure
typedef struct struct_message {
  char nodeId[8];
  float value;
} struct_message;

struct_message dataToSend;

// Replace with receiver MAC
uint8_t receiverAddress[] = {0xFC, 0x01, 0x2C, 0xCC, 0x7C, 0x24};

// NEW SEND CALLBACK FORMAT FOR ESP32-S3 (IDF 5.x)
void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.print("Send Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");

  // Print destination MAC (correct field name: des_addr)
  char macStr[18];
  snprintf(macStr, sizeof(macStr),
           "%02X:%02X:%02X:%02X:%02X:%02X",
           info->des_addr[0], info->des_addr[1], info->des_addr[2],
           info->des_addr[3], info->des_addr[4], info->des_addr[5]);

  Serial.print("Sent to: ");
  Serial.println(macStr);
}

String serialBuffer = "";

void setup() {
  Serial.begin(115200);

  // For Serial2: GPIO16 RX, GPIO17 TX (you can change if needed)
  Serial2.begin(9600, SERIAL_8N1, 16, 17);

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register new-style callback
  esp_now_register_send_cb(OnDataSent);

  // Add peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, receiverAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  strncpy(dataToSend.nodeId, "MQ3", sizeof(dataToSend.nodeId));
}

void loop() {
  // Handle incoming serial from Arduino
  while (Serial2.available()) {
    char c = Serial2.read();

    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        float value = serialBuffer.toFloat();
        dataToSend.value = value;

        esp_now_send(receiverAddress, (uint8_t *)&dataToSend, sizeof(dataToSend));

        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
    }
  }
}
