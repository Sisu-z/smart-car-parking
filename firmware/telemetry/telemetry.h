#ifndef SMART_CAR_TELEMETRY_H
#define SMART_CAR_TELEMETRY_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t timestamp_ms;
    uint8_t enabled;
    float target_rpm;
    float actual_rpm;
    float error_rpm;
    float controller_output;
    float pwm_duty;
    int32_t encoder_delta;
    uint32_t fault_flags;
} TelemetryFrame;

typedef enum {
    TELEMETRY_OK = 0,
    TELEMETRY_ERR_ARGUMENT,
    TELEMETRY_ERR_CAPACITY
} TelemetryResult;

TelemetryResult Telemetry_FormatCsv(const TelemetryFrame *frame,
                                    char *buffer,
                                    size_t capacity);

#endif
