#include "encoder.h"

#include <assert.h>
#include <math.h>

int main(void)
{
    float rpm = 0.0f;
    assert(Encoder_DeltaToRpm(20, 0.01f, 400.0f, &rpm) == ENCODER_SPEED_OK);
    assert(fabsf(rpm - 300.0f) < 0.001f);

    assert(Encoder_DeltaToRpm(-10, 0.02f, 400.0f, &rpm) == ENCODER_SPEED_OK);
    assert(fabsf(rpm + 75.0f) < 0.001f);

    assert(Encoder_DeltaToRpm(20, 0.0f, 400.0f, &rpm) ==
           ENCODER_SPEED_ERR_UNCALIBRATED);
    assert(Encoder_DeltaToRpm(20, 0.01f, 0.0f, &rpm) ==
           ENCODER_SPEED_ERR_UNCALIBRATED);
    return 0;
}
