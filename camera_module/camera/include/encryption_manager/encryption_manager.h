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

struct ECDHResult
{
    const uECC_Curve_t *curve;
    uint8_t pubkey[64];
    uint8_t privkey[32];
    int shared_secret_size;
    bool success;
};

class EncryptionManager
{
public:
    static std::vector<uint8_t> encrypt_aes(
    const std::vector<uint8_t>& plain,
    const std::vector<uint8_t>& key,
    const std::vector<uint8_t>& iv)
{
    const size_t block = 16;
    if (key.size() != 32 || iv.size() != block) {
        Logger::debug("encrypt_aes: invalid key or IV size");
        return {};
    }

    try {
        size_t paddedLen = ((plain.size() + block) / block) * block;
        std::vector<uint8_t> buf(paddedLen, 0);
        memcpy(buf.data(), plain.data(), plain.size());
        uint8_t pad = static_cast<uint8_t>(paddedLen - plain.size());
        memset(buf.data() + plain.size(), pad, pad);

        mbedtls_aes_context ctx;
        mbedtls_aes_init(&ctx);

        if (mbedtls_aes_setkey_enc(&ctx, key.data(), 256) != 0) {
            Logger::debug("encrypt_aes: mbedtls_aes_setkey_enc failed");
            mbedtls_aes_free(&ctx);
            return {};
        }

        std::vector<uint8_t> iv_local(iv);
        if (mbedtls_aes_crypt_cbc(&ctx, MBEDTLS_AES_ENCRYPT,
                                  paddedLen, iv_local.data(),
                                  buf.data(), buf.data()) != 0) {
            Logger::debug("encrypt_aes: mbedtls_aes_crypt_cbc failed");
            mbedtls_aes_free(&ctx);
            return {};
        }

        mbedtls_aes_free(&ctx);
        return buf;
    } catch (...) {
        Logger::debug("encrypt_aes: exception caught");
        return {};
    }
}

static std::vector<uint8_t> decrypt_aes(
    const std::vector<uint8_t>& cipher,
    const std::vector<uint8_t>& key,
    const std::vector<uint8_t>& iv)
{
    const size_t block = 16;
    if (key.size() != 32 || iv.size() != block || cipher.size() % block != 0) {
        Logger::debug("decrypt_aes: invalid key/IV size or cipher length");
        return {};
    }

    try {
        std::vector<uint8_t> buf(cipher);
        mbedtls_aes_context ctx;
        mbedtls_aes_init(&ctx);

        if (mbedtls_aes_setkey_dec(&ctx, key.data(), 256) != 0) {
            Logger::debug("decrypt_aes: mbedtls_aes_setkey_dec failed");
            mbedtls_aes_free(&ctx);
            return {};
        }

        std::vector<uint8_t> iv_local(iv);
        if (mbedtls_aes_crypt_cbc(&ctx, MBEDTLS_AES_DECRYPT,
                                  buf.size(), iv_local.data(),
                                  buf.data(), buf.data()) != 0) {
            Logger::debug("decrypt_aes: mbedtls_aes_crypt_cbc failed");
            mbedtls_aes_free(&ctx);
            return {};
        }

        mbedtls_aes_free(&ctx);

        if (buf.empty()) {
            Logger::debug("decrypt_aes: decrypted buffer empty");
            return {};
        }

        uint8_t pad = buf.back();
        if (pad == 0 || pad > block) {
            Logger::debug("decrypt_aes: invalid padding value");
            return {};
        }

        for (size_t i = buf.size() - pad; i < buf.size(); ++i) {
            if (buf[i] != pad) {
                Logger::debug("decrypt_aes: bad PKCS7 padding");
                return {};
            }
        }

        buf.resize(buf.size() - pad);
        return buf;
    } catch (...) {
        Logger::debug("decrypt_aes: exception caught");
        return {};
    }
}


    static ECDHResult get_ecdh()
    {
        auto res = ECDHResult();
        res.curve = uECC_secp256r1();
        res.success = uECC_make_key(res.pubkey, res.privkey, res.curve);
        res.shared_secret_size = uECC_curve_private_key_size(res.curve);
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