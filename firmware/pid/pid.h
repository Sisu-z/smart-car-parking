#ifndef SMART_CAR_PID_H
#define SMART_CAR_PID_H

#include <stdint.h>

typedef enum {
    PID_OK = 0,
    PID_ERR_ARGUMENT,
    PID_ERR_RANGE
} PidResult;

typedef struct {
    float kp;
    float ki;
    float kd;
    float output_min;
    float output_max;
    float integral_min;
    float integral_max;
} PidConfig;

typedef struct {
    PidConfig config;
    float integral_term;
    float previous_measurement;
    uint8_t has_previous_measurement;
    uint8_t initialized;
} PidController;

PidResult PID_Init(PidController *pid, const PidConfig *config);
PidResult PID_Update(PidController *pid,
                     float target,
                     float measured,
                     float dt_s,
                     float *output);
void PID_Reset(PidController *pid);

#endif
