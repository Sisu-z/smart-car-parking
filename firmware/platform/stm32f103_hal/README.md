# STM32F103 HAL 集成说明

状态：`[BUILD-VERIFIED][UNVERIFIED-ON-HARDWARE]`。2026-09-22 新增独立候选工程；下方双路/舵机表仍是未来方案，不是本轮全部实现。

## 本轮真正可构建的内容

`bench_main.c`：只包含 Motor A、Encoder E1、USART1 和单电机安全层。引用已有 `test01` 的 HAL/CMSIS、启动文件、系统文件和链接脚本，不改原工程，不创建重复副本。不存在舵机输出、第二电机、ADC、CAN、RTOS 或真实 RDK 链路。

在工作台根目录运行：

```sh
cmake -S firmware/platform/stm32f103_hal -B build/stm32 -DCMAKE_TOOLCHAIN_FILE=arm-toolchain.cmake -DBASELINE=/absolute/path/to/test01
cmake --build build/stm32 -j 4
```

产物 `build/stm32/single_motor_bench.elf`。迁移环境用 `-DBASELINE=已有HAL工程路径` 指定依赖。最终构建/体积日志见 `results/step_07.log`；未烧录、未测波形或实机负载。

### 上板限制，必须先看

- 固件默认 `hardware_approved=0`，所有 MOTOR:ENABLE 都被拒绝；`counts_per_rev=0/max_rpm=0`，速度闭环也不可启用。示例 duty_limit=0.10 只是软件配置，不代表该电机/驱动电流已安全。
- 默认 PI 增益为 0，禁止复制电脑仿真的增益到实机。确认硬件、供电、波形和 raw count 后逐步标定。
- 板级映射使用 `01_hardware_source_of_truth.md` §1 的厂家参考，并未确认实物 A/E1 对应或实际正方向。
- 本工程 stop/disable/fault 均请求 **coast**：AIN1=AIN2=低、PWMA=高，TIM3 CCR4=ARR+1；与 PWM=0 刹车、STBY=低待机不同。[来源：本地 `【WHEELTEC】TB6612电机驱动附送资料_V3.2_2026.07.25/6.芯片手册/TB6612FNG芯片手册.pdf` p.4，H-SW Control Function。]
- STBY 参考接法常高，软件不能真正关闭它；不声称具备独立硬件急停、过流/堵转保护或独立看门狗。断电能力与电流观察必须由台架提供。
- RX 中断只入有界队列，前台解析；TX 使用中断，繁忙时跳过遥测，不阻塞控制。SysTick 超期门控不能替代独立硬件看门狗；优先级、耗时和所有引脚必须实测。
- 本轮不主动连接 ST-LINK、不烧录、不访问串口。联合舵机工程继续按 DEC-009 单独复审。

## 为什么现在不直接写入 `test01`

`test01` 当前使用 TIM3_CH1/PA6、PSC=71、ARR=19999 产生 50 Hz 舵机 PWM。D153 电机参考需要 TIM3_CH3/PB0 和 CH4/PB1、PSC=0、ARR=7199 产生 10 kHz PWM。同一 TIM3 的全部通道共享基准周期，所以两套配置不能同时存在。

## 暂定 CubeMX 资源分配（DEC-009）

| 功能 | 暂定资源 | 配置 |
|---|---|---|
| Servo | TIM1_CH1 / PA8 | 1 MHz 计数，ARR=19999，50 Hz；初期只使用已经跑过的 1000～2000 us |
| Motor B PWM | TIM3_CH3 / PB0 | 72 MHz 下 PSC=0、ARR=7199，得到 10 kHz |
| Motor A PWM | TIM3_CH4 / PB1 | 与 Motor B 共用定时器基频 |
| Motor direction | PB12/PB13/PB14/PB15 | GPIO 输出；A/B 对应关系按硬件事实库 |
| Encoder E2 | TIM2_CH1/CH2 / PA0/PA1 | Encoder Mode；ARR=65535；滤波值由实测决定 |
| Encoder E1 | TIM4_CH1/CH2 / PB6/PB7 | Encoder Mode；ARR=65535；滤波值由实测决定 |
| Voltage ADC | ADC1_IN6 / PA6 | PWM 迁移后可选；必须标定板级分压 |
| Debug UART | USART1 / PA9/PA10 | 115200 8N1 |
| Control scheduler | 初期由 1 ms SysTick 派生 10 ms flag | 禁止阻塞；进入 PI 前必须测量 GPIO 周期 |

D153 参考引脚的硬件来源见 `01_hardware_source_of_truth.md` 第 1 节。Servo 迁移与调度方式属于项目方案，不是厂家事实。

## HAL 适配实现

现行实现见 `bench_main.c` 的 `coast/apply`：消费 MotorOutput、只驱动 CH4/Motor A，默认 coast。已删除早期未实现停止分支的伪代码，防止它被误当成现行程序。未来 Motor B 必须使用 CH3 并另做验证，不能复制厂家 A/B 写反函数。

## 未来舵机 + 电机联合工程的集成门槛

以下不作为本轮独立单电机候选的前置条件。

1. 为 `test01` 创建受保护的副本或分支。
2. 只迁移 Servo timer/pin；构建、烧录并重复已有 Servo/VOFA+ 测试。
3. 加入 TIM3 Motor PWM/GPIO，电机保持断开；验证 10 kHz 和通道映射。
4. 只接一台 Motor，按 B01 测试。
5. 只加一个 Encoder，计数通过后再加第二路。
6. 最后才接入 speed/PID 模块。

## 嵌入式库注意事项

`telemetry.c` 为方便 Host/VOFA+ 阶段阅读，使用了浮点 `snprintf`。部分 newlib 配置需要显式开启浮点格式化，并会增加 Flash 占用。集成时先检查链接结果与体积；如果成本不可接受，只替换为缩放整数 formatter，不改变 Telemetry 数据对象和协议语义。
