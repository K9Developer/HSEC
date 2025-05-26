#include "network_manager.h"
#include <WiFi.h>
#include <Ethernet.h>
#include "constants.h"
#include "Arduino.h"

int           EthernetManager::currentState = EthernetState::OFFLINE;
void          (*EthernetManager::ethEventListeners[5])() = {nullptr, nullptr, nullptr, nullptr, nullptr};
EthernetData  EthernetManager::ethData = {"", "", ""};
char*         EthernetManager::hostName = nullptr;

void EthernetManager::setHostName(char* name) {
  hostName = name;
}

bool EthernetManager::begin() {
  WiFi.onEvent(onEthEvent);
  bool success = ETH.begin(ETH_PHY_ADDR, 1, PIN__ETH_SPI_CS, PIN__ETH_IRQ, PIN__ETH_RESET, SPI3_HOST, PIN__ETH_SPI_SCLK, PIN__ETH_SPI_MISO, PIN__ETH_SPI_MOSI);
  if (success) currentState |= EthernetState::STARTED;
  return success;
}

void EthernetManager::addEventListener(EthernetEvent event, void (*callback)()) {
  if (event >= 0 && event <= 4)
    ethEventListeners[event] = callback;
}

EthernetData EthernetManager::getData() {
  return ethData;
}

int EthernetManager::getState() {
  return currentState;
}

void EthernetManager::onEthEvent(WiFiEvent_t event) {
  switch (event) {
    case ARDUINO_EVENT_ETH_START:
      ETH.setHostname(hostName == nullptr ? CAMERA_NAME : hostName);
      if (ethEventListeners[ETH_MODULE_STARTED]) ethEventListeners[ETH_MODULE_STARTED]();
      break;

    case ARDUINO_EVENT_ETH_CONNECTED:
      if (ethEventListeners[ETH_MODULE_CONNECTED]) ethEventListeners[ETH_MODULE_CONNECTED]();
      currentState |= EthernetState::CONNECTED;
      break;

    case ARDUINO_EVENT_ETH_GOT_IP:
      if (ethEventListeners[ETH_GOT_IP]) ethEventListeners[ETH_GOT_IP]();
      currentState |= EthernetState::CONNECTED;

      ethData.localIP = ETH.localIP().toString();
      ethData.gatewayIP = ETH.gatewayIP().toString();
      ethData.macAddress = ETH.macAddress().c_str();
      break;

    case ARDUINO_EVENT_ETH_DISCONNECTED:
      if (ethEventListeners[ETH_MODULE_DISCONNECTED]) ethEventListeners[ETH_MODULE_DISCONNECTED]();
      currentState &= ~EthernetState::CONNECTED;
      ethData = {"", "", ""};
      break;

    case ARDUINO_EVENT_ETH_STOP:
      if (ethEventListeners[ETH_MODULE_STOPPED]) ethEventListeners[ETH_MODULE_STOPPED]();
      currentState &= ~EthernetState::STARTED;
      break;

    default:
      break;
  }
}
