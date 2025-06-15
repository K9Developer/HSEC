#ifndef CAMERA_H
#define CAMERA_H

#include "network_manager/socket.h"
#include "network_manager/network_manager.h"
#include "logger/logger.h"
#include "camera_manager/camera_manager.h"
#include "eeprom_manager.h"
#include "task.h"
#include <vector>
#include <string>
#include <tuple>

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
    std::string mac_str;

    // uint8_t current_state = IDLE;
    uint8_t current_state = DISCOVERING;

    std::vector<uint8_t> curr_frame;
    CameraManager* camera = &CameraManager::getInstance();

    Task *heartbeat_send_task;
    Task *heartbeat_response_task;
    Task *repair_task;
    Task *stream_task;
    Task *listen_task;

    uint8_t frame_counter = 0;

    ServerData server_data;

    void _on_fatal_error(const std::string &msg)
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

    std::string decode(std::vector<uint8_t> buff) {
        std::string s;
        for (auto c: buff) s += c;
        return s;
    }

    std::vector<uint8_t> encode(std::string s) {
        std::vector<uint8_t> buff;
        for (auto c: s) buff.push_back(c);
        return buff;
    }

    void _purge_server() {
        this->tcp_soc->tcp_client.flush();
        this->tcp_soc->tcp_client.stop();

        this->server_data.addr = IPAddress();
        this->server_data.port = 0;

        this->curr_frame.clear();
        this->curr_frame.shrink_to_fit();

        clear_eeprom();
    }

    std::tuple<bool, std::vector<uint8_t>, std::vector<uint8_t>> handle_key_exchange() {

        // Server hello
        auto server_hello_raw = this->tcp_soc->recv();
        if (server_hello_raw.empty()) {
            Logger::error("Failed to recieve server hello, leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }
        auto server_hello_fields = this->_bytes_to_fields(server_hello_raw);
        if (decode(server_hello_fields[0]) != "exch" || decode(server_hello_fields[1]) != "ecdh" || decode(server_hello_fields[2]) != "aes") {
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }

        auto raw_server_pubkey = join_fields(3, server_hello_fields);
        Logger::info("Recieved server public key: ", Logger::get_hex(raw_server_pubkey));
        Logger::info("Generating own keys...");
        auto ecdh_data = EncryptionManager::get_ecdh();
        if (!ecdh_data.success) {
            Logger::error("Failed to create ECDH data! leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }
        Logger::info("Own public key: ", Logger::get_hex(std::vector<uint8_t>(ecdh_data.pubkey, ecdh_data.pubkey+64)));

        uint8_t shared_secret[ecdh_data.shared_secret_size];
        auto shared_sec_success = EncryptionManager::get_shared_secret(ecdh_data, raw_server_pubkey.data(), shared_secret);
        if (!shared_sec_success) {
            Logger::error("Failed to create shared secret! leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }
        auto shared_secret_vec = std::vector<uint8_t>(shared_secret, shared_secret+ecdh_data.shared_secret_size);
        Logger::info("Shared secret: ", Logger::get_hex(shared_secret_vec));

        // Client hello
        this->tcp_soc->send(_fields_to_bytes("exch", "ecdh", "aes", std::vector<uint8_t>(ecdh_data.pubkey, ecdh_data.pubkey+64)));
        Logger::debug("Sent own public key.");
        this->tcp_soc->set_aes_data(shared_secret_vec.data(), shared_secret_vec.size());

        // Confirmation
        Logger::info("Free heap: ", esp_get_free_heap_size());
        auto iv = std::vector<uint8_t>(shared_secret, shared_secret+16);
        auto encrypted_confirm = EncryptionManager::encrypt_aes(encode("confirm"), shared_secret_vec, iv);
        if (encrypted_confirm.empty()) {
            Logger::error("Failed to encrypt confirmation. Leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }
        this->tcp_soc->send(encrypted_confirm);
        Logger::debug("Sent encrypted confirmation. Waiting for server confirmation...");
        Logger::hex_dump(encrypted_confirm);
        auto server_conf_raw = this->tcp_soc->recv();
        if (server_conf_raw.empty()) {
            Logger::error("Failed to recieve server confirmation. Leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }
        auto server_conf = EncryptionManager::decrypt_aes(server_conf_raw, shared_secret_vec, iv);
        if (server_conf.empty()) {
            Logger::error("Failed to decrypt server confirmation. Leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }
        if (decode(server_conf) != "confirm") {
            Logger::error("Server confirmation is not \"confirm\" (", decode(server_conf), "). Leaving...");
            return std::make_tuple(false, std::vector<uint8_t>{}, std::vector<uint8_t>{});
        }

        Logger::info("Key exchange successful!");
        return std::make_tuple(true, shared_secret_vec, iv);
    }

    std::vector<uint8_t> join_fields(int start, std::vector<std::vector<uint8_t>> fields) {
        std::vector<uint8_t> joined;
        for (int i = start; i < fields.size(); i++) {
            joined.insert(joined.end(), fields[i].begin(), fields[i].end());
            if (i != fields.size()-1) joined.push_back(MESSAGE_SEPARATOR);
        }
        return joined;
    }

    bool _link_to_server() {

        Logger::info("Connecting to camera server...");
        if (this->tcp_soc->tcp_client.connected()) {
            Logger::error("Camera already connected to camera server (", this->server_data.addr.toString(), "), ignoring pairing request.");
            return false;
        }

        auto connection_status = this->tcp_soc->connect(this->server_data.addr, this->server_data.port);
        if (!connection_status) {
            Logger::error("Failed to connect to camera server! ignoring...");
            return false;
        }

        // confirm link
        this->tcp_soc->send(this->_fields_to_bytes("CAMLINK-HSEC", this->mac_str));
        Logger::debug("Sent link confirmation.");
        auto xchng_data = this->handle_key_exchange();

        if (!std::get<0>(xchng_data)) {
            Logger::error("Failed to exchange keys with the server.");
            return false;
        }

        Logger::info("Successfuly linked to server!");
        std::copy_n(std::get<1>(xchng_data).begin(), 32, this->server_data.shared_secret);
        std::copy_n(std::get<2>(xchng_data).begin(), 16, this->server_data.aes_iv);
        update_server_data();

        return true;
    }

    bool _relink_to_server() {
        Logger::info("(re)Connecting to camera server...");
        if (this->tcp_soc->tcp_client.connected()) {
            Logger::error("Camera already connected to camera server (", this->server_data.addr.toString(), "), ignoring pairing request.");
            return false;
        }

        auto connection_status = this->tcp_soc->connect(this->server_data.addr, this->server_data.port);
        if (!connection_status) {
            Logger::error("Failed to connect to camera server! ignoring...");
            return false;
        }

        auto succ_send = this->tcp_soc->send(this->_fields_to_bytes("CAMRELINK-HSEC", this->mac_str));
        if (!succ_send) {
            Logger::error("Failed to send relink request, leaving...");
            return false;
        }
        Logger::info("Sent RE-LINK.");

        // TODO: Check failed sends
        auto server_repair_raw = this->tcp_soc->recv();
        if (server_repair_raw.empty()) {
            Logger::error("Failed to get server reapir, leaving...");
            return false;
        }

        auto shared_sec_vec = std::vector<uint8_t>(this->server_data.shared_secret, this->server_data.shared_secret+32);
        auto iv_vec = std::vector<uint8_t>(this->server_data.aes_iv, this->server_data.aes_iv+16);
        auto server_repair_fields = _bytes_to_fields(server_repair_raw);

        if (server_repair_fields.size() < 2 || decode(server_repair_fields[0]) != "CAMREPAIR-HSEC") {
            Logger::error("Failed to get server reapir (2), leaving...");
            return false;
        }

        auto decrypted_confirm = EncryptionManager::decrypt_aes(join_fields(1, server_repair_fields), shared_sec_vec, iv_vec);
        if (decode(decrypted_confirm) != "confirm-pair") {
            Logger::error("Failed to get \"confirm-pair\", leaving...");
            return false;
        }

        auto relink_ack_encrypted = EncryptionManager::encrypt_aes(encode("confirm-pair-ack"), shared_sec_vec, iv_vec);
        succ_send = this->tcp_soc->send(_fields_to_bytes("CAMREPAIRACK-HSEC", relink_ack_encrypted));
        if (!succ_send) {
            Logger::error("Failed to send relink ack, leaving...");
            return false;
        }
        Logger::info("Re-paired succesfully!");

        return true;

        // // confirm link
        // this->tcp_soc->send(this->_fields_to_bytes("CAMRELINK-HSEC", this->mac_str));
        // Logger::debug("Sent link confirmation.");
        // auto xchng_data = this->handle_key_exchange();
        //
        // if (!std::get<0>(xchng_data)) {
        //     Logger::error("Failed to exchange keys with the server.");
        //     _purge_server();
        //     return false;
        // }
        //
        // Logger::info("Successfuly linked to server!");
        // this->shared_secret = std::get<1>(xchng_data);
        // this->aes_iv = std::get<2>(xchng_data);

        return true;
    }

public:
    Camera(uint8_t mac[6])
    {
        Logger::info("Starting camera setup...");

        Logger::debug("Creating sockets...");
        udp_soc = new SocketUDP();
        tcp_soc = new SocketTCP();
        if (!udp_soc->begin(CAMERA_HEARTBEAT_PORT))
            _on_fatal_error("Failed to start UDP socket!");

        Logger::debug("Setting up tasks...");
        heartbeat_send_task = new Task([this](){ this->send_heartbeat(); }, 1000);
        heartbeat_response_task = new Task([this](){ this->listen_for_heartbeat_response(); }, 1000);
        repair_task = new Task([this](){ this->repair_camera(); }, 1000);
        listen_task = new Task([this](){ this->listen_for_messages(); }, 1000);
        stream_task = new Task([this](){ this->steam_camera(); }, -1);

        this->mac = std::vector<uint8_t>(mac, mac + 6);
        this->mac_str = EthernetManager::mac_bytes_to_string(this->mac.data());

        auto success = camera->init();
        if (!success)
            _on_fatal_error("Failed to initialize camera!");
    }

    void update_server_data()
    {
        write_data_to_eeprom(this->server_data);
    }

    void listen_for_messages() {
        auto raw_bytes = udp_soc->recv();
        if (raw_bytes.empty()) return;
        auto fields = _bytes_to_fields(raw_bytes);
        if (decode(fields[0]) == "CAMUNPAIR-HSEC" && udp_soc->udp_client.remoteIP() == server_data.addr) {
            _purge_server();
            current_state = DISCOVERING;
           Logger::info("Recieved an unpair request, purging server...");
        }
    }

    void repair_camera() {
        this->current_state &= ~REPEAIRING;
        auto success = this->_relink_to_server();
        if (success) this->current_state |= LINKED;
        else {
            this->current_state |= REPEAIRING;
            this->tcp_soc->tcp_client.stop();
        };
    }

    void steam_camera() {
        static unsigned long last_fps_time = 0;
        static uint32_t frame_count = 0;

        if (this->camera->capture_frame(this->curr_frame)) {
            frame_count++;

            auto succ = this->tcp_soc->send(this->_fields_to_bytes(
                "CAMFRAME-HSEC",
                this->curr_frame
            ), DataTransferOptions::WITH_SIZE | DataTransferOptions::ENCRYPT_AES);
            if (!succ)
                Logger::error("Failed to send frame!");
        }

        unsigned long now = millis();
        if (now - last_fps_time >= 1000) {
            Logger::info("FPS: ", frame_count);
            frame_count = 0;
            last_fps_time = now;
        }
    }


    void send_heartbeat()
    {

        udp_soc->send(EthernetManager::get_broadcast_address(),
                      CAMERA_HEARTBEAT_PORT,
                      _fields_to_bytes("CAMPAIR-HSEC", this->mac_str),
                      0);
    }

    void listen_for_heartbeat_response()
    {

        auto raw_bytes = udp_soc->recv();
        if (raw_bytes.empty()) return;
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
            udp_soc->send(udp_soc->udp_client.remoteIP().toString().c_str(),
                      CAMERA_HEARTBEAT_PORT,
                      _fields_to_bytes("BADCODE-HSEC", this->mac_str),
                      0);
            return;
        }

        Logger::info("Valid pairing request, linking...");

        // Actually start server link
        this->server_data.addr = udp_soc->udp_client.remoteIP();
        this->server_data.port = stoi(decode(fields[1]));
        update_server_data();

        this->current_state &= ~DISCOVERING;
        auto success = this->_link_to_server();
        if (success) this->current_state |= LINKED;
        else {
            this->current_state |= DISCOVERING;
            _purge_server();
        }
    }

    bool had_server() {
        // return false;
        return has_eeprom_data();
    }

    void tick()
    {
        // If boot is held, reset is pressed then boot released
        if (digitalRead(BOOT_PIN) == LOW) {
            Logger::info("Clearing EEPROM, discovering...");
            _purge_server();
            current_state = DISCOVERING;
        }

        if (!this->tcp_soc->tcp_client.connected() || current_state & IDLE) {
            if (had_server()) {
                current_state = REPEAIRING;
                if (this->server_data.port == 0) {
                    Logger::info("Getting saved server data...");
                    this->server_data = read_data_from_eeprom();
                    this->tcp_soc->set_aes_data(this->server_data.shared_secret, 32);
                    Logger::info("Got shared secret from storage: ", Logger::get_hex(std::vector<uint8_t>(server_data.shared_secret, server_data.shared_secret+32)));
                }
            }
            else current_state = DISCOVERING;
        }

        if (current_state & DISCOVERING) {
            heartbeat_send_task->tick();
            heartbeat_response_task->tick();
        } else if (current_state & REPEAIRING) {
            repair_task->tick();
        } else if (current_state & LINKED) {
            stream_task->force_run();
            listen_task->tick();
        }


        // If clicked button, purge_server and put on discovering
    }
};

#endif // CAMERA_H
