#ifndef ENCRYPTION_MANAGER_H
#define ENCRYPTION_MANAGER_H

#include <vector>
#include <uECC.h>
#include "esp_system.h"
#include "mbedtls/aes.h"

static int RNG(uint8_t *dest, unsigned size)
{
    while (size--)
    {
        *dest++ = (uint8_t)esp_random();
    }
    return 1;
}

struct ECCInitializer
{
    ECCInitializer()
    {
        uECC_set_rng(&RNG);
    }
};

static ECCInitializer ecc_init_guard; // call set rng once
static AESLib aesLib;

struct ECDHResult
{
    const uECC_Curve_t *curve;
    uint8_t pubkey[40];
    uint8_t privkey[21];
    bool success;
};

class EncryptionManager
{
    static void use_pkcs7() { aesLib.set_paddingmode((paddingMode)0); }

    static size_t cipher_capacity(size_t plainLen)
    {
        return aesLib.get_cipher_length(static_cast<uint16_t>(plainLen));
    }

public:
    static std::vector<uint8_t> encrypt_aes(
        const std::vector<uint8_t> &plain,
        const std::vector<uint8_t> &key,
        const std::vector<uint8_t> &iv)
    {
        const size_t block = 16;
        size_t paddedLen = ((plain.size() + block) / block) * block;
        std::vector<uint8_t> buf(paddedLen, 0);
        memcpy(buf.data(), plain.data(), plain.size());
        uint8_t pad = static_cast<uint8_t>(paddedLen - plain.size());
        memset(buf.data() + plain.size(), pad, pad);

        mbedtls_aes_context ctx;
        mbedtls_aes_init(&ctx);
        mbedtls_aes_setkey_enc(&ctx, key.data(), 256);
        std::vector<uint8_t> iv_local(iv);
        mbedtls_aes_crypt_cbc(&ctx, MBEDTLS_AES_ENCRYPT,
                              paddedLen, iv_local.data(),
                              buf.data(), buf.data());
        mbedtls_aes_free(&ctx);

        return buf;
    }

    static std::vector<uint8_t> decrypt_aes(
        const std::vector<uint8_t> &cipher,
        const std::vector<uint8_t> &key,
        const std::vector<uint8_t> &iv)
    {
        std::vector<uint8_t> buf(cipher);
        mbedtls_aes_context ctx;
        mbedtls_aes_init(&ctx);
        mbedtls_aes_setkey_dec(&ctx, key.data(), 256);
        std::vector<uint8_t> iv_local(iv);
        mbedtls_aes_crypt_cbc(&ctx, MBEDTLS_AES_DECRYPT,
                              buf.size(), iv_local.data(),
                              buf.data(), buf.data());
        mbedtls_aes_free(&ctx);

        uint8_t pad = buf.back();
        buf.resize(buf.size() - pad);
        return buf;
    }

    static ECDHResult get_ecdh()
    {
        auto res = ECDHResult();
        res.curve = uECC_secp160r1();
        res.success = uECC_make_key(res.pubkey, res.privkey, res.curve);
        return res;
    }

    static bool get_shared_secret(const ECDHResult &own_data, uint8_t other_pub[], uint8_t *out_secret)
    {
        if (!uECC_shared_secret(other_pub, own_data.privkey, out_secret, own_data.curve))
            return false;

        return true;
    }
};

#endif /* ENCRYPTION_MANAGER_H */