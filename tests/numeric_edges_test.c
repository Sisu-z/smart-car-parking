#include "motor.h"
#include "pid.h"
#include "encoder.h"
#include <assert.h>
#include <math.h>
#include <float.h>
#include <stddef.h>
int main(void) {
    Motor m; MotorConfig mc={7199,1,1};
    assert(Motor_Init(&m,&mc)==MOTOR_OK);
    assert(Motor_SetTargetDuty(&m,.5f)==MOTOR_OK);
    assert(Motor_Update(&m).pwm_counts>0);
    assert(Motor_SetTargetDuty(&m,NAN)!=MOTOR_OK);
    assert(Motor_Update(&m).pwm_counts==0);
    assert(Motor_Init(&m,NULL)!=MOTOR_OK && !m.initialized);
    PidController p; PidConfig pc={1,1,0,-1,1,-1,1}; float o=5;
    assert(PID_Init(&p,&pc)==PID_OK);
    assert(PID_Update(&p,NAN,0,.01f,&o)!=PID_OK && o==0);
    o=5; assert(PID_Update(&p,FLT_MAX,-FLT_MAX,.01f,&o)!=PID_OK && o==0);
    assert(PID_Init(&p,NULL)!=PID_OK && !p.initialized);
    float rpm=5;
    assert(Encoder_DeltaToRpm(1,0,100,&rpm)!=ENCODER_SPEED_OK && rpm==0);
    assert(Encoder_DeltaToRpm(100,FLT_MIN,FLT_MIN,&rpm)!=ENCODER_SPEED_OK && rpm==0);
    assert(Encoder_DeltaToRpm(100,FLT_MAX,FLT_MAX,&rpm)!=ENCODER_SPEED_OK && rpm==0);
    return 0;
}
