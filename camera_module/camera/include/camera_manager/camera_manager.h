#ifndef CAMERA_MANAGER_H
#define CAMERA_MANAGER_H

#include "esp_camera.h"
#include "Arduino.h"
#include "../logger/logger.h"

class CameraManager {
private:
    CameraManager() {}
    CameraManager(const CameraManager&) = delete;
    CameraManager& operator=(const CameraManager&) = delete;

    bool ran_init = false;
    sensor_t *sensor;
    unsigned long last_capture = 0;

public:
    static camera_config_t get_config() {
        camera_config_t config = {
            .pin_pwdn      = PWDN_GPIO_NUM,
            .pin_reset     = RESET_GPIO_NUM,
            .pin_xclk      = XCLK_GPIO_NUM,
            .pin_sccb_sda  = SIOD_GPIO_NUM,
            .pin_sccb_scl  = SIOC_GPIO_NUM,

            // Data pins (D7–D0 in order required)
            .pin_d7 = Y9_GPIO_NUM, .pin_d6 = Y8_GPIO_NUM, .pin_d5 = Y7_GPIO_NUM, .pin_d4 = Y6_GPIO_NUM,
            .pin_d3 = Y5_GPIO_NUM, .pin_d2 = Y4_GPIO_NUM, .pin_d1 = Y3_GPIO_NUM, .pin_d0 = Y2_GPIO_NUM,

            .pin_vsync = VSYNC_GPIO_NUM,
            .pin_href  = HREF_GPIO_NUM,
            .pin_pclk  = PCLK_GPIO_NUM,

            .xclk_freq_hz  = 30000000,
            .ledc_timer    = LEDC_TIMER_0,
            .ledc_channel  = LEDC_CHANNEL_0,

            .pixel_format  = PIXFORMAT_JPEG,
            .frame_size    = FRAMESIZE_VGA,

            .jpeg_quality  = 12,
            .fb_count      = 3,
            .fb_location   = CAMERA_FB_IN_PSRAM,
            .grab_mode     = CAMERA_GRAB_WHEN_EMPTY
        };


        // if (config.pixel_format == PIXFORMAT_JPEG) {
        //     if (psramFound()) {
        //         config.jpeg_quality = 10;
        //         config.fb_count = 2;
        //         config.grab_mode = CAMERA_GRAB_LATEST;
        //     } else {
        //         // Limit the frame size when PSRAM is not available
        //         config.frame_size = FRAMESIZE_SVGA;
        //         config.fb_location = CAMERA_FB_IN_DRAM;
        //     }
        // }

        return config;
    }

    static CameraManager& getInstance() {
        static CameraManager instance;
        return instance;
    }

    bool init() {
        if (ran_init) return true;

        // Turn camera OFF
        pinMode(PIN__CAM_ENABLE, OUTPUT);
        digitalWrite(PIN__CAM_ENABLE, LOW);

        // Initialize camera
        const auto config = this->get_config();
        esp_camera_deinit();
        delay(200);
        esp_err_t err = esp_camera_init(&config);
        if (err != ESP_OK) {
            Logger::error("Failed to initialized camera! Error code: ", err);
            return false;
        }
        Logger::debug("Camera initialized successfully!");

        // Get sensor and set frame size
        this->sensor = esp_camera_sensor_get();
        if (config.pixel_format == PIXFORMAT_JPEG)
            this->sensor->set_framesize(this->sensor, config.frame_size);

        this->ran_init = true;
        return true;
    }

    bool capture_frame(std::vector<uint8_t>& out_frame) {
        auto delta = millis() - this->last_capture;
        if (delta < (1. / MAX_FPS) * 1000.) {
            // Logger::debug("Skipped frame, lower than FPS. delta: ", delta);
            return false;
        }

        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb) {
            Logger::error("Failed to capture a frame!");
            return false;
        }

        out_frame.resize(fb->len);
        memcpy(out_frame.data(), fb->buf, fb->len);

        this->last_capture = millis();
        esp_camera_fb_return(fb);

        return true;
    }
};

#endif // CAMERA_MANAGER_H
