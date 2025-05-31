/*
  AES-256/CBC demo  —  suculent/AESLib
  Encrypts a short message, then decrypts it back.

  ⚠  SECURITY NOTE
  Re-using part of the key as the IV is **not** recommended in real systems.
  It’s done here only because the exercise requires it.
*/

#include <logger/logger.h>
#include <encryption_manager/encryption_manager.h>
// std::vector<uint8_t> to std::vector<char>
std::vector<char> u8Tochr(std::vector<uint8_t>& arr) {
    std::vector<char> result(arr.size());
    std::copy(arr.begin(), arr.end(), result.begin());
    return result;
}

void setup() {
    delay(5000);
    Logger::info("Starting AES-256/CBC demo...");

    std::vector<uint8_t> key = {'T', 'h', 'i', 's', 'I', 's', 'A', 'S', 'e', 'c', 'r', 'e', 't', 'K', 'e', 'y', 'T', 'h', 'i', 's', 'I', 's', 'A', 'S', 'e', 'c', 'r', 'e', 't', 'K', 'e', 'y'};
    std::vector<uint8_t> iv = {'T', 'h', 'i', 's', 'I', 's', 'A', 'S', 'e', 'c', 'r', 'e', 't', 'I', 'V', 'V'};
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o', ' ', 'W', 'o', 'r', 'l', 'd', '!'};

    Logger::info("KEY LENGTH: ", key.size());
    Logger::info("IV LENGTH: ", iv.size());

    Logger::hexDump(u8Tochr(plaintext));
    std::vector<uint8_t> ciphertext = EncryptionManager::encrypt_aes(plaintext, key, iv);
    Logger::info("Ciphertext:");
    Logger::hexDump(u8Tochr(ciphertext));
    std::vector<uint8_t> decrypted = EncryptionManager::decrypt_aes(ciphertext, key, iv);
    Logger::hexDump(u8Tochr(decrypted));
    if (decrypted == plaintext) {
        Logger::info("Decryption successful!");
    } else {
        Logger::error("Decryption failed!");
    }
}

void loop() {}