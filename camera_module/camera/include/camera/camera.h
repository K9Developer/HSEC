#ifndef CAMERA_H
#define CAMERA_H

#include "network_manager/socket.h"
#include "network_manager/network_manager.h"
#include "logger/logger.h"
#include "task.h"
#include <EEPROM.h>
#include <vector>
#include <string>

enum CameraState
{
    IDLE = 0b00000001,
    DISCOVERING = 0b00000010,
    LINKED = 0b00000100,
    REPEAIRING = 0b00001000
};

class Camera
{
private:
    SocketUDP *udp_soc;
    SocketTCP *tcp_soc;
    std::vector<uint8_t> mac;

    uint8_t current_state = IDLE;

    Task *heartbeat_send_task;
    Task *heartbeat_response_task;

    IPAddress server_ip;
    uint16_t server_port;

    void _on_error(const std::string &msg)
    {
        Logger::error(msg);
        esp_restart();
    }

    void _append(std::vector<uint8_t> &out, const char *part)
    {
        out.insert(out.end(), part, part + strlen(part));
    }

    template <typename T>
    void _append(std::vector<uint8_t> &out, const T &part)
    {
        out.insert(out.end(), part.begin(), part.end());
    }

    template <typename... Args>
    std::vector<uint8_t> _fields_to_bytes(Args &&...args)
    {
        std::vector<uint8_t> out;
        bool first = true;
        int _[] = {
            0,
            (first ? (first = false, _append(out, args))
                   : (out.push_back(MESSAGE_SEPARATOR), _append(out, args)),
             0)...};
        (void)_;
        return out;
    }

    std::vector<std::vector<uint8_t>> _bytes_to_fields(const std::vector<uint8_t> &input)
    {
        std::vector<std::vector<uint8_t>> fields;
        std::vector<uint8_t> current;

        for (uint8_t byte : input)
        {
            if (byte == MESSAGE_SEPARATOR)
            {
                fields.push_back(current);
                current.clear();
            }
            else
            {
                current.push_back(byte);
            }
        }

        if (!current.empty() || input.back() == MESSAGE_SEPARATOR)
            fields.push_back(current);

        return fields;
    }

public:
    Camera(uint8_t mac[6])
    {
        Logger::info("Starting camera setup...");

        Logger::debug("Creating sockets...");
        udp_soc = new SocketUDP();
        tcp_soc = new SocketTCP();
        if (!udp_soc->begin())
            _on_error("Failed to start UDP socket!");

        Logger::debug("Setting up tasks...");
        heartbeat_send_task = new Task([this]()
                                       { this->send_heartbeat(); }, 1000);
        heartbeat_response_task = new Task([this]()
                                           { this->listen_for_heartbeat_response(); }, 1000);
        this->mac = std::vector<uint8_t>(mac, mac + 6);

        // TMP - will have to check storage if already have a server
        current_state = DISCOVERING;
    }

    // sec
    void set_server_data(std::string ip, uint16_t port)
    {
        IPAddress ipobj;
        if (!ipobj.fromString(ip.c_str()))
        {
            Logger::error("Attempted to connect to invalid ip!", ip);
            return;
        }
        this->server_ip = ipobj;
        this->server_port = port;
    }

    void send_heartbeat()
    {
        udp_soc->send(EthernetManager::get_broadcast_address(),
                      CAMERA_HEARTBEAT_PORT,
                      _fields_to_bytes("CAMPAIR-HSEC", EthernetManager::mac_bytes_to_string(mac.data())),
                      0);
    }

    void listen_for_heartbeat_response()
    {
        auto raw_bytes = udp_soc->recv();
        auto fields = _bytes_to_fields(raw_bytes);
        if (fields.size() != 3)
        {
            Logger::warning("Invalid pairing request. Too few fields, ignoring...");
            return;
        }

        std::string action(fields[0].begin(), fields[0].end());
        if (action != "CAMACK-HSEC")
        {
            Logger::warning("Invalid action sent instead of pairing request: ", action);
            return;
        }

        std::string code(fields[2].begin(), fields[2].end());
        if (code != CAMERA_CODE)
        {
            Logger::warning("Invalid code sent: ", code);
            return;
        }

        // BADCODE-HSEC
    }

    void tick()
    {
        if (current_state & DISCOVERING)
        {
            heartbeat_send_task->tick();
            heartbeat_response_task->tick();
        }
    }
};

#endif // CAMERA_H
