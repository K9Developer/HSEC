#include <esp_camera.h>
class Camera {
    private:
        camera_config_t config;
        sensor_t *sensor;

        camera_fb_t* get_frame() {
            camera_fb_t *fb = esp_camera_fb_get();
            if (!fb) {
                Logger::error("Camera capture failed");
                return nullptr;
            }
            return fb;
        }
        
    public:

        Camera(camera_config_t config, sensor_t *sensor) {
            this->config = config;
            this->sensor = sensor;
        }

        ~Camera() {
            esp_camera_deinit();
        }

        uint8_t* capture_jpg() {
            camera_fb_t *fb = get_frame();
            if (fb == nullptr) {
                return nullptr;
            }

            uint8_t *jpg_buf = (uint8_t *)malloc(fb->len);
            if (!jpg_buf) {
                Logger::error("Failed to allocate memory for JPEG buffer");
                esp_camera_fb_return(fb);
                return nullptr;
            }

            memcpy(jpg_buf, fb->buf, fb->len);
            esp_camera_fb_return(fb);
            return jpg_buf;
        }

};