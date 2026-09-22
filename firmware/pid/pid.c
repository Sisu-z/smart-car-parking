#include "pid.h"

#include <math.h>
#include <stddef.h>

static float clampf(float value, float minimum, float maximum)
{
    if (value < minimum) {
        return minimum;
    }
    if (value > maximum) {
        return maximum;
    }
    return value;
}

PidResult PID_Init(PidController *pid, const PidConfig *config)
{
    if (pid == NULL) {
        return PID_ERR_ARGUMENT;
    }
    pid->initialized = 0U;
    PID_Reset(pid);
    if (config == NULL) return PID_ERR_ARGUMENT;
    if (!isfinite(config->kp) || !isfinite(config->ki) ||
        !isfinite(config->kd) || !isfinite(config->output_min) ||
        !isfinite(config->output_max) || !isfinite(config->integral_min) ||
        !isfinite(config->integral_max) || config->kp < 0.0f ||
        config->ki < 0.0f || config->kd < 0.0f ||
        config->output_min >= config->output_max ||
        config->integral_min > config->integral_max) {
        return PID_ERR_RANGE;
    }

    pid->config = *config;
    pid->initialized = 1U;
    PID_Reset(pid);
    return PID_OK;
}

PidResult PID_Update(PidController *pid,
                     float target,
                     float measured,
                     float dt_s,
                     float *output)
{
    if (output != NULL) *output = 0.0f;
    if (pid == NULL || output == NULL || pid->initialized == 0U ||
        !isfinite(target) || !isfinite(measured) ||
        !isfinite(dt_s) || dt_s <= 0.0f) {
        return PID_ERR_ARGUMENT;
    }

    const float error = target - measured;
    const float proportional = pid->config.kp * error;
    float derivative = 0.0f;
    if (pid->has_previous_measurement != 0U && pid->config.kd != 0.0f) {
        derivative = -pid->config.kd *
                     (measured - pid->previous_measurement) / dt_s;
    }

    const float next_integral = pid->integral_term + pid->config.ki * error * dt_s;
    if (!isfinite(error) || !isfinite(proportional) || !isfinite(derivative) ||
        !isfinite(next_integral)) {
        PID_Reset(pid);
        return PID_ERR_RANGE;
    }
    const float candidate_integral = clampf(
        next_integral,
        pid->config.integral_min,
        pid->config.integral_max);
    const float candidate_unclamped = proportional + candidate_integral + derivative;
    if (!isfinite(candidate_unclamped)) {
        PID_Reset(pid);
        return PID_ERR_RANGE;
    }

    const uint8_t pushes_high = (candidate_unclamped > pid->config.output_max &&
                                 error > 0.0f);
    const uint8_t pushes_low = (candidate_unclamped < pid->config.output_min &&
                                error < 0.0f);
    if (pushes_high == 0U && pushes_low == 0U) {
        pid->integral_term = candidate_integral;
    }

    const float unclamped = proportional + pid->integral_term + derivative;
    *output = clampf(unclamped, pid->config.output_min, pid->config.output_max);
    pid->previous_measurement = measured;
    pid->has_previous_measurement = 1U;
    return PID_OK;
}

void PID_Reset(PidController *pid)
{
    if (pid == NULL) {
        return;
    }
    pid->integral_term = 0.0f;
    pid->previous_measurement = 0.0f;
    pid->has_previous_measurement = 0U;
}
