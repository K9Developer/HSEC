//
// Created by ilaik on 5/27/2025.
//

#ifndef SOCKET_H
#define SOCKET_H
// #define SPI_ETHERNET_SETTINGS SPISettings(60'000'000, MSBFIRST, SPI_MODE0)
#include <Ethernet.h>
#include "../constants.h"
#include <vector>
#pragma push_macro("debug")
#undef debug
#pragma pop_macro("debug")
#include "../logger/logger.h"
#include <encryption_manager/encryption_manager.h>
#include <EthernetUdp.h>

enum DataTransferOptions
{
    WITH_SIZE = 0b00000001,
    ENCRYPT_AES = 0b00000010
};

class SocketTCP
{
private:
    std::vector<uint8_t> aesKey;
    std::vector<uint8_t> aesIV;

    std::vector<uint8_t> _recv(int bufferSize)
    {
        if (!tcp_client.connected())
            return {};

        std::vector<uint8_t> buffer;
        buffer.reserve(bufferSize);

        int timeout_counter = 0;

        while ((int)buffer.size() < bufferSize)
        {
            if (!tcp_client.available()) {
                delay(100);
                if (++timeout_counter >= 10)
                    break;
                continue;
            }

            int byte = tcp_client.read();
            if (byte < 0) {
                delay(10);
                continue;
            }

            buffer.push_back(static_cast<uint8_t>(byte));
            timeout_counter = 0; // reset on successful read
        }

        buffer.shrink_to_fit();
        return buffer;
    }

    bool _send(const uint8_t *data, size_t len)
    {
        if (!tcp_client || !tcp_client.connected())
            return false;

        size_t offset = 0;

        while (offset < len)
        {
            size_t space = tcp_client.availableForWrite();
            if (space == 0)
            {
                yield(); // better than delay for concurrency
                continue;
            }

            size_t to_write = std::min(space, len - offset);
            if (!tcp_client || !tcp_client.connected())
                return false;
            size_t written = tcp_client.write(data + offset, to_write);
            // Logger::debug("WRITTEN ", written, " bytes");
            if (written <= 0)
                return false;

            offset += written;
        }

        return true;
    }

    bool _send(const std::vector<uint8_t> &data)
    {
        return _send(data.data(), data.size());
    }

    // Big endian
    uint64_t number_from_bytes(const std::vector<uint8_t> &vec)
    {
        uint64_t result = 0;
        for (size_t i = 0; i < vec.size(); ++i)
        {
            result <<= 8;
            result |= static_cast<uint8_t>(vec[i]);
        }
        return result;
    }

    // Big endian
    std::vector<uint8_t> number_to_bytes(int32_t num, int bytes)
    {
        std::vector<uint8_t> out;
        out.reserve(bytes);
        for (int shift = (bytes - 1) * 8; shift >= 0; shift -= 8)
        {
            out.push_back(static_cast<char>((static_cast<uint32_t>(num) >> shift) & 0xFF));
        }
        return out;
    }

public:
    EthernetClient tcp_client;

    SocketTCP()
    {
    }

    void dumpEthernetStatus()
    {
        switch (Ethernet.hardwareStatus())
        {
        case EthernetNoHardware:
            Serial.println("No Ethernet shield");
            break;
        case EthernetW5100:
            Serial.println("W5100 detected");
            break;
        case EthernetW5200:
            Serial.println("W5200 detected");
            break;
        case EthernetW5500:
            Serial.println("W5500 detected");
            break;
        }

        switch (Ethernet.linkStatus())
        {
        case Unknown:
            Serial.println("Link status: unknown (old W5100?)");
            break;
        case LinkON:
            Serial.println("Link status: ON (cable OK)");
            break;
        case LinkOFF:
            Serial.println("Link status: **OFF** (cable?)");
            break;
        }

        Serial.print("Local  IP : ");
        Serial.println(Ethernet.localIP());
        Serial.print("Gateway IP: ");
        Serial.println(Ethernet.gatewayIP());
    }

public:
    bool set_aes_data(const uint8_t *aesKeyInput, size_t length)
    {
        if (length != 32)
        {
            Logger::error("AES key must be 32 bytes long!");
            return false;
        }

        aesKey.assign(aesKeyInput, aesKeyInput + 32);
        aesIV.assign(aesKey.begin(), aesKey.begin() + 16);
        return true;
    }

    bool connect(const std::string &ip, uint16_t port)
    {
        IPAddress ipobj;
        if (!ipobj.fromString(ip.c_str()))
        {
            Logger::error("Attempted to connect to invalid ip!", ip);
        }
        return this->connect(ipobj, port);
    }

    bool connect(const IPAddress &ip, uint16_t port)
    {
        Logger::debug("Connecting to ", ip, ":", port);
        return this->tcp_client.connect(ip, port);
    }

    std::vector<uint8_t> recv(int bufferSize = -1, int flags = DataTransferOptions::WITH_SIZE)
    {
        // If DataTransferOptions::WITH_SIZE is set then buffer size doesnt matter
        if (!(flags & DataTransferOptions::WITH_SIZE) && bufferSize < 0)
        {
            Logger::error("Cannot use an invalid buffer size when DataTransferOptions::WITH_SIZE is not set in recv");
            return {};
        }

        if (flags & DataTransferOptions::WITH_SIZE)
        {
            std::vector<uint8_t> sizeBytes = this->_recv(MESSAGE_SIZE_BYTE_LENGTH);
            if (sizeBytes.size() != MESSAGE_SIZE_BYTE_LENGTH) {
                return {};
            }
            bufferSize = this->number_from_bytes(sizeBytes);
            Logger::debug("Got message size (via DataTransferOptions::WITH_SIZE) of ", bufferSize, " bytes");
        }

        std::vector<uint8_t> raw = this->_recv(bufferSize);
        if (flags & DataTransferOptions::ENCRYPT_AES)
        {
            if (flags & DataTransferOptions::WITH_SIZE && raw.size() != bufferSize)
            {
                Logger::error("Recieved an invalid message length! expected: ", bufferSize, ", instead got: ", raw.size());
                return {};
            }

            if (this->aesKey.empty() || this->aesIV.empty())
            {
                Logger::error("The AES key or the AES IV is not set. Cannot recv with the AES flag.");
                return {};
            }

            return EncryptionManager::decrypt_aes(
                raw,
                this->aesKey,
                this->aesIV);
        }

        return raw;
    }

    bool send(std::vector<uint8_t> data, int flags = DataTransferOptions::WITH_SIZE)
    {
        if (flags & DataTransferOptions::ENCRYPT_AES)
        {
            data = EncryptionManager::encrypt_aes(
                data,
                this->aesKey,
                this->aesIV);
            if (data.empty())
            {
                Logger::error("Failed to encrypt.");
                return false;
            }
        }

        if (flags & DataTransferOptions::WITH_SIZE)
        {
            auto size_bytes = this->number_to_bytes(data.size(), MESSAGE_SIZE_BYTE_LENGTH);
            data.insert(data.begin(), size_bytes.begin(), size_bytes.end());
        }

        return this->_send(data);;
    }
};

class SocketUDP
{
private:
    unsigned int localPort = 0;

    std::vector<uint8_t> _recv(int bufferSize)
    {
        std::vector<uint8_t> buffer;
        buffer.reserve(bufferSize);
        while (buffer.size() < bufferSize && udp_client.available())
        {
            buffer.push_back(udp_client.read());
        }
        buffer.shrink_to_fit();
        return buffer;
    }

    bool _send(const IPAddress &ip, uint16_t port, const std::vector<uint8_t> &data)
    {
        if (!udp_client.beginPacket(ip, port))
            return false;
        udp_client.write(data.data(), data.size());
        return udp_client.endPacket() == 1;
    }

    uint64_t number_from_bytes(const std::vector<uint8_t> &vec)
    {
        uint64_t result = 0;
        for (size_t i = 0; i < vec.size(); ++i)
        {
            result <<= 8;
            result |= static_cast<uint8_t>(vec[i]);
        }
        return result;
    }

    std::vector<uint8_t> number_to_bytes(int32_t num, int bytes)
    {
        std::vector<uint8_t> out;
        out.reserve(bytes);
        for (int shift = (bytes - 1) * 8; shift >= 0; shift -= 8)
        {
            out.push_back(static_cast<char>((static_cast<uint32_t>(num) >> shift) & 0xFF));
        }
        return out;
    }

public:
    EthernetUDP udp_client;
    SocketUDP() {}

    bool begin(uint16_t port = 0)
    {
        localPort = port;
        return udp_client.begin(port);
    }

    unsigned int getPort() const
    {
        return localPort;
    }

    bool send(const std::string &ip, uint16_t port, std::vector<uint8_t> data, int flags = DataTransferOptions::WITH_SIZE)
    {
        IPAddress ipobj;
        if (!ipobj.fromString(ip.c_str()))
        {
            Logger::error("Invalid IP format:", ip);
            return false;
        }

        if (flags & DataTransferOptions::WITH_SIZE)
        {
            auto size_bytes = number_to_bytes(data.size(), MESSAGE_SIZE_BYTE_LENGTH);
            data.insert(data.begin(), size_bytes.begin(), size_bytes.end());
        }

        return _send(ipobj, port, data);
    }

    std::vector<uint8_t> recv(int bufferSize = -1)
    {
        int packetSize = udp_client.parsePacket();
        if (packetSize <= 0)
            return {};
        return _recv(bufferSize == -1 ? packetSize : bufferSize);
    }
};

#endif // SOCKET_H
