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

enum DataTransferOptions {
    WITH_SIZE = 0b00000001,
    ENCRYPT_AES = 0b00000010
};

class SocketTCP {
private:
    EthernetClient client;
    char* aesKey;
    char* aesIV;
    AESLib aes;

    std::vector<char> _recv(int bufferSize) {
        if (!client.connected()) return {};
        std::vector<char> buffer;
        buffer.reserve(bufferSize);
        for (int i = 0; i < bufferSize; i++) {
            if (!client.available()) break;
            buffer.push_back(client.read());
        }
        buffer.shrink_to_fit();
        return buffer;
    }

    bool _send(const std::vector<char>& data)      // pass by const-ref; no copy needed
    {
        if (!client.connected()) return false;
        Logger::debug("Sending ", data.size(), " bytes");
        client.write(reinterpret_cast<const uint8_t*>(data.data()), data.size());                 // explicit length → binary-safe
        return true;
    }

    // Big endian
    uint64_t number_from_bytes(const std::vector<char>& vec) {
        uint64_t result = 0;
        for (size_t i = 0; i < vec.size(); ++i) {
            result <<= 8;
            result |= static_cast<uint8_t>(vec[i]);
        }
        return result;
    }

    // Big endian
    std::vector<char> number_to_bytes(int32_t num, int bytes)
    {
        std::vector<char> out;
        out.reserve(bytes);
        for (int shift = (bytes - 1) * 8; shift >= 0; shift -= 8) {
            out.push_back(static_cast<char>((static_cast<uint32_t>(num) >> shift) & 0xFF));
        }
        return out;
    }

    std::vector<char> _decrypt_aes(std::vector<char> raw) {
        if (raw.empty()) {
            Logger::warning("Decrypt called with empty buffer");
            return {};
        }

        if (this->aesKey == nullptr || this->aesIV == nullptr) {
            Logger::error("AES key or IV not set – cannot decrypt");
            return {};
        }

        std::vector<char> plain(raw.size());
        byte ivCopy[16];
        memcpy(ivCopy, this->aesIV, 16);

        uint16_t decLen = this->aes.decrypt(
            reinterpret_cast<byte *>(raw.data()),
            static_cast<uint16_t>(raw.size()),
            reinterpret_cast<byte *>(plain.data()),
            reinterpret_cast<const byte *>(this->aesKey),
            128,
            ivCopy);

        if (decLen == 0) {
            Logger::error("AES decryption failed – check key/IV/length");
            return {};
        }

        uint8_t pad = plain[decLen - 1];
        if (pad == 0 || pad > 16) {
            Logger::warning("Padding byte invalid – returning raw block");
            plain.resize(decLen);
            return plain;
        }

        plain.resize(decLen - pad);
        return plain;
    }

    std::vector<char> _encrypt_aes(const std::vector<char>& plain)
    {
        if (plain.empty()) {
            Logger::warning("Encrypt called with empty buffer");
            return {};
        }

        if (this->aesKey == nullptr || this->aesIV == nullptr) {
            Logger::error("AES key or IV not set – cannot encrypt");
            return {};
        }

        std::vector<char> padded = plain;
        uint8_t pad = 16 - (padded.size() % 16);
        if (pad == 0) pad = 16;
        padded.insert(padded.end(), pad, static_cast<char>(pad));

        std::vector<char> cipher(padded.size());
        byte ivCopy[16];
        memcpy(ivCopy, this->aesIV, 16);

        uint16_t encLen = this->aes.encrypt(
            reinterpret_cast<byte*>(padded.data()),
            static_cast<uint16_t>(padded.size()),
            reinterpret_cast<byte*>(cipher.data()),
            reinterpret_cast<const byte*>(this->aesKey),
            128,
            ivCopy);

        if (encLen == 0) {
            Logger::error("AES encryption failed – check key/IV");
            return {};
        }
        cipher.resize(encLen);
        return cipher;
    }

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
    bool connect(const std::string &ip, uint16_t port) {
        IPAddress ipobj;
        if (!ipobj.fromString(ip.c_str())) {
            Logger::error("Attempted to connect to invalid ip!", ip);
        }
        Logger::debug("Connecting to ", ip);
        return this->client.connect(ipobj, port);
    }

    std::vector<char> recv(int bufferSize = -1, int flags = DataTransferOptions::WITH_SIZE) {
        // If DataTransferOptions::WITH_SIZE is set then buffer size doesnt matter
        if (!(flags&DataTransferOptions::WITH_SIZE) && bufferSize < 0) {
            Logger::error("Cannot use an invalid buffer size when DataTransferOptions::WITH_SIZE is not set in recv");
            return {};
        }

        if (flags & DataTransferOptions::WITH_SIZE) {
            std::vector<char> sizeBytes = this->_recv(MESSAGE_SIZE_BYTE_LENGTH);
            bufferSize = this->number_from_bytes(sizeBytes);
            Logger::debug("Got message size (via DataTransferOptions::WITH_SIZE) of ", bufferSize, " bytes");
        }

        std::vector<char> raw = this->_recv(bufferSize);
        if (flags & DataTransferOptions::ENCRYPT_AES) {
            if (flags & DataTransferOptions::WITH_SIZE && raw.size() != bufferSize) {
                Logger::error("Recieved an invalid message length! expected: ", bufferSize, ", instead got: ", raw.size());
                return {};
            }

            if (this->aesKey == nullptr || this->aesIV == nullptr) {
                Logger::error("The AES key or the AES IV is not set. Cannot recv with the AES flag.");
                return {};
            }

            return this->_decrypt_aes(raw);
        } else {
            return raw;
        }
    }

    bool send(std::vector<char> data, int flags = DataTransferOptions::WITH_SIZE) {
        if (flags & DataTransferOptions::ENCRYPT_AES) {
            Logger::debug("Encrypting data with AES...");
            data = this->_encrypt_aes(data);
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
