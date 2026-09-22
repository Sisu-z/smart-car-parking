#include "bench.h"
#include "line_receiver.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

static BenchConfig config(void) {
    BenchConfig c = {.duty_limit=.25f, .max_rpm=100, .counts_per_rev=1000,
        .timeout_ms=300, .max_step_ms=50, .quiet_ms=100, .hardware_approved=1,
        .motor={7199,1,.1f}, .pid={.01f,.02f,0,-1,1,-1,1}};
    return c;
}
static void warm(Bench *b, uint32_t base) {
    for (uint32_t t=10; t<=100; t+=10) (void)Bench_Tick(b,base+t,0);
}
int main(void) {
    Bench b; BenchConfig c=config();
    assert(Bench_Init(&b,&c,0,0));
    assert(!Bench_Command(&b,"DUTY:0.2",0));
    assert(!Bench_Command(&b,"MOTOR:ENABLE",0));
    warm(&b,0);
    assert(Bench_Command(&b,"MOTOR:ENABLE",100));
    assert(Bench_Command(&b,"DUTY:0.2",100));
    assert(Bench_Tick(&b,110,0).pwm_counts>0);
    assert(Bench_Command(&b,"GET:STATUS",110));
    for (uint32_t t=120;t<=400;t+=10) (void)Bench_Tick(&b,t,0);
    assert(!b.enabled && b.frame.fault_flags==BENCH_TIMEOUT);
    assert(!Bench_Command(&b,"MOTOR:ENABLE",400));
    assert(!Bench_Command(&b,"DUTY:0.2",400));
    assert(Bench_Command(&b,"MOTOR:DISABLE",400));
    warm(&b,400);
    assert(Bench_Command(&b,"MOTOR:ENABLE",500));
    assert(Bench_Tick(&b,510,0).pwm_counts==0); /* 无旧目标恢复。 */
    assert(Bench_Command(&b,"DUTY:0.2",510));
    assert(!Bench_Command(&b,"DUTY:-0.2",510));
    assert(b.frame.fault_flags & BENCH_REVERSAL);
    assert(Bench_Tick(&b,520,0).pwm_counts==0);
    assert(Bench_Command(&b,"MOTOR:DISABLE",520)); warm(&b,520);
    assert(Bench_Command(&b,"MOTOR:ENABLE",620));
    assert(!Bench_Command(&b,"DUTY:nan",620));
    assert(b.frame.fault_flags & BENCH_INPUT);
    c.counts_per_rev=0; assert(Bench_Init(&b,&c,0,0)); warm(&b,0);
    assert(isnan(b.frame.actual_rpm));
    assert(Bench_Command(&b,"MOTOR:ENABLE",100));
    assert(!Bench_Command(&b,"SPEED_RPM:10",100));
    assert(b.frame.fault_flags & BENCH_CALIBRATION);
    c=config(); c.hardware_approved=0;
    assert(Bench_Init(&b,&c,0,0)); warm(&b,0);
    assert(!Bench_Command(&b,"MOTOR:ENABLE",100));
    assert(b.frame.fault_flags & BENCH_PLATFORM);
    c=config(); uint32_t base=UINT32_MAX-50;
    assert(Bench_Init(&b,&c,base,0)); warm(&b,base);
    assert(Bench_Command(&b,"MOTOR:ENABLE",base+100));
    assert(Bench_Command(&b,"DUTY:0.2",base+100));
    assert(Bench_Tick(&b,base+110,0).pwm_counts>0);
    assert(Bench_Tick(&b,base+200,0).pwm_counts==0);
    assert(b.frame.fault_flags & BENCH_TIMING);
    /* 运动中的计数不断更新 quiet 时间，不允许重新使能。 */
    assert(Bench_Init(&b,&c,0,0));
    for(uint32_t t=10;t<=200;t+=10) (void)Bench_Tick(&b,t,(uint16_t)t);
    assert(!Bench_Command(&b,"MOTOR:ENABLE",200));
    LineReceiver r={0};
    for(int i=0;i<1000;i++) (void)LineReceiver_Push(&r,'X');
    assert(LineReceiver_Push(&r,'\n')==0);
    const char *s="DUTY:0.1\r\n"; int ready=0;
    for(size_t i=0;i<strlen(s);i++) ready=LineReceiver_Push(&r,(unsigned char)s[i]);
    assert(ready==1 && !strcmp(r.data,"DUTY:0.1"));
    assert(LineReceiver_Push(&r,0)==-1);
    assert(LineReceiver_Push(&r,'\n')==0);
    return 0;
}
