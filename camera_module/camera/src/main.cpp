#include <Arduino.h>
#include "camera_manager/camera_manager.h"
#include "network_manager/network_manager.h"
#include "network_manager/socket.h"

uint8_t mac[6] = { 0xB6, 0x5E, 0x3A, 0xF2, 0x1C, 0x84 };
Camera& c = Camera::getInstance();
SocketTCP* s;
std::vector<uint8_t> frame;
unsigned long fps_timer = 0;
int frame_counter = 0;
int frame_size = 0;

void setup() {
    delay(5000);
    Serial.begin(115200);

    Logger::info("Start");

    EthernetManager::begin("abc", mac);
    s = new SocketTCP();

    auto su = s->connect("10.100.102.174", 12345);
    Logger::info("Connection status: ", su);
    if (!su) return;

    Logger::info("inniting");
    Logger::info("success: ", c.init());
    Logger::info("finish");



}

void loop() {
    // if (c.capture_frame(frame)) {
    //     s->send(frame);
    //     frame_counter++;
    //     frame_size += frame.size();
    // }
    //
    // unsigned long now = millis();
    // if (now - fps_timer >= 1000) {
    //     Logger::info("FPS: ", frame_counter, "avg size: ", frame_size / frame_counter);  // ×2 for 0.5s to 1s estimate
    //     frame_counter = 0;
    //     frame_size = 0;
    //     fps_timer = now;
    // }
    unsigned long t0 = millis();
    if (c.capture_frame(frame)) {
        unsigned long t1 = millis();
        s->send(frame);
        unsigned long t2 = millis();
        Logger::info("capture: ", t1 - t0, " ms, send: ", t2 - t1, " ms", ", sending ", frame.size(), " bytes.");
    }
}
