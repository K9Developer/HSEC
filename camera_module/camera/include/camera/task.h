#ifndef TASK_H
#define TASK_H

#include <functional>
#include <Arduino.h>

class Task {
private:
    std::function<void()> func;
    unsigned long interval;
    unsigned long last_run;

public:
    Task(std::function<void()> f, unsigned long interval_ms)
        : func(f), interval(interval_ms), last_run(0) {}

    void tick() {
        unsigned long current_time = millis();
        if (current_time - last_run >= interval) {
            last_run = current_time;
            func();
        }
    }

    void force_run() {
        last_run = 0;
        func();
    }
};

#endif // TASK_H