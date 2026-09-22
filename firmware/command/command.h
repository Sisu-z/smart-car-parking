#ifndef SMART_CAR_COMMAND_H
#define SMART_CAR_COMMAND_H

#include <stdint.h>

typedef enum {
    COMMAND_NONE = 0,
    COMMAND_MOTOR_ENABLE,
    COMMAND_MOTOR_DISABLE,
    COMMAND_MOTOR_STOP,
    COMMAND_SET_DUTY,
    COMMAND_SET_SPEED_RPM,
    COMMAND_SET_KP,
    COMMAND_SET_KI,
    COMMAND_SET_KD,
    COMMAND_GET_STATUS,
    COMMAND_SET_SERVO_US
} CommandType;

typedef enum {
    COMMAND_OK = 0,
    COMMAND_ERR_ARGUMENT,
    COMMAND_ERR_SYNTAX,
    COMMAND_ERR_RANGE,
    COMMAND_ERR_UNKNOWN
} CommandResult;

typedef struct {
    CommandType type;
    float value;
} RobotCommand;

CommandResult Command_ParseLine(const char *line, RobotCommand *out);

#endif
