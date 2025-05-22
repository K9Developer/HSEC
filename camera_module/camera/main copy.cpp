#include <Arduino.h>
#include "../lib/logger.h"
// #include "ETH.h"
// #include <WiFi.h>
// #include <esp_camera.h>
#include "../lib/camera_conf.h"
#include "../lib/camera.h"

static bool connectedToEthernet = false;
static Camera* camera;
byte mac[] = { 0x1, 0x2, 0x3, 0x4, 0x5, 0x6 };

// void ethernetEventHandler(arduino_event_id_t eventId) {
//   switch (eventId) {
//     case ARDUINO_EVENT_ETH_CONNECTED:
//       Logger::info("Ethernet module connected");
//       connectedToEthernet = true;
//       break;
//     case ARDUINO_EVENT_ETH_DISCONNECTED:
//       Logger::warn("Ethernet module disconnected");
//       connectedToEthernet = false;
//       break;
//     case ARDUINO_EVENT_ETH_GOT_IP:
//       Logger::info("Ethernet module got IP:");
//       break;
//     case ARDUINO_EVENT_ETH_STOP:
//       Logger::info("Ethernet module stopped");
//       break;
//   }
// }

// void initEthernet() {
//   WiFi.onEvent(ethernetEventHandler);
//   ETH.begin();
//   while (!connectedToEthernet) { delay(100); }
// }

// bool initCamera() {
//   camera_config_t config = get_config();
//   esp_err_t err = esp_camera_init(&config);

//   if (err != ESP_OK) {
//       Serial.printf("Camera init failed with error 0x%x", err);
//       return false;
//   }

//   sensor_t *s = esp_camera_sensor_get();
//   s->set_vflip(s, 1); // Flip since the camera is upside down

//   camera = new Camera(config, s);
//   return true;
// }

// void setup() {
//   Logger::begin();
//   Logger::info("Setup started");

//   initEthernet();
//   Logger::info("Ethernet initialized");

//   bool success = initCamera();
//   if (!success) {
//       Logger::error("Camera initialization failed");
//       return;
//   }
// }

// void loop() {
//   if (!connectedToEthernet) {
//       Logger::warn("Not connected to Ethernet");
//       return;
//   }
//   if (camera == nullptr) {
//       Logger::error("Camera not initialized");
//       return;
//   }

//   Logger::info("Capturing image...");
//   // Serial.println(reinterpret_cast<const char*>(camera->capture_jpg()));
//   delay(1000);
// }

#include <SPI.h>
#include <Ethernet.h>

void initEthernet() {
  if (Ethernet.begin(mac) == 0) {
    Serial.println("Failed to get IP from DHCP");
    while (true); // halt
  }

  Serial.print("IP Address: ");
  Serial.println(Ethernet.localIP());
}

void setup() {
  delay(5000);

    Logger::begin();
    Logger::info("Setup started");
    initEthernet();


}

void loop() {
    Logger::info("Looping...");
  delay(1000);
}