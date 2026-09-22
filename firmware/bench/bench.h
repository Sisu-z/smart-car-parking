#ifndef SMART_CAR_BENCH_H
#define SMART_CAR_BENCH_H
#include "motor.h"
#include "encoder.h"
#include "pid.h"
#include "command.h"
#include "telemetry.h"

/* 单电机台架门控；参数是项目配置，不是厂家规格。 */
enum {
    BENCH_TIMEOUT = 1U, BENCH_INPUT = 2U, BENCH_TIMING = 4U,
    BENCH_CALIBRATION = 8U, BENCH_REVERSAL = 16U, BENCH_PLATFORM = 32U
};
typedef struct {
    float duty_limit, max_rpm, counts_per_rev;
    uint32_t timeout_ms, max_step_ms, quiet_ms;
    uint8_t hardware_approved;
    MotorConfig motor;
    PidConfig pid;
} BenchConfig;
typedef struct {
    BenchConfig config;
    Motor motor;
    Encoder encoder;
    PidController pid;
    TelemetryFrame frame;
    uint32_t last_tick_ms, last_command_ms, quiet_since_ms;
    int8_t last_direction;
    uint8_t enabled, speed_mode, initialized;
    float requested_duty, target_rpm;
} Bench;
int Bench_Init(Bench *, const BenchConfig *, uint32_t now_ms, uint16_t counter);
int Bench_Command(Bench *, const char *line, uint32_t now_ms);
MotorOutput Bench_Tick(Bench *, uint32_t now_ms, uint16_t counter);
void Bench_Fault(Bench *, uint32_t flags);
#endif
