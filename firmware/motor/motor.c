#include "motor.h"

#include <math.h>
#include <stddef.h>

static float move_toward(float current, float target, float step)
{
    const float difference = target - current;
    if (difference > step) {
        return current + step;
    }
    if (difference < -step) {
        return current - step;
    }
    return target;
}

MotorResult Motor_Init(Motor *motor, const MotorConfig *config)
{
    if (motor == NULL) {
        return MOTOR_ERR_ARGUMENT;
    }
    Motor_Stop(motor, MOTOR_STOP_STANDBY);
    motor->initialized = 0U;
    if (config == NULL) return MOTOR_ERR_ARGUMENT;
    if (config->pwm_period_counts == 0U ||
        (config->polarity != 1 && config->polarity != -1) ||
        !isfinite(config->max_duty_step) ||
        config->max_duty_step <= 0.0f || config->max_duty_step > 1.0f) {
        return MOTOR_ERR_RANGE;
    }

    motor->config = *config;
    motor->target_duty = 0.0f;
    motor->applied_duty = 0.0f;
    motor->stop_mode = MOTOR_STOP_COAST;
    motor->initialized = 1U;
    return MOTOR_OK;
}

MotorResult Motor_SetTargetDuty(Motor *motor, float duty)
{
    if (motor == NULL || motor->initialized == 0U || !isfinite(duty)) {
        Motor_Stop(motor, MOTOR_STOP_STANDBY);
        return MOTOR_ERR_ARGUMENT;
    }
    if (duty < -1.0f || duty > 1.0f) {
        Motor_Stop(motor, MOTOR_STOP_STANDBY);
        return MOTOR_ERR_RANGE;
    }

    motor->target_duty = duty;
    return MOTOR_OK;
}

MotorOutput Motor_Update(Motor *motor)
{
    MotorOutput output = {0, 0U, 0.0f, MOTOR_STOP_STANDBY};
    if (motor == NULL || motor->initialized == 0U) {
        return output;
    }

    motor->applied_duty = move_toward(motor->applied_duty,
                                      motor->target_duty,
                                      motor->config.max_duty_step);
    if (fabsf(motor->applied_duty) < 0.000001f) {
        motor->applied_duty = 0.0f;
    }

    output.applied_duty = motor->applied_duty;
    output.stop_mode = motor->stop_mode;

    if (motor->applied_duty == 0.0f) {
        return output;
    }

    output.direction = (motor->applied_duty > 0.0f ? 1 : -1) *
                       motor->config.polarity;
    const float magnitude = fabsf(motor->applied_duty);
    output.pwm_counts = (uint16_t)(magnitude *
                                   (float)motor->config.pwm_period_counts + 0.5f);
    if (output.pwm_counts > motor->config.pwm_period_counts) {
        output.pwm_counts = motor->config.pwm_period_counts;
    }
    return output;
}

void Motor_Stop(Motor *motor, MotorStopMode mode)
{
    if (motor == NULL) {
        return;
    }
    motor->target_duty = 0.0f;
    motor->applied_duty = 0.0f;
    motor->stop_mode = mode;
}
