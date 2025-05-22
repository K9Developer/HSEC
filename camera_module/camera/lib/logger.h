#include "constants.h"
#include <string>
#include <Arduino.h>

class Logger {
    private:
    public:
        static void begin() {
            Serial.begin(BAUD_RATE);
            Serial.println("Logger initialized");
        }

        static void info(const std::string& message) {
            Serial.print("[INFO] ");
            Serial.println(message.c_str());
        }

        static void warn(const std::string& message) {
            Serial.print("[WARN] ");
            Serial.println(message.c_str());
        }

        static void error(const std::string& message) {
            Serial.print("[ERROR] ");
            Serial.println(message.c_str());
        }
};