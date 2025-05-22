#include <ETH.h>
#include <WiFi.h> // Required for event handling
#include "../lib/logger.h" // Your custom logger

// SPI pins for Waveshare ESP32-S3-ETH
#define ETH_MISO  12
#define ETH_MOSI  11
#define ETH_SCLK  13
#define ETH_CS    14
#define ETH_INT   10
#define ETH_RST   9

#define SPI3_HOST 3  // Needed for ESP32-S3

bool ethConnected = false;

void WiFiEvent(WiFiEvent_t event) {
  switch (event) {
    case ARDUINO_EVENT_ETH_START:
      Logger::info("ETH started");
      ETH.setHostname("esp32-eth");
      break;
    case ARDUINO_EVENT_ETH_CONNECTED:
      Logger::info("ETH connected");
      break;
    case ARDUINO_EVENT_ETH_GOT_IP:
      Logger::info(std::string("[ETH] IP Address: ") + ETH.localIP().toString().c_str());
      ethConnected = true;
      break;
    case ARDUINO_EVENT_ETH_DISCONNECTED:
      Logger::info("ETH disconnected");
      ethConnected = false;
      break;
    case ARDUINO_EVENT_ETH_STOP:
      Logger::info("ETH stopped");
      ethConnected = false;
      break;
    default:
      break;
  }
}

void initEthernet() {
  Logger::info("Initializing Ethernet...");
  WiFi.onEvent(WiFiEvent);
  if (!ETH.begin(ETH_CS, ETH_INT, ETH_RST, SPI3_HOST, ETH_MISO, ETH_MOSI, ETH_SCLK)) {
    Logger::info("ETH.begin() failed");
    while (true);
  }

  while (!ethConnected) {
    delay(100);
    Logger::info("Waiting for Ethernet connection...");
  }
}

void setup() {
  delay(4000);  // <-- Your requested delay
  Logger::begin();
  Logger::info("Setup started");
  initEthernet();
}

void loop() {
  Logger::info("Looping...");
  delay(1000);
}
