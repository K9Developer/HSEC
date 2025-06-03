#include <string>
#define ETHERNET_LARGE_BUFFERS
#include <SPI.h>
#include <Ethernet.h>
#include "../logger/logger.h"

// extern "C" {
// #include <wizchip_conf.h>
// }
// static void boostSocketBuf() {
//     uint8_t tx[8] = {16,0,0,0,0,0,0,0};   // 16 KB TX on S0
//     uint8_t rx[8] = { 0,0,0,0,0,0,0,0};   // use RX only for ACKs
//     wizchip_init(tx, rx);
// }

struct EthernetData {
    std::string localIP;
    std::string gatewayIP;
    std::string macAddress;
};

enum EthernetState {
    OFFLINE = 0b00000000,
    STARTED = 0b00000001,
    CONNECTED = 0b00000010,
};


class EthernetManager {
private:

    static std::string macBytesToString(const byte* mac) {
        char buf[18];
        snprintf(buf, sizeof(buf),
                 "%02X:%02X:%02X:%02X:%02X:%02X",
                 mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
        return std::string{buf};
    }

public:
    static EthernetData ethernetData;

    static bool begin(const std::string& hostName, byte mac[]) {
        Logger::debug("Initializing SPI...");
        SPI.begin(PIN__ETH_SPI_SCLK, PIN__ETH_SPI_MISO, PIN__ETH_SPI_MOSI, PIN__ETH_SPI_CS);
        EthernetClass::init(PIN__ETH_SPI_CS);
        // boostSocketBuf();

        Logger::debug("Requesting local IP from DHCP server...");
        int dhcpResult = EthernetClass::begin(mac);
        if (dhcpResult == 0) {
            Logger::error("Failed to get IP from DHCP server!");
            return false;
        }

        ethernetData.localIP = EthernetClass::localIP().toString().c_str();
        ethernetData.gatewayIP = EthernetClass::gatewayIP().toString().c_str();
        ethernetData.macAddress = macBytesToString(mac);
        return true;
    }
};
