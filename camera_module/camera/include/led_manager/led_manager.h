#ifndef LED_MANAGER_H
#define LED_MANAGER_H

#include "Arduino.h"
#include "../logger/logger.h"
#include <Adafruit_NeoPixel.h>

enum Effect {
    FADE_IN_OUT,
    BLINK,
    STATIC,
    OFF
};

struct Color {
    uint8_t R;
    uint8_t G;
    uint8_t B;
    uint8_t A;

    constexpr bool operator==(const Color& other) const noexcept {
        return R == other.R &&
               G == other.G &&
               B == other.B &&
               A == other.A;
    }
    constexpr bool operator!=(const Color& other) const noexcept {
        return !(*this == other);
    }
};

struct LEDJob {
    Color clr{};
    Effect fx = Effect::OFF;
    unsigned long time_into_cycle{};

    int in_interval{};
    int bridge_interval{};
    int out_interval{};

    unsigned long start_cycle_time{};

    constexpr LEDJob(Color c,
                     Effect e,
                     unsigned long tic,
                     int in_i,
                     int br_i,
                     int out_i,
                     unsigned long start_t) noexcept
        : clr(c),
          fx(e),
          time_into_cycle(tic),
          in_interval(in_i),
          bridge_interval(br_i),
          out_interval(out_i),
          start_cycle_time(start_t) {}
};

class LEDManager {
private:
    LEDManager() {}
    LEDManager(const LEDManager&) = delete;
    LEDManager& operator=(const LEDManager&) = delete;

    TaskHandle_t* led_task_handle;
    bool ran_init = false;
    Adafruit_NeoPixel* led;
    LEDJob currentJob {
        {0,0,0,0},
        Effect::OFF,
        0,0,0,0,0
    };

    static void ledTask(void *pv) {
        LEDManager &self = getInstance();
        const TickType_t period = pdMS_TO_TICKS(10);   // ≈100 Hz
        for (;;) {
            self.tick();
        }
    }

    Color get_color_fade_in_out() {
        const int32_t fadeIn  = currentJob.in_interval;
        const int32_t hold = currentJob.bridge_interval;
        const int32_t fadeOut = currentJob.out_interval;

        const int32_t cycleLen = fadeIn + hold + fadeOut + hold;

        if (cycleLen <= 0) return Color{0, 0, 0, 0};

        int32_t t = currentJob.time_into_cycle % cycleLen;
        float ratio = 0.0f;                    // 0 = off, 1 = full clr

        if (t < fadeIn && fadeIn > 0) ratio = static_cast<float>(t) / fadeIn;
        else if (t < fadeIn + hold) ratio = 1.0f;
        else if (t < fadeIn + hold + fadeOut && fadeOut > 0) {
            int32_t tOut = t - (fadeIn + hold);
            ratio = 1.0f - static_cast<float>(tOut) / fadeOut;
        } else ratio = 0.0f;

        return Color{
            static_cast<uint8_t>(currentJob.clr.R * ratio),
            static_cast<uint8_t>(currentJob.clr.G * ratio),
            static_cast<uint8_t>(currentJob.clr.B * ratio),
            static_cast<uint8_t>(currentJob.clr.A * ratio)
        };
    }

    Color get_color_blink() {
        const int32_t onLen  = currentJob.in_interval  > 0 ? currentJob.in_interval : 500;
        const int32_t offLen = currentJob.out_interval > 0 ? currentJob.out_interval : 500;
        const int32_t cycleLen = onLen + offLen;

        if (cycleLen <= 0) return Color{0, 0, 0, 0};
        int32_t t = currentJob.time_into_cycle % cycleLen;
        bool onPhase = (t < onLen);

        return onPhase
               ? currentJob.clr
               : Color{0, 0, 0, 0};
    }
public:
    static LEDManager& getInstance() {
        static LEDManager instance;
        return instance;
    }

    void init(int16_t pin) {
        if (ran_init) return;
        ran_init = true;

        led = new Adafruit_NeoPixel(1, pin, NEO_GRB + NEO_KHZ800);
        led->begin();
        led->setBrightness(50);
        led->show();

        xTaskCreatePinnedToCore(
            ledTask,
            "LEDTask",
            2048,
            nullptr,
            1,
            led_task_handle,
            0
        );
    }

    void start_led(Color clr, Effect fx, int in_interval = 300, int bridge_interval=1, int out_interval = 300) {
        if (currentJob.clr == clr && currentJob.fx == fx) return;

        if (!led) {
            Logger::warning("Failed to start LED effect, didnt INIT yet.");
            return;
        }

        currentJob = LEDJob {
            clr,
            fx,
            0,
            in_interval,
            bridge_interval,
            out_interval,
            millis()
        };
    };
    void end_led() {
        currentJob = LEDJob {
            Color {0,0,0, 0},
            OFF,
            0,
            0,
            0,
            0,
            millis()
        };
    };

    void tick() {
        if (!led) return;
        currentJob.time_into_cycle = millis() - currentJob.start_cycle_time;

        Color clr {0,0,0, 0};
        switch (currentJob.fx) {
            case Effect::OFF:
                clr = {0,0,0, 0};
                break;
            case Effect::BLINK:
                clr = get_color_blink();
                break;
            case Effect::STATIC:
                clr = currentJob.clr;
                break;
            case Effect::FADE_IN_OUT:
                clr = get_color_fade_in_out();
        }


        led->setPixelColor(0, Adafruit_NeoPixel::Color(clr.R, clr.G, clr.B));
        led->setBrightness(clr.A);
        led->show();
    }
};

#endif // LED_MANAGER_H
