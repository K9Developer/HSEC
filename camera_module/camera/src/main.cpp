#include "camera/camera.h"
#include "esp_log.h"

Camera* c;
uint8_t mac[6] = { 0x12, 0x34, 0x56, 0xF2, 0x1C, 0x84 };
void setup() {
    pinMode(BOOT_PIN, INPUT_PULLUP);
    EEPROM.begin(sizeof(ServerData) + sizeof(EEPROM_MAGIC));
    delay(3000);
    Logger::info("OMG STARTING HSEC!!!!");
    EthernetManager::begin(CAMERA_NAME, mac);
    c = new Camera(mac);
}
void loop() {
    c->tick();
}