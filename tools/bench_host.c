/* 主机虚拟台架：复用 MCU 的同一 Bench，不连接任何物理串口。
 * 测试输入：T,<ms>,<uint16_counter> 或 C,<ms>,<V0命令>。 */
#include "bench.h"
#include <stdio.h>
#include <string.h>
int main(void) {
    Bench b;
    const BenchConfig c={.duty_limit=.3f,.max_rpm=100,.counts_per_rev=1000,
        .timeout_ms=300,.max_step_ms=50,.quiet_ms=200,.hardware_approved=1,
        .motor={7199,1,.05f},.pid={.005f,.01f,0,-.3f,.3f,-.3f,.3f}};
    if (!Bench_Init(&b,&c,0,0)) return 1;
    char line[256], csv[256];
    while(fgets(line,sizeof(line),stdin)) {
        unsigned long ms=0; unsigned int count=0; int offset=0;
        if(sscanf(line,"T,%lu,%u",&ms,&count)==2) {
            (void)Bench_Tick(&b,(uint32_t)ms,(uint16_t)count);
            if(Telemetry_FormatCsv(&b.frame,csv,sizeof(csv))==TELEMETRY_OK) fputs(csv,stdout);
        } else if(sscanf(line,"C,%lu,%n",&ms,&offset)==1 && offset>0) {
            line[strcspn(line,"\r\n")]=0;
            int ok=Bench_Command(&b,line+offset,(uint32_t)ms);
            printf("A,%lu,%d,%lu\n",ms,ok,(unsigned long)b.frame.fault_flags);
        } else { Bench_Fault(&b,BENCH_INPUT); puts("E,invalid_test_input"); }
        fflush(stdout);
    }
    return 0;
}
