#ifndef NETWORKMANAGER_H
#define NETWORKMANAGER_H

struct EthernetData {
    String localIP;
    String gatewayIP;
    String macAddress;
};

enum EthernetState {
    OFFLINE = 0b00000000,
    STARTED = 0b00000001,
    CONNECTED = 0b00000010,
  };

enum EthernetEvent {
    ETH_MODULE_STARTED = 0,
    ETH_MODULE_CONNECTED = 1,
    ETH_GOT_IP = 2,
    ETH_MODULE_DISCONNECTED = 3,
    ETH_MODULE_STOPPED = 4
};

class EthernetManager {
private:
    static int currentState;
    static void (*ethEventListeners[5])();
    static EthernetData ethData;
    static char* hostName;

    static void onEthEvent(WiFiEvent_t event);

public:
    static void setHostName(char* name);
    static bool begin();
    static void addEventListener(EthernetEvent event, void (*callback)());
    static EthernetData getData();
    static int getState();
};

#endif //NETWORKMANAGER_H
