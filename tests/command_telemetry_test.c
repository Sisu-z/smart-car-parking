#include "command.h"
#include "telemetry.h"

#include <assert.h>
#include <string.h>

int main(void)
{
    RobotCommand command;
    assert(Command_ParseLine("MOTOR:ENABLE", &command) == COMMAND_OK);
    assert(command.type == COMMAND_MOTOR_ENABLE);
    assert(Command_ParseLine("DUTY:-0.25", &command) == COMMAND_OK);
    assert(command.type == COMMAND_SET_DUTY);
    assert(Command_ParseLine("DUTY:2", &command) == COMMAND_ERR_RANGE);
    assert(Command_ParseLine("KP:nan", &command) == COMMAND_ERR_SYNTAX);
    assert(Command_ParseLine("S:1700", &command) == COMMAND_OK);
    assert(command.type == COMMAND_SET_SERVO_US);
    assert(Command_ParseLine("UNKNOWN:1", &command) == COMMAND_ERR_UNKNOWN);

    const TelemetryFrame frame = {
        .timestamp_ms = 123U,
        .enabled = 1U,
        .target_rpm = 100.0f,
        .actual_rpm = 90.0f,
        .error_rpm = 10.0f,
        .controller_output = 0.25f,
        .pwm_duty = 0.25f,
        .encoder_delta = 12,
        .fault_flags = 0U,
    };
    char buffer[160];
    assert(Telemetry_FormatCsv(&frame, buffer, sizeof(buffer)) == TELEMETRY_OK);
    assert(strstr(buffer, "T,123,1,100.000,90.000,10.000") == buffer);

    char too_small[4];
    assert(Telemetry_FormatCsv(&frame, too_small, sizeof(too_small)) ==
           TELEMETRY_ERR_CAPACITY);
    return 0;
}
