// Assembly 2 - ESP32 sender for MQ-3
// Reads a line from Arduino over Serial2, sends via ESP-NOW with nodeId "MQ3"

#include <WiFi.h>
#include <esp_now.h>

typedef struct struct_message {
  char nodeId[8];  // "MQ3"
  float value;     // sensor value
} struct_message;

struct_message dataToSend;

// REPLACE THIS WITH YOUR END-NODE ESP32 MAC
uint8_t receiverAddress[] = {0x24, 0x6F, 0x28, 0xAB, 0xCD, 0xEF};

String serialBuffer = "";

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  // Optional debug:
  // Serial.print("Last Packet Send Status: ");
  // Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void setup() {
  Serial.begin(115200);       // debug (USB)
  Serial2.begin(9600, SERIAL_8N1, 16, 17);  // RX=16, TX=17, to Arduino

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

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
  while (Serial2.available()) {
    char c = (char)Serial2.read();
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        float value = serialBuffer.toFloat();  // raw ADC from Arduino
        dataToSend.value = value;

        esp_err_t result = esp_now_send(receiverAddress, (uint8_t *)&dataToSend, sizeof(dataToSend));
        if (result != ESP_OK) {
          Serial.println("Error sending ESP-NOW packet");
        }

        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
    }
  }
}
