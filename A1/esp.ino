#include <WiFi.h>
#include <esp_now.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEAdvertising.h>
#include "esp_wifi.h"

// ==============================
//  STRUCT FOR SENDING DATA
// ==============================
typedef struct struct_message {
  char nodeId[8];
  float value;
} struct_message;

struct_message dataToSend;

// ==============================
//  RECEIVER MAC ADDRESS
// ==============================
uint8_t receiverAddress[] = {0xFC, 0x01, 0x2C, 0xCC, 0x7C, 0x24};

// ==============================
//  SEND CALLBACK
// ==============================
void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.print("Send Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
}

// ==============================
//  STRICT NUMERIC VALIDATOR
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

// BLE Advertising object
BLEAdvertising *pAdvertising;

// ==============================
//  SETUP
// ==============================
void setup() {
  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, 17, 18);

  delay(300);
  Serial.println("MQ3 Sender Booted");

  // -------- ESP-NOW SETUP --------
  WiFi.mode(WIFI_STA);

  // CRITICAL FIX for BLE+ESP-NOW coexistence
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

  strncpy(dataToSend.nodeId, "MQ3", sizeof(dataToSend.nodeId));

  // -------- BLE BEACON SETUP --------
  BLEDevice::init("MQ3_BEACON");
  
  pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->setScanResponse(false);   // IMPORTANT FOR S3
  pAdvertising->setMinInterval(160);
  pAdvertising->setMaxInterval(240);

  BLEAdvertisementData adv;
  adv.setName("MQ3_BEACON");  // Receiver will match this
  adv.setFlags(0x04);

  // NO manufacturer data — avoids API issues

  pAdvertising->setAdvertisementData(adv);
  pAdvertising->start();

  Serial.println("BLE Beacon Active (MQ3_BEACON)");
}

// ==============================
//  MAIN LOOP
// ==============================
void loop() {
  while (Serial1.available()) {
    char c = Serial1.read();

    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0 && isNumeric(serialBuffer)) {

        float value = serialBuffer.toFloat();
        if (value > 1.0) {
          dataToSend.value = value;

          Serial.print("MQ3 TX: ");
          Serial.println(value);

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
