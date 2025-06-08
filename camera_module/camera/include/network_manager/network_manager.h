#include <string>
#include <SPI.h>
#include <Ethernet.h>
#include "../logger/logger.h"
#include "utility/w5100.h"

#undef SPI_ETHERNET_SETTINGS
#define SPI_ETHERNET_SETTINGS SPISettings(14000000, MSBFIRST, SPI_MODE0)

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


public:
    static EthernetData ethernetData;

    static std::string mac_bytes_to_string(const byte* mac) {
        char buf[18];
        snprintf(buf, sizeof(buf),
                 "%02X:%02X:%02X:%02X:%02X:%02X",
                 mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
        return std::string{buf};
    }

    static bool begin(const std::string& hostName, byte mac[]) {
        Logger::debug("Initializing SPI...");
        SPI.begin(PIN__ETH_SPI_SCLK, PIN__ETH_SPI_MISO, PIN__ETH_SPI_MOSI, PIN__ETH_SPI_CS);


        EthernetClass::init(PIN__ETH_SPI_CS);
        Logger::debug("Requesting local IP from DHCP server...");

        int dhcpResult = EthernetClass::begin(mac);
        if (dhcpResult == 0) {
            Logger::error("Failed to get IP from DHCP server!");
            return false;
        }
        Logger::debug("Got IP from DHCP server: ", EthernetClass::localIP());
        Logger::debug("Max socket number: ", MAX_SOCK_NUM, ", Allowing large buffers: ",
            #ifdef ETHERNET_LARGE_BUFFERS
                true,
            #else
                false,
            #endif
                ", SPI clock speed: ", SPI_ETHERNET_SETTINGS._clock
            );


        ethernetData.localIP = EthernetClass::localIP().toString().c_str();
        ethernetData.gatewayIP = EthernetClass::gatewayIP().toString().c_str();
        ethernetData.macAddress = mac_bytes_to_string(mac);

        return true;
    }

    static std::string get_broadcast_address() {
        IPAddress ip = EthernetClass::localIP();
        IPAddress subnet = EthernetClass::subnetMask();
        IPAddress broadcast;

        for (int i = 0; i < 4; i++) {
            broadcast[i] = ip[i] | (~subnet[i]);
        }
        return broadcast.toString().c_str();
    }
};
