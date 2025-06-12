#ifndef LOGGER_H
#define LOGGER_H

#include <Arduino.h>
#include <vector>
#include <cctype>
#include <string>
#include "constants.h"
#include <sstream>
#include <iomanip>

static bool serialInitialized = false;

class Logger {
public:
    template<typename... Args> static void debug  (Args&&... args) { log("DEBUG",   std::forward<Args>(args)...); }
    template<typename... Args> static void info   (Args&&... args) { log("INFO",    std::forward<Args>(args)...); }
    template<typename... Args> static void warning(Args&&... args) { log("WARNING", std::forward<Args>(args)...); }
    template<typename... Args> static void error  (Args&&... args) { log("ERROR",   std::forward<Args>(args)...); }

    static std::string get_hex(const std::vector<uint8_t>& data) {
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (uint8_t b : data) oss << std::setw(2) << static_cast<int>(b);
        return oss.str();
    }

    static void hex_dump(const std::vector<uint8_t>& data,
                        std::size_t bytesPerLine = 16)
    {
        ensureSerial();

        const char* HEX_ = "0123456789ABCDEF";

        for (std::size_t i = 0; i < data.size(); ++i) {
            uint8_t byte = static_cast<uint8_t>(data[i]);

            Serial.print(HEX_[byte >> 4]);
            Serial.print(HEX_[byte & 0x0F]);
            Serial.print(' ');

            bool endOfLine = (i + 1) % bytesPerLine == 0 || i + 1 == data.size();
            if (endOfLine) {
                std::size_t pad = bytesPerLine - ((i + 1) % bytesPerLine);
                if (pad != bytesPerLine) {
                    for (std::size_t k = 0; k < pad; ++k) Serial.print(F("   "));
                }

                Serial.print(F(" | "));
                std::size_t lineStart = (i / bytesPerLine) * bytesPerLine;
                std::size_t lineEnd   = i + 1;

                for (std::size_t j = lineStart; j < lineEnd; ++j) {
                    char c = data[j];
                    Serial.print(isprint(static_cast<uint8_t>(c)) ? c : '.');
                }
                Serial.println();
            }
        }
    }

private:
    template<typename... Args>
    static void log(const char* level, Args&&... args)
    {
        ensureSerial();

        Serial.print('['); Serial.print(level); Serial.print(F("] "));

        using swallow = int[];
        (void)swallow{0, (printArg(std::forward<Args>(args)), 0)...};

        Serial.println();
    }

    static void ensureSerial()
    {
        if (!serialInitialized) {
            Serial.begin(SERIAL_BAUD_RATE);
            while (!Serial) { delay(10); }
            serialInitialized = true;
        }
    }

    static void printArg(const String&        s) { Serial.print(s); }
    static void printArg(const char*          s) { Serial.print(s); }
    static void printArg(const std::string&   s) { Serial.print(s.c_str()); }

    template<typename T>
    static void printArg(const T& v)              { Serial.print(v); }
};

#endif /* LOGGER_H */