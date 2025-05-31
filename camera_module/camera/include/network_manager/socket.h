//
// Created by ilaik on 5/27/2025.
//

#ifndef SOCKET_H
#define SOCKET_H

#include <Ethernet.h>
#include "../constants.h"
#include <vector>
#include <AESLib.h>
#include "../logger/logger.h"
#include <encryption_manager/encryption_manager.h>

enum DataTransferOptions {
    WITH_SIZE = 0b00000001,
    ENCRYPT_AES = 0b00000010
};

class SocketTCP {
private:
    EthernetClient client;
    std::vector<uint8_t> aesKey;
    std::vector<uint8_t> aesIV;
    // AESLib aes;

    std::vector<uint8_t> _recv(int bufferSize) {
        if (!client.connected()) return {};
        std::vector<uint8_t> buffer;
        buffer.reserve(bufferSize);
        for (int i = 0; i < bufferSize; i++) {
            if (!client.available()) break;
            buffer.push_back(client.read());
        }
        buffer.shrink_to_fit();
        return buffer;
    }

    bool _send(const std::vector<uint8_t>& data)
    {
        if (!client.connected()) return false;
        Logger::debug("Sending ", data.size(), " bytes");
        client.write(reinterpret_cast<const uint8_t*>(data.data()), data.size());
        return true;
    }

    // Big endian
    uint64_t number_from_bytes(const std::vector<uint8_t>& vec) {
        uint64_t result = 0;
        for (size_t i = 0; i < vec.size(); ++i) {
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
        for (int shift = (bytes - 1) * 8; shift >= 0; shift -= 8) {
            out.push_back(static_cast<char>((static_cast<uint32_t>(num) >> shift) & 0xFF));
        }
        return out;
    }
public:
    void dumpEthernetStatus()
    {
        switch (Ethernet.hardwareStatus()) {
            case EthernetNoHardware:   Serial.println("No Ethernet shield");     break;
            case EthernetW5100:        Serial.println("W5100 detected");         break;
            case EthernetW5200:        Serial.println("W5200 detected");         break;
            case EthernetW5500:        Serial.println("W5500 detected");         break;
        }

        switch (Ethernet.linkStatus()) {
            case Unknown:  Serial.println("Link status: unknown (old W5100?)");  break;
            case LinkON:   Serial.println("Link status: ON (cable OK)");         break;
            case LinkOFF:  Serial.println("Link status: **OFF** (cable?)");      break;
        }

        Serial.print("Local  IP : "); Serial.println(Ethernet.localIP());
        Serial.print("Gateway IP: "); Serial.println(Ethernet.gatewayIP());
    }

public:
    bool setAesData(const uint8_t* aesKeyInput, size_t length) {
        if (length != 32) {
            Logger::error("AES key must be 32 bytes long!");
            return false;
        }

        aesKey.assign(aesKeyInput, aesKeyInput + 32);
        aesIV.assign(aesKey.begin(), aesKey.begin() + 16);
    }


    bool connect(const std::string &ip, uint16_t port) {
        IPAddress ipobj;
        if (!ipobj.fromString(ip.c_str())) {
            Logger::error("Attempted to connect to invalid ip!", ip);
        }
        Logger::debug("Connecting to ", ip);
        return this->client.connect(ipobj, port);
    }

    std::vector<uint8_t> recv(int bufferSize = -1, int flags = DataTransferOptions::WITH_SIZE) {
        // If DataTransferOptions::WITH_SIZE is set then buffer size doesnt matter
        if (!(flags&DataTransferOptions::WITH_SIZE) && bufferSize < 0) {
            Logger::error("Cannot use an invalid buffer size when DataTransferOptions::WITH_SIZE is not set in recv");
            return {};
        }

        if (flags & DataTransferOptions::WITH_SIZE) {
            std::vector<uint8_t> sizeBytes = this->_recv(MESSAGE_SIZE_BYTE_LENGTH);
            bufferSize = this->number_from_bytes(sizeBytes);
            Logger::debug("Got message size (via DataTransferOptions::WITH_SIZE) of ", bufferSize, " bytes");
        }

        std::vector<uint8_t> raw = this->_recv(bufferSize);
        if (flags & DataTransferOptions::ENCRYPT_AES) {
            if (flags & DataTransferOptions::WITH_SIZE && raw.size() != bufferSize) {
                Logger::error("Recieved an invalid message length! expected: ", bufferSize, ", instead got: ", raw.size());
                return {};
            }

            if (this->aesKey.empty() || this->aesIV.empty()) {
                Logger::error("The AES key or the AES IV is not set. Cannot recv with the AES flag.");
                return {};
            }

            return EncryptionManager::decrypt_aes(
                raw,
                this->aesKey,
                this->aesIV
            );
        } else {
            return raw;
        }
    }

    bool send(std::vector<uint8_t> data, int flags = DataTransferOptions::WITH_SIZE) {
        if (flags & DataTransferOptions::ENCRYPT_AES) {
            Logger::debug("Encrypting data with AES...");
            data = EncryptionManager::encrypt_aes(
                data,
                this->aesKey,
                this->aesIV
            );
            if (data.empty()) {
                Logger::error("Failed to encrypt.");
                return false;
            }
        }

        if (flags & DataTransferOptions::WITH_SIZE) {
            Logger::debug("Adding size bytes...");
            auto size_bytes = this->number_to_bytes(data.size(), MESSAGE_SIZE_BYTE_LENGTH);
            data.insert(data.begin(), size_bytes.begin(), size_bytes.end());
        }

        return this->_send(data);
    }
};

#endif //SOCKET_H
