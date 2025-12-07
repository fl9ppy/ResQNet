#include <WiFi.h>
#include <esp_now.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEAdvertising.h>
#include "esp_wifi.h"

// ==============================
// ESP-NOW DATA STRUCT
// ==============================
typedef struct struct_message {
  char nodeId[8];
  float value;
} struct_message;

struct_message dataToSend;

// ==============================
// RECEIVER MAC ADDRESS (same as MQ3)
// ==============================
uint8_t receiverAddress[] = {0xFC, 0x01, 0x2C, 0xCC, 0x7C, 0x24};

// ==============================
void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.print("Send Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
}

// ==============================
bool isNumeric(const String &s) {
  if (s.length() == 0) return false;
  int dots = 0;
  int start = (s[0] == '-') ? 1 : 0;
  for (int i = start; i < s.length(); i++) {
    char c = s[i];
    if (isdigit(c)) continue;
    if (c == '.' && dots == 0) { dots++; continue; }
    return false;
  }
  return true;
}

String serialBuffer = "";
BLEAdvertising *pAdvertising;

// ==============================
void setup() {
  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, 17, 18);

  delay(300);
  Serial.println("TEMP Sender Booted");

  // ------ ESP-NOW ------
  WiFi.mode(WIFI_STA);
  esp_wifi_set_ps(WIFI_PS_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW Init Failed!");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, receiverAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  strncpy(dataToSend.nodeId, "TEMP", sizeof(dataToSend.nodeId));

  // ------ BLE BEACON ------
  BLEDevice::init("TEMP_BEACON");

  pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinInterval(160);
  pAdvertising->setMaxInterval(240);

  BLEAdvertisementData adv;
  adv.setFlags(0x04);
  adv.setName("TEMP_BEACON");

  pAdvertising->setAdvertisementData(adv);
  pAdvertising->start();

  Serial.println("BLE Beacon Active: TEMP_BEACON");
}

// ==============================
void loop() {
  while (Serial1.available()) {
    char c = Serial1.read();

    if (c == '\n' || c == '\r') {

      if (serialBuffer.length() > 0 && isNumeric(serialBuffer)) {
        float tempC = serialBuffer.toFloat();

        if (tempC > -30 && tempC < 150) {  // valid range
          dataToSend.value = tempC;

          Serial.print("TEMP TX: ");
          Serial.println(tempC);

          esp_now_send(receiverAddress, (uint8_t*)&dataToSend, sizeof(dataToSend));
        }
      }

      serialBuffer = "";
    }
    else {
      serialBuffer += c;
    }
  }
}
