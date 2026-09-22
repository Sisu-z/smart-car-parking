#include "encoder.h"

#include <assert.h>

int main(void)
{
    Encoder encoder;
    Encoder_Init(&encoder, 65530U, 1);
    assert(Encoder_UpdateCounter(&encoder, 2U) == 8);
    assert(Encoder_UpdateCounter(&encoder, 65530U) == -8);
    assert(Encoder_GetTotal(&encoder) == 0);

    Encoder_Init(&encoder, 100U, -1);
    assert(Encoder_UpdateCounter(&encoder, 120U) == -20);
    assert(Encoder_GetTotal(&encoder) == -20);
    Encoder_ZeroTotal(&encoder);
    assert(Encoder_GetTotal(&encoder) == 0);
    return 0;
}
