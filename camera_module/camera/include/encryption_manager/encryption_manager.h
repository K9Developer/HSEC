#ifndef ENCRYPTION_MANAGER_H
#define ENCRYPTION_MANAGER_H

#include <AESLib.h>
#include <vector>

#include <AESLib.h>

static AESLib aesLib; //  global – keeps padding mode

class EncryptionManager
{
    static void use_pkcs7() { aesLib.set_paddingmode((paddingMode)0); }

    static size_t cipher_capacity(size_t plainLen)
    {
        return aesLib.get_cipher_length(static_cast<uint16_t>(plainLen));
    }

public:
    static std::vector<uint8_t> encrypt_aes(const std::vector<uint8_t> &plain,
                                            const std::vector<uint8_t> &key,
                                            const std::vector<uint8_t> &iv)
    {

        use_pkcs7();

        std::vector<uint8_t> iv_local(iv);
        std::vector<uint8_t> cipher(cipher_capacity(plain.size()));

        uint16_t encLen = aesLib.encrypt(
            plain.data(),
            static_cast<uint16_t>(plain.size()),
            cipher.data(),
            key.data(), 256,
            iv_local.data());

        cipher.resize(encLen);
        return cipher;
    }

    static std::vector<uint8_t> decrypt_aes(const std::vector<uint8_t> &cipher,
                                            const std::vector<uint8_t> &key,
                                            const std::vector<uint8_t> &iv)
    {

        use_pkcs7();

        std::vector<uint8_t> iv_local(iv);
        std::vector<uint8_t> plain(cipher.size());

        uint16_t plainLen = aesLib.decrypt(
            const_cast<uint8_t *>(cipher.data()),
            static_cast<uint16_t>(cipher.size()),
            plain.data(),
            key.data(), 256,
            iv_local.data());

        plain.resize(plainLen);
        return plain;
    }
};

#endif /* ENCRYPTION_MANAGER_H */