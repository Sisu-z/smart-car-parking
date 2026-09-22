#include "telemetry.h"

#include <stdio.h>

TelemetryResult Telemetry_FormatCsv(const TelemetryFrame *frame,
                                    char *buffer,
                                    size_t capacity)
{
    if (frame == NULL || buffer == NULL || capacity == 0U) {
        return TELEMETRY_ERR_ARGUMENT;
    }

    const int length = snprintf(buffer, capacity,
                                "T,%lu,%u,%.3f,%.3f,%.3f,%.5f,%.5f,%ld,%lu\r\n",
                                (unsigned long)frame->timestamp_ms,
                                (unsigned int)frame->enabled,
                                (double)frame->target_rpm,
                                (double)frame->actual_rpm,
                                (double)frame->error_rpm,
                                (double)frame->controller_output,
                                (double)frame->pwm_duty,
                                (long)frame->encoder_delta,
                                (unsigned long)frame->fault_flags);
    if (length < 0 || (size_t)length >= capacity) {
        if (capacity > 0U) {
            buffer[0] = '\0';
        }
        return TELEMETRY_ERR_CAPACITY;
    }
    return TELEMETRY_OK;
}
