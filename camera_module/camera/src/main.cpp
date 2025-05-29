#include "network_manager/socket.h"
#include "network_manager/network_manager.h"
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
SocketTCP* s ;

std::vector<char> str_to_cvec(std::string s) {
    std::vector<char> arr;
    arr.reserve(s.size());

    for(int i = s.size()-1; i >= 0; i--) {
        arr.push_back(s[i]);
    }
    return arr;
}

void setup() {
    delay(5000);

    EthernetManager::begin("cocain", mac);

    s = new SocketTCP();
    const std::string ip = "10.100.102.175";
    bool success = s->connect(ip, 12345);
    Logger::warning(EthernetManager::ethernetData.localIP);
    Logger::warning(success);
}
void loop() {

    Logger::hexDump(s->recv());
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