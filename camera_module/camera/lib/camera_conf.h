#include <Arduino.h>
#include "esp_camera.h"
#include "constants.h"

static camera_config_t get_config() {
    static camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = PIN__Y2_GPIO_NUM;
    config.pin_d1 = PIN__Y3_GPIO_NUM;
    config.pin_d2 = PIN__Y4_GPIO_NUM;
    config.pin_d3 = PIN__Y5_GPIO_NUM;
    config.pin_d4 = PIN__Y6_GPIO_NUM;
    config.pin_d5 = PIN__Y7_GPIO_NUM;
    config.pin_d6 = PIN__Y8_GPIO_NUM;
    config.pin_d7 = PIN__Y9_GPIO_NUM;
    config.pin_xclk = PIN__XCLK_GPIO_NUM;
    config.pin_pclk = PIN__PCLK_GPIO_NUM;
    config.pin_vsync = PIN__VSYNC_GPIO_NUM;
    config.pin_href = PIN__HREF_GPIO_NUM;
    config.pin_sccb_sda = PIN__SIOD_GPIO_NUM;
    config.pin_sccb_scl = PIN__SIOC_GPIO_NUM;
    config.pin_pwdn = PIN__PWDN_GPIO_NUM;
    config.pin_reset = PIN__RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.frame_size = FRAMESIZE_UXGA;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    return config;
}