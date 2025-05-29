#include "network_manager/socket.h"
#include "network_manager/network_manager.h"
#include "logger/logger.h"
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
SocketTCP* s ;


static std::vector<char> k = {0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03, 0x01, 0x02};
static std::vector<unsigned char> c = {0x57, 0x02, 0xa3, 0xb7, 0x03, 0x30, 0x30, 0x6e, 0x9c, 0x7e, 0x28, 0x6d, 0xfe, 0x5c, 0x30, 0xf0, 0x56, 0xad, 0x56, 0x70, 0x68, 0x4a, 0x3e, 0x14, 0x7f, 0x1d, 0xf2, 0x5e, 0x63, 0x3b, 0xfc, 0x67};


// std::vector<char> str_to_cvec(std::string s) {
//     std::vector<char> arr;
//     arr.reserve(s.size());

//     for(int i = s.size()-1; i >= 0; i--) {
//         arr.push_back(s[i]);
//     }
//     return arr;
// }

void setup() {
    Serial.begin(115200);

    EthernetManager::begin("cocain", mac);

    s = new SocketTCP();
    s->setAesData(k.data(), 32);

    // const std::string ip = "10.68.121.237";
    // bool success = s->connect(ip, 12345);
    //Logger::warning(EthernetManager::ethernetData.localIP);
    // Logger::warning(success);
}


void loop() {
    Logger::hexDump(s->_decrypt_aes(c));
    delay(1000);
    // auto r = s->recv(20, 0);
    // if (r.size() != 0) {
    //
    //     Serial.print("RECIEVE: ");
    //     for (auto ch: r) {
    //         Serial.print(ch);
    //     }
    //     Serial.println();
    //     // Serial.print("Sending: ");
    //     //
    //     //
    //     // while (!Serial.available()) {delay(100);}
    //     //
    //     // std::vector<char> a;
    //     // while (Serial.available()) {
    //     //     auto s = Serial.read();
    //     //     Serial.print((char)s);
    //     //     a.push_back((char)s);
    //     // }
    //     // Serial.println();
    //     //
    //     //
    //     // s->send(a, 0);
    // }
}