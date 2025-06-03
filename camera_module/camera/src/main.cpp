#include "logger/logger.h"
#include "encryption_manager/encryption_manager.h"

void printSecret(const char* label, const uint8_t* data, size_t len) {
    Logger::info(label);
    std::vector<char> hexDump(data, data + len);
    Logger::hexDump(hexDump);
}

void setup() {
    delay(5000);
    Logger::info("STARTING!");

    // Generate ECDH key pairs
    ECDHResult partyA = EncryptionManager::get_ecdh();
    ECDHResult partyB = EncryptionManager::get_ecdh();

    if (!partyA.success || !partyB.success) {
        Logger::error("ECDH key generation failed");
        return;
    }

    Logger::info("Party A public key:");
    Logger::hexDump(std::vector<char>(partyA.pubkey, partyA.pubkey + sizeof(partyA.pubkey)));

    Logger::info("Party B public key:");
    Logger::hexDump(std::vector<char>(partyB.pubkey, partyB.pubkey + sizeof(partyB.pubkey)));

    uint8_t shared1[20], shared2[20];

    bool ok1 = EncryptionManager::get_shared_secret(partyA, partyB.pubkey, shared1);
    bool ok2 = EncryptionManager::get_shared_secret(partyB, partyA.pubkey, shared2);

    if (!ok1 || !ok2) {
        Logger::error("Failed to compute shared secrets");
        return;
    }

    printSecret("Shared secret 1 (A → B):", shared1, sizeof(shared1));
    printSecret("Shared secret 2 (B → A):", shared2, sizeof(shared2));

    bool match = memcmp(shared1, shared2, sizeof(shared1)) == 0;
    if (match)
        Logger::info("Shared secrets MATCH");
    else
        Logger::error("Shared secrets MISMATCH");
}

void loop() {}
