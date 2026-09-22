#include "encoder.h"

#include <math.h>
#include <stddef.h>

void Encoder_Init(Encoder *encoder, uint16_t initial_counter, int8_t polarity)
{
    if (encoder == NULL) {
        return;
    }
    encoder->previous_counter = initial_counter;
    encoder->polarity = (polarity < 0) ? -1 : 1;
    encoder->total_counts = 0;
    encoder->initialized = 1U;
}

int32_t Encoder_UpdateCounter(Encoder *encoder, uint16_t counter)
{
    if (encoder == NULL || encoder->initialized == 0U) {
        return 0;
    }

    const int16_t wrapped_delta = (int16_t)(counter - encoder->previous_counter);
    encoder->previous_counter = counter;
    const int32_t signed_delta = (int32_t)wrapped_delta * encoder->polarity;
    encoder->total_counts += signed_delta;
    return signed_delta;
}

int64_t Encoder_GetTotal(const Encoder *encoder)
{
    if (encoder == NULL || encoder->initialized == 0U) {
        return 0;
    }
    return encoder->total_counts;
}

void Encoder_ZeroTotal(Encoder *encoder)
{
    if (encoder != NULL) {
        encoder->total_counts = 0;
    }
}

EncoderSpeedResult Encoder_DeltaToRpm(int32_t delta_count,
                                      float dt_s,
                                      float counts_per_output_rev,
                                      float *rpm_out)
{
    if (rpm_out != NULL) *rpm_out = 0.0f;
    if (rpm_out == NULL || !isfinite(dt_s) || !isfinite(counts_per_output_rev)) {
        return ENCODER_SPEED_ERR_ARGUMENT;
    }
    if (dt_s <= 0.0f || counts_per_output_rev <= 0.0f) {
        return ENCODER_SPEED_ERR_UNCALIBRATED;
    }

    const float denominator = counts_per_output_rev * dt_s;
    if (!isfinite(denominator) || denominator <= 0) return ENCODER_SPEED_ERR_ARGUMENT;
    const float rpm = ((float)delta_count * 60.0f) / denominator;
    if (!isfinite(rpm)) return ENCODER_SPEED_ERR_ARGUMENT;
    *rpm_out = rpm;
    return ENCODER_SPEED_OK;
}
