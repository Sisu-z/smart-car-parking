#include "command.h"

#include <errno.h>
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

static CommandResult parse_float_exact(const char *text, float *value)
{
    if (text == NULL || value == NULL || *text == '\0') {
        return COMMAND_ERR_SYNTAX;
    }

    errno = 0;
    char *end = NULL;
    const float parsed = strtof(text, &end);
    if (errno == ERANGE || end == text || *end != '\0' || !isfinite(parsed)) {
        return COMMAND_ERR_SYNTAX;
    }
    *value = parsed;
    return COMMAND_OK;
}

static CommandResult parse_value_command(const char *line,
                                         const char *prefix,
                                         CommandType type,
                                         float minimum,
                                         float maximum,
                                         RobotCommand *out)
{
    const size_t prefix_length = strlen(prefix);
    if (strncmp(line, prefix, prefix_length) != 0) {
        return COMMAND_ERR_UNKNOWN;
    }

    float value = 0.0f;
    const CommandResult result = parse_float_exact(line + prefix_length, &value);
    if (result != COMMAND_OK) {
        return result;
    }
    if (value < minimum || value > maximum) {
        return COMMAND_ERR_RANGE;
    }

    out->type = type;
    out->value = value;
    return COMMAND_OK;
}

CommandResult Command_ParseLine(const char *line, RobotCommand *out)
{
    if (line == NULL || out == NULL) {
        return COMMAND_ERR_ARGUMENT;
    }
    out->type = COMMAND_NONE;
    out->value = 0.0f;

    if (strcmp(line, "MOTOR:ENABLE") == 0) {
        out->type = COMMAND_MOTOR_ENABLE;
        return COMMAND_OK;
    }
    if (strcmp(line, "MOTOR:DISABLE") == 0) {
        out->type = COMMAND_MOTOR_DISABLE;
        return COMMAND_OK;
    }
    if (strcmp(line, "MOTOR:STOP") == 0) {
        out->type = COMMAND_MOTOR_STOP;
        return COMMAND_OK;
    }
    if (strcmp(line, "GET:STATUS") == 0) {
        out->type = COMMAND_GET_STATUS;
        return COMMAND_OK;
    }

    CommandResult result = parse_value_command(line, "DUTY:", COMMAND_SET_DUTY,
                                               -1.0f, 1.0f, out);
    if (result != COMMAND_ERR_UNKNOWN) {
        return result;
    }
    result = parse_value_command(line, "SPEED_RPM:", COMMAND_SET_SPEED_RPM,
                                 -100000.0f, 100000.0f, out);
    if (result != COMMAND_ERR_UNKNOWN) {
        return result;
    }
    result = parse_value_command(line, "KP:", COMMAND_SET_KP,
                                 0.0f, 100000.0f, out);
    if (result != COMMAND_ERR_UNKNOWN) {
        return result;
    }
    result = parse_value_command(line, "KI:", COMMAND_SET_KI,
                                 0.0f, 100000.0f, out);
    if (result != COMMAND_ERR_UNKNOWN) {
        return result;
    }
    result = parse_value_command(line, "KD:", COMMAND_SET_KD,
                                 0.0f, 100000.0f, out);
    if (result != COMMAND_ERR_UNKNOWN) {
        return result;
    }
    result = parse_value_command(line, "S:", COMMAND_SET_SERVO_US,
                                 1000.0f, 2000.0f, out);
    if (result != COMMAND_ERR_UNKNOWN) {
        return result;
    }

    return COMMAND_ERR_UNKNOWN;
}
