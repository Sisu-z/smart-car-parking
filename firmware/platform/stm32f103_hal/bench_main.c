/* [UNVERIFIED] 独立单 Motor A 候选工程，不包含舵机，不修改 test01。
 * 引脚依据 01_hardware_source_of_truth.md §1：PB1=PWMA，PB14/15=AIN1/2，
 * PB6/7=E1。上电波形、电平和 A/E1 实物对应关系仍须复审。
 * STBY 参考接线接常高，本程序不声称实现芯片 standby 或硬件急停。
 */
#include "stm32f1xx_hal.h"
#include "bench.h"
#include "line_receiver.h"
#include <string.h>

/* 必须在硬件审核后人工填写；默认固件无法使能电机。 */
static const BenchConfig board = {
    .hardware_approved=0, .duty_limit=.10f, .max_rpm=0, .counts_per_rev=0,
    .timeout_ms=300, .max_step_ms=30, .quiet_ms=200,
    .motor={7199,1,.01f}, .pid={0,0,0,-.10f,.10f,-.10f,.10f}
};
static Bench bench;
static TIM_HandleTypeDef pwm, enc;
static UART_HandleTypeDef uart;
static uint8_t rx_byte;
static volatile uint16_t head, tail;
static volatile uint8_t rx_overflow;
static uint8_t rx_queue[128];
static char tx_buffer[256];
static volatile uint32_t last_control;

/* COAST：IN1=IN2=0、PWM=1；PWM=0 不当作高阻停车。
 * 数据手册真值表 TB6612FNG p.4。CCR=ARR+1 表示恒高。
 * 板子接错或 STBY 常高时，软件不构成独立断能保障。 */
static void coast(void) {
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_14|GPIO_PIN_15, GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&pwm,TIM_CHANNEL_4,7200U);
}
static void apply(const MotorOutput *o) {
    if (!o->direction || !o->pwm_counts) { coast(); return; }
    __HAL_TIM_SET_COMPARE(&pwm,TIM_CHANNEL_4,0U);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_14,o->direction>0?GPIO_PIN_SET:GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_15,o->direction<0?GPIO_PIN_SET:GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&pwm,TIM_CHANNEL_4,o->pwm_counts);
}
void Error_Handler(void) {
    if(pwm.Instance==TIM3) coast();
    __disable_irq();
    while(1) { /* 需要人工断电检查。 */ }
}
static void check(HAL_StatusTypeDef s) { if(s!=HAL_OK) Error_Handler(); }
void SysTick_Handler(void) {
    HAL_IncTick();
    /* 独立于前台解析/格式化的超期输出门控，但不是独立硬件看门狗。 */
    if (pwm.Instance==TIM3 && HAL_GetTick()-last_control>board.max_step_ms) coast();
}
void USART1_IRQHandler(void) { HAL_UART_IRQHandler(&uart); }
void HardFault_Handler(void) { Error_Handler(); }
void MemManage_Handler(void) { Error_Handler(); }
void BusFault_Handler(void) { Error_Handler(); }
void UsageFault_Handler(void) { Error_Handler(); }
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *u) {
    if(u!=&uart) return;
    uint16_t next=(head+1U)%sizeof(rx_queue);
    if(next==tail) rx_overflow=1;
    else { rx_queue[head]=rx_byte; head=next; }
    if(HAL_UART_Receive_IT(&uart,&rx_byte,1)!=HAL_OK) rx_overflow=1;
}
void HAL_UART_ErrorCallback(UART_HandleTypeDef *u) {
    if(u==&uart) rx_overflow=1;
}
static void init_board(void) {
    HAL_Init();
    /* 复用 test01 SystemClock_Config 的 HSE/PLL/APB 配置。 */
    RCC_OscInitTypeDef osc={0}; RCC_ClkInitTypeDef clk={0};
    osc.OscillatorType=RCC_OSCILLATORTYPE_HSE; osc.HSEState=RCC_HSE_ON;
    osc.HSEPredivValue=RCC_HSE_PREDIV_DIV1; osc.HSIState=RCC_HSI_ON;
    osc.PLL.PLLState=RCC_PLL_ON; osc.PLL.PLLSource=RCC_PLLSOURCE_HSE;
    osc.PLL.PLLMUL=RCC_PLL_MUL9; check(HAL_RCC_OscConfig(&osc));
    clk.ClockType=RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK; clk.AHBCLKDivider=RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider=RCC_HCLK_DIV2; clk.APB2CLKDivider=RCC_HCLK_DIV1;
    check(HAL_RCC_ClockConfig(&clk,FLASH_LATENCY_2));
    __HAL_RCC_AFIO_CLK_ENABLE(); __HAL_RCC_GPIOA_CLK_ENABLE(); __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_TIM3_CLK_ENABLE(); __HAL_RCC_TIM4_CLK_ENABLE(); __HAL_RCC_USART1_CLK_ENABLE();
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_14|GPIO_PIN_15,GPIO_PIN_RESET);
    GPIO_InitTypeDef io={.Pin=GPIO_PIN_14|GPIO_PIN_15,.Mode=GPIO_MODE_OUTPUT_PP,.Speed=GPIO_SPEED_FREQ_LOW};
    HAL_GPIO_Init(GPIOB,&io);
    io.Pin=GPIO_PIN_1; io.Mode=GPIO_MODE_AF_PP; HAL_GPIO_Init(GPIOB,&io);
    pwm.Instance=TIM3; pwm.Init.Prescaler=0; pwm.Init.CounterMode=TIM_COUNTERMODE_UP;
    pwm.Init.Period=7199; pwm.Init.ClockDivision=TIM_CLOCKDIVISION_DIV1;
    check(HAL_TIM_PWM_Init(&pwm));
    TIM_OC_InitTypeDef oc={.OCMode=TIM_OCMODE_PWM1,.Pulse=7200,.OCPolarity=TIM_OCPOLARITY_HIGH,.OCFastMode=TIM_OCFAST_DISABLE};
    check(HAL_TIM_PWM_ConfigChannel(&pwm,&oc,TIM_CHANNEL_4));
    check(HAL_TIM_PWM_Start(&pwm,TIM_CHANNEL_4)); coast();
    io.Pin=GPIO_PIN_6|GPIO_PIN_7; io.Mode=GPIO_MODE_INPUT; io.Pull=GPIO_NOPULL; HAL_GPIO_Init(GPIOB,&io);
    enc.Instance=TIM4; enc.Init.Period=65535; enc.Init.CounterMode=TIM_COUNTERMODE_UP;
    enc.Init.ClockDivision=TIM_CLOCKDIVISION_DIV1;
    TIM_Encoder_InitTypeDef ec={.EncoderMode=TIM_ENCODERMODE_TI12,
        .IC1Polarity=TIM_ICPOLARITY_RISING,.IC1Selection=TIM_ICSELECTION_DIRECTTI,.IC1Prescaler=TIM_ICPSC_DIV1,
        .IC2Polarity=TIM_ICPOLARITY_RISING,.IC2Selection=TIM_ICSELECTION_DIRECTTI,.IC2Prescaler=TIM_ICPSC_DIV1};
    check(HAL_TIM_Encoder_Init(&enc,&ec)); check(HAL_TIM_Encoder_Start(&enc,TIM_CHANNEL_ALL));
    io.Pin=GPIO_PIN_9; io.Mode=GPIO_MODE_AF_PP; io.Speed=GPIO_SPEED_FREQ_HIGH; HAL_GPIO_Init(GPIOA,&io);
    io.Pin=GPIO_PIN_10; io.Mode=GPIO_MODE_INPUT; HAL_GPIO_Init(GPIOA,&io);
    uart.Instance=USART1; uart.Init.BaudRate=115200; uart.Init.WordLength=UART_WORDLENGTH_8B;
    uart.Init.StopBits=UART_STOPBITS_1; uart.Init.Parity=UART_PARITY_NONE; uart.Init.Mode=UART_MODE_TX_RX;
    uart.Init.HwFlowCtl=UART_HWCONTROL_NONE; uart.Init.OverSampling=UART_OVERSAMPLING_16;
    check(HAL_UART_Init(&uart));
    HAL_NVIC_SetPriority(SysTick_IRQn,0,0); HAL_NVIC_SetPriority(USART1_IRQn,2,0); HAL_NVIC_EnableIRQ(USART1_IRQn);
    check(HAL_UART_Receive_IT(&uart,&rx_byte,1));
}
int main(void) {
    init_board();
    uint32_t now=HAL_GetTick(); last_control=now;
    if(!Bench_Init(&bench,&board,now,(uint16_t)__HAL_TIM_GET_COUNTER(&enc))) Error_Handler();
    uint32_t last_tx=now; LineReceiver receiver={0};
    while(1) {
        now=HAL_GetTick();
        if(rx_overflow) {
            __disable_irq(); tail=head; rx_overflow=0; __enable_irq();
            receiver.used=0; receiver.dropping=1;
            Bench_Fault(&bench,BENCH_INPUT); coast();
            (void)HAL_UART_AbortReceive(&uart);
            if(HAL_UART_Receive_IT(&uart,&rx_byte,1)!=HAL_OK) rx_overflow=1;
        }
        if(now-last_control>=10U) {
            MotorOutput out=Bench_Tick(&bench,now,(uint16_t)__HAL_TIM_GET_COUNTER(&enc));
            last_control=now; apply(&out);
        }
        for(unsigned int n=0; n<32 && tail!=head; n++) {
            unsigned char byte=rx_queue[tail]; tail=(tail+1U)%sizeof(rx_queue);
            int result=LineReceiver_Push(&receiver,byte);
            if(result<0) { Bench_Fault(&bench,BENCH_INPUT); coast(); }
            if(result>0) { (void)Bench_Command(&bench,receiver.data,HAL_GetTick());
                if(!bench.enabled) coast(); }
        }
        if(now-last_tx>=50U && uart.gState==HAL_UART_STATE_READY) {
            if(Telemetry_FormatCsv(&bench.frame,tx_buffer,sizeof(tx_buffer))==TELEMETRY_OK)
                (void)HAL_UART_Transmit_IT(&uart,(uint8_t*)tx_buffer,(uint16_t)strlen(tx_buffer));
            last_tx=now;
        }
    }
}
