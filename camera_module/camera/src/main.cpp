// #include <Arduino.h>
// #include "camera_manager/camera_manager.h"
// #include "network_manager/network_manager.h"
// #include "network_manager/socket.h"
//
// uint8_t mac[6] = { 0x12, 0x34, 0x56, 0xF2, 0x1C, 0x84 };
//
// Camera& c = Camera::getInstance();
// SocketTCP* s;
// std::vector<uint8_t> frame;
// unsigned long fps_timer = 0;
// int frame_counter = 0;
// int frame_size = 0;
//
// static const std::vector<uint8_t> KEY = {
//     0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
//     0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10,
//     0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
//     0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20
// };
//
// void setup() {
//     delay(5000);
//     Serial.begin(115200);
//
//     Logger::info("Start");
//
//     EthernetManager::begin("abc", mac);
//     s = new SocketTCP();
//     s->setAesData(KEY.data(), KEY.size());
//     auto su = s->connect("10.100.102.174", 12345);
//     Logger::info("Connection status: ", su);
//     if (!su) return;
//
//     Logger::info("inniting");
//     Logger::info("success: ", c.init());
//     Logger::info("finish");
//
// }
//
// void loop() {
//     if (c.capture_frame(frame)) {
//         s->send(frame, DataTransferOptions::WITH_SIZE | DataTransferOptions::ENCRYPT_AES);
//         frame_counter++;
//         frame_size += frame.size();
//     }
//
//     unsigned long now = millis();
//     if (now - fps_timer >= 1000 && frame_counter > 0) {
//         Logger::info("FPS: ", frame_counter, "avg size: ", frame_size / frame_counter);  // ×2 for 0.5s to 1s estimate
//         frame_counter = 0;
//         frame_size = 0;
//         fps_timer = now;
//     }
// }
// #include <network_manager/network_manager.h>

// #include "network_manager/socket.h"
//
// SocketUDP* s;
// uint8_t mac[6] = { 0xB6, 0x5E, 0x3A, 0xF2, 0x1C, 0x84 };
//
// void setup() {
//     delay(3000);
//     Logger::info("Starting...");
//     EthernetManager::begin("abc", mac);
//     s = new SocketUDP();
//     s->begin();
//     Logger::info("Started on port: ", s->getPort());
//
// }
//
// void loop() {
//
//     Logger::info("Sent, send status: ", s->send("10.100.102.174", 12345, {0x01, 0x02}));
//     delay(1000);
//     auto a = s->recv();
//     Logger::hexDump(a);
//     delay(1000);
// }
#include "camera/camera.h"

Camera* c;
uint8_t mac[6] = { 0x12, 0x34, 0x56, 0xF2, 0x1C, 0x84 };
void setup() {
    delay(3000);
    EthernetManager::begin(CAMERA_NAME, mac);
    c = new Camera(mac);
}
void loop() {
    c->tick();
    delay(1000);
}