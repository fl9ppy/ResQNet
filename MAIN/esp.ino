#include <WiFi.h>
#include <esp_now.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

typedef struct struct_message {
  char nodeId[8];
  float value;
} struct_message;

struct_message incomingData;

// Distance storage
volatile float distMQ3 = -1;
volatile float distTEMP = -1;

const int BEACON_TX_POWER = -59;
const float N_ENV = 2.0;

float rssiToDist(int rssi) {
  float exp = (BEACON_TX_POWER - rssi) / (10.0f * N_ENV);
  return pow(10.0f, exp);
}

void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != sizeof(struct_message)) return;

  memcpy(&incomingData, data, sizeof(incomingData));
  incomingData.nodeId[7] = '\0';

  Serial.print(incomingData.nodeId);
  Serial.print(": ");
  Serial.println(incomingData.value, 2);

  if (strcmp(incomingData.nodeId, "MQ3") == 0 && distMQ3 > 0) {
    Serial.print("DIST_MQ3: ");
    Serial.println(distMQ3, 2);
  }
  if (strcmp(incomingData.nodeId, "TEMP") == 0 && distTEMP > 0) {
    Serial.print("DIST_TEMP: ");
    Serial.println(distTEMP, 2);
  }
}

class BeaconScanner : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice dev) {
    String name = String(dev.getName().c_str());
    int rssi = dev.getRSSI();

    if (name == "MQ3_BEACON") {
      float d = rssiToDist(rssi);
      distMQ3 = (distMQ3 < 0) ? d : (distMQ3 * 0.7 + d * 0.3);
    }

    if (name == "TEMP_BEACON") {
      float d = rssiToDist(rssi);
      distTEMP = (distTEMP < 0) ? d : (distTEMP * 0.7 + d * 0.3);
    }
  }
};

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW Init Failed");
    return;
  }
  esp_now_register_recv_cb(OnDataRecv);

  BLEDevice::init("");
  BLEScan *scan = BLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new BeaconScanner(), false);
  scan->setActiveScan(true);
  scan->start(0, nullptr, false);
}

void loop() {
}
