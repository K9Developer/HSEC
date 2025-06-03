#include <string>
#define ETHERNET_LARGE_BUFFERS
#define MAX_SOCK_NUM 2
#include <SPI.h>
#include <Ethernet.h>
#include "../logger/logger.h"
#undef SPI_ETHERNET_SETTINGS
#define SPI_ETHERNET_SETTINGS SPISettings(8000000, MSBFIRST, SPI_MODE0)

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
        // setSn_TXBUF_SIZE(0, 16);              // 16 KB transmit
        // setSn_RXBUF_SIZE(0,  1);

        ethernetData.localIP = EthernetClass::localIP().toString().c_str();
        ethernetData.gatewayIP = EthernetClass::gatewayIP().toString().c_str();
        ethernetData.macAddress = macBytesToString(mac);
        return true;
    }
};
