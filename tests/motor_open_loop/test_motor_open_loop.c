#include "motor.h"

#include <assert.h>
#include <math.h>

int main(void)
{
    Motor motor;
    const MotorConfig config = {
        .pwm_period_counts = 7199U,
        .polarity = 1,
        .max_duty_step = 0.10f,
    };

    assert(Motor_Init(&motor, &config) == MOTOR_OK);
    assert(Motor_SetTargetDuty(&motor, 0.25f) == MOTOR_OK);

    MotorOutput out = Motor_Update(&motor);
    assert(out.direction == 1);
    assert(fabsf(out.applied_duty - 0.10f) < 0.0001f);
    assert(out.pwm_counts == 720U);

    out = Motor_Update(&motor);
    out = Motor_Update(&motor);
    assert(fabsf(out.applied_duty - 0.25f) < 0.0001f);
    assert(out.pwm_counts == 1800U);

    assert(Motor_SetTargetDuty(&motor, -0.25f) == MOTOR_OK);
    for (int i = 0; i < 5; ++i) {
        out = Motor_Update(&motor);
    }
    assert(out.direction == -1);
    assert(fabsf(out.applied_duty + 0.25f) < 0.0001f);

    assert(Motor_SetTargetDuty(&motor, 1.01f) == MOTOR_ERR_RANGE);
    Motor_Stop(&motor, MOTOR_STOP_STANDBY);
    out = Motor_Update(&motor);
    assert(out.direction == 0);
    assert(out.pwm_counts == 0U);
    assert(out.stop_mode == MOTOR_STOP_STANDBY);
    return 0;
}
