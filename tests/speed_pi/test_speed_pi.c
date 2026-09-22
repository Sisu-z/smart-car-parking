#include "pid.h"

#include <assert.h>
#include <math.h>

int main(void)
{
    PidController pi;
    const PidConfig config = {
        .kp = 0.012f,
        .ki = 0.040f,
        .kd = 0.0f,
        .output_min = -1.0f,
        .output_max = 1.0f,
        .integral_min = -0.8f,
        .integral_max = 0.8f,
    };
    assert(PID_Init(&pi, &config) == PID_OK);

    const float dt_s = 0.01f;
    const float target_rpm = 100.0f;
    float measured_rpm = 0.0f;
    float output = 0.0f;

    for (int i = 0; i < 1200; ++i) {
        assert(PID_Update(&pi, target_rpm, measured_rpm, dt_s, &output) == PID_OK);
        assert(output >= -1.0f && output <= 1.0f);
        const float plant_target_rpm = output * 140.0f;
        measured_rpm += (plant_target_rpm - measured_rpm) * 0.04f;
    }
    assert(fabsf(measured_rpm - target_rpm) < 2.0f);

    for (int i = 0; i < 500; ++i) {
        assert(PID_Update(&pi, 10000.0f, measured_rpm, dt_s, &output) == PID_OK);
        assert(output <= 1.0f);
    }
    assert(pi.integral_term <= config.integral_max);

    PID_Reset(&pi);
    assert(pi.integral_term == 0.0f);
    assert(pi.has_previous_measurement == 0U);
    return 0;
}
