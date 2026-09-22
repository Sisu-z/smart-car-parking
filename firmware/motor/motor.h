#ifndef SMART_CAR_MOTOR_H
#define SMART_CAR_MOTOR_H

#include <stdint.h>

typedef enum {
    MOTOR_OK = 0,
    MOTOR_ERR_ARGUMENT,
    MOTOR_ERR_RANGE
} MotorResult;

typedef enum {
    MOTOR_STOP_COAST = 0,
    MOTOR_STOP_BRAKE,
    MOTOR_STOP_STANDBY
} MotorStopMode;

typedef struct {
    uint16_t pwm_period_counts;
    int8_t polarity;
    float max_duty_step;
} MotorConfig;

typedef struct {
    MotorConfig config;
    float target_duty;
    float applied_duty;
    MotorStopMode stop_mode;
    uint8_t initialized;
} Motor;

typedef struct {
    int8_t direction;
    uint16_t pwm_counts;
    float applied_duty;
    MotorStopMode stop_mode;
} MotorOutput;

MotorResult Motor_Init(Motor *motor, const MotorConfig *config);
MotorResult Motor_SetTargetDuty(Motor *motor, float duty);
MotorOutput Motor_Update(Motor *motor);
void Motor_Stop(Motor *motor, MotorStopMode mode);

#endif
