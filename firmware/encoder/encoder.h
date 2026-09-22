#ifndef SMART_CAR_ENCODER_H
#define SMART_CAR_ENCODER_H

#include <stdint.h>

typedef struct {
    uint16_t previous_counter;
    int8_t polarity;
    int64_t total_counts;
    uint8_t initialized;
} Encoder;

typedef enum {
    ENCODER_SPEED_OK = 0,
    ENCODER_SPEED_ERR_ARGUMENT,
    ENCODER_SPEED_ERR_UNCALIBRATED
} EncoderSpeedResult;

void Encoder_Init(Encoder *encoder, uint16_t initial_counter, int8_t polarity);
int32_t Encoder_UpdateCounter(Encoder *encoder, uint16_t counter);
int64_t Encoder_GetTotal(const Encoder *encoder);
void Encoder_ZeroTotal(Encoder *encoder);

EncoderSpeedResult Encoder_DeltaToRpm(int32_t delta_count,
                                      float dt_s,
                                      float counts_per_output_rev,
                                      float *rpm_out);

#endif
