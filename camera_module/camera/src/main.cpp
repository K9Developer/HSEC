#include <Arduino.h>
#include "camera_manager/camera_manager.h"
#include "network_manager/network_manager.h"
#include "network_manager/socket.h"
uint8_t mac[6] = { 0xB6, 0x5E, 0x3A, 0xF2, 0x1C, 0x84 };
Camera& c = Camera::getInstance();
SocketTCP* s;
void setup() {
    delay(5000);
    Serial.begin(115200);

    Logger::info("Start");

    EthernetManager::begin("abc", mac);
    SocketTCP* s = new SocketTCP();

    auto su = s->connect("10.100.102.174", 12345);
    Logger::info("Connection status: ", su);
    if (!su) return;

    Logger::info("inniting");
    Logger::info("success: ", c.init());
    Logger::info("finish");



}

void loop() {
    auto f = c.capture_frame();
    s->send(f);
    Logger::info("captured ", f.size());
}
