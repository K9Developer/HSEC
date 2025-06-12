//
// Created by ilaik on 6/10/2025.
//

#ifndef EEPROM_MANAGER_H
#define EEPROM_MANAGER_H

#include <constants.h>
#include <EEPROM.h>



struct ServerData {
    IPAddress addr;
    uint16_t port = 0;
    uint8_t shared_secret[32]{};
    uint8_t aes_iv[16]{};
};


void write_data_to_eeprom(const ServerData& data) {
    int curr_ptr = 0;

    EEPROM.put(curr_ptr, EEPROM_MAGIC);
    curr_ptr += sizeof(EEPROM_MAGIC);

    EEPROM.put(curr_ptr, data);

    EEPROM.commit();
}

bool has_eeprom_data() {

    uint32_t magic;
    EEPROM.get(0, magic);

    return magic == EEPROM_MAGIC;
}

ServerData read_data_from_eeprom() {

    ServerData data;
    EEPROM.get(sizeof(EEPROM_MAGIC), data);

    return data;
}

void clear_eeprom() {

    for (int i = 0; i < sizeof(ServerData) + sizeof(EEPROM_MAGIC); ++i) {
        EEPROM.write(i, 0xFF); // or 0x00 depending on your convention
    }

    EEPROM.commit();
}

#endif //EEPROM_MANAGER_H
