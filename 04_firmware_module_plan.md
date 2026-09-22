# 04 可复用固件模块规划

目标是建立可逐个验证、可替换硬件映射、不会绑死最终车型的 STM32F103C8T6 + HAL 固件骨架。以下是**软件设计建议**；其中硬件映射只采用已引用的厂家资料，未确认项保持 `UNKNOWN`。

引用约定：来源根目录为 `<HARDWARE_SOURCE_ROOT>`；文中的“用户手册”指 `【WHEELTEC】TB6612电机驱动附送资料_V3.2_2026.07.25/1.用户手册与使用教程/电机驱动模块使用手册—TB6612(2025.08.27).pdf`；“GMR HAL”与“GMR 标准库”分别指同资料包 `4.例程源码/1.STM32F1例程/2.D153B（双路驱动带稳压版）例程/D153B_GMR编码器HAL库例程_2026.8.20.zip` 和同目录 `D153B_GMR编码器标准库例程_2025.7.7.zip`。压缩包引用随后给出包内文件与行号。

## 1. 设计边界

- 不设计最终整车行为、底盘运动学、PCB 或 3D 结构。
- 控制算法不直接访问 HAL 句柄；HAL 只留在板级适配层。
- “原始计数 → 物理速度 → 控制输出”分层，禁止把 `counts/窗口` 冒充 RPM。
- 中断做定时采样和最小控制计算；格式化、串口发送、命令解析放非中断上下文。
- 左右电机方向差异、编码器方向差异、PWM 通道和板版本集中配置。
- 所有输出都受状态机、限幅和故障门控；通信中断不能留下持续驱动命令。

## 2. 推荐目录

```text
firmware/
├── Core/                      CubeMX 生成区
├── app/
│   ├── app_main.c
│   ├── control_scheduler.c
│   └── system_state.c
├── bsp/
│   ├── board_config.h
│   ├── motor_hw_stm32.c
│   ├── encoder_hw_stm32.c
│   ├── uart_hw_stm32.c
│   └── power_monitor_hw_stm32.c
├── modules/
│   ├── motor_driver.c
│   ├── encoder.c
│   ├── speed_estimator.c
│   ├── pi_controller.c
│   ├── command.c
│   ├── telemetry.c
│   ├── safety.c
│   └── fault_log.c
├── tests/
│   ├── test_motor_openloop.c
│   ├── test_encoder_count.c
│   ├── test_speed_estimator.c
│   ├── test_pi_controller.c
│   └── test_command_parser.c
└── docs/
    ├── pinmap.md
    ├── calibration.md
    └── bringup_runs/
```

目录名是建议，不要求覆盖已有舵机工程。

## 3. 板级配置 `board_config`

集中保存：

```c
typedef struct {
    MotorHw left_motor;
    MotorHw right_motor;
    EncoderHw left_encoder;
    EncoderHw right_encoder;
    int8_t motor_polarity[2];
    int8_t encoder_polarity[2];
    uint32_t pwm_frequency_hz;
    uint16_t pwm_period_counts;
    float control_period_s;
    float counts_per_output_rev[2];
    float adc_divider_ratio;
    DriverBoardRevision driver_revision;
} BoardConfig;
```

初始硬件映射：Motor A 的 PWMA=PB1/TIM3_CH4，方向 PB14/PB15；Motor B 的 PWMB=PB0/TIM3_CH3，方向 PB13/PB12；编码器 E1=PB6/PB7(TIM4)，E2=PA0/PA1(TIM2)；电压 ADC=PA6。[来源：用户手册 p.17；接线 PNG；GMR HAL `.ioc:66-88,162-182`]

配置项状态：

| 配置项 | 初值 | 证据/状态 |
|---|---:|---|
| `pwm_frequency_hz` | 10000 | 厂家推荐 10 kHz。[来源：用户手册 p.11] |
| `control_period_s` | 0.010 | `PROPOSED`；需示波器实测。厂家例程实际 0.005 s，不可照抄。[来源：GMR HAL `tim.c:46-70`] |
| `adc_divider_ratio` | 11.0 | 板级说明/原理图为 1/11。[来源：用户手册 p.8；D153C V1.1 原理图 p.1] |
| `counts_per_output_rev` | `NAN/UNSET` | `UNKNOWN`；必须通过精确数据页和实测填入 |
| `motor_polarity` | `UNSET` | 装配相关，B02/B05 标定 |
| `encoder_polarity` | `UNSET` | 接线/安装相关，B04/B05 标定 |
| `driver_revision` | `UNSET` | 通过丝印/照片确认 V1.0 或 V1.1 |

若关键 `UNSET` 未清除，闭环模式拒绝启动。

## 4. 模块职责与最小 API

### 4.1 `motor_driver`

职责：把带符号的归一化命令映射为方向 GPIO 与正确 PWM 通道；明确区分 drive、coast、short brake、standby。

```c
void motor_init(const MotorConfig *cfg);
void motor_set_normalized(MotorId id, float command); // [-1, 1]
void motor_coast(MotorId id);
void motor_brake(MotorId id);
void motor_disable_all(void);
MotorOutput motor_get_output(MotorId id);
```

必须包含范围检查、斜坡限制和 0 命令语义。不可直接复制厂家 HAL `Set_PWM`，因为它的 A/B CCR 映射与接线和标准库版冲突。[来源：GMR HAL `Core/Src/tim.c:423-445`；GMR 标准库 `HAREWER/PWM/pwm.c:46-70`；用户手册 p.17]

### 4.2 `encoder`

职责：读取硬件计数器、计算有符号增量、处理回绕、应用极性，不计算控制输出。

```c
void encoder_init(const EncoderConfig *cfg);
EncoderDelta encoder_sample(EncoderId id);
int64_t encoder_total(EncoderId id);
void encoder_zero(EncoderId id);
```

厂家 HAL 的“强制转 `short` 后清 CNT”可作为思路，但并发、回绕和采样时刻要在新实现中写清楚。[来源：GMR HAL `Core/Src/tim.c:410-420`]

### 4.3 `speed_estimator`

职责：用真实 `dt` 和 `counts_per_output_rev` 生成 RPM/rad/s，选择性滤波，并暴露有效性状态。

```c
SpeedSample speed_update(int32_t delta_count, float dt_s,
                         float counts_per_output_rev);
void speed_reset(void);
```

输入比例未标定时返回 `invalid`，不能输出伪 RPM。厂家手册承认示例只反馈计数、没有完成速度换算。[来源：用户手册 p.23]

### 4.4 `pi_controller`

职责：P/PI 算法、输出限幅、条件积分或 back-calculation、模式切换复位；单位使用 RPM 或 rad/s。

```c
void pi_init(PIController *c, const PIConfig *cfg);
float pi_step(PIController *c, float target, float measured, float dt_s);
void pi_reset(PIController *c);
```

厂家增量式 PI 可作为公式参考，但其默认目标、增益、周期和原始计数单位不能复用。[来源：GMR HAL `Core/Src/main.c:49-51`、`Core/Src/tim.c:452-481`]

### 4.5 `command`

职责：接收串口命令，校验格式与范围，更新时间戳，再交给状态机；不直接写 GPIO/PWM。

建议最小命令：

```text
MODE OPEN|SPEED|DISABLED
MOTOR <L|R|BOTH> <normalized_value>
SPEED <L|R|BOTH> <rpm>
STOP
GET STATUS
SET KP <value>
SET KI <value>
```

必须拒绝 NaN、越界值、缺字段和未知命令；命令超时进入安全状态。具体超时时间需由测试确定，标为 `PROPOSED`。

### 4.6 `telemetry`

职责：从控制快照生成 VOFA+/CSV 帧，不在 ISR 内阻塞发送。

```c
void telemetry_publish(const TelemetryFrame *frame);
void telemetry_service(void); // 主循环或 DMA
```

厂家示例在定时器 ISR 内调用忙等 `printf`，该结构禁止进入主工程。[来源：GMR HAL `Core/Src/main.c:168-207`、`Core/Src/usart.c:42-47`]

### 4.7 `safety` 与 `system_state`

状态建议：

```text
BOOT → SELF_TEST → DISABLED → OPEN_LOOP_TEST → SPEED_LOOP
                     ↑               ↓              ↓
                     └──────────── FAULT ←──────────┘
```

故障至少覆盖：配置未标定、命令超时、ADC 电压越界、编码器失联/不合理跳变、控制周期超时和用户急停。电压阈值在电源方案确定前保持 `UNKNOWN`，不得凭经验写死。

### 4.8 `power_monitor`

职责：读取 PA6 ADC、应用分压与校准系数、滤波并上报；不直接假定电池类型或欠压阈值。D153 板载检测网络标称 1/11 分压。[来源：用户手册 p.8；D153C V1.1 原理图 p.1]

厂家 `ADC_Average` 每个样本 `HAL_Delay(5)`，不适合实时主循环；采样应改为非阻塞调度或 DMA。[来源：GMR HAL `Core/Src/adc.c:126-160`]

## 5. 调度与数据流

```text
TIM1 fixed tick
  ├─ encoder_sample()
  ├─ speed_update()
  ├─ safety_fast_check()
  ├─ pi_step()           [仅 SPEED_LOOP]
  ├─ motor_set...()
  └─ publish snapshot

主循环 / DMA 服务
  ├─ command_parse()
  ├─ telemetry_service()
  ├─ power_monitor_service()
  ├─ safety_slow_check()
  └─ fault_log_flush()
```

控制 tick 必须校验 `htim->Instance`，不能假定所有周期回调都来自 TIM1。厂家回调未作此检查。[来源：GMR HAL `Core/Src/main.c:168-209`]

## 6. 测试资产

| 测试 | 是否需要实物 | 验证内容 | 通过门槛 |
|---|---|---|---|
| `test_motor_logic` | 否/逻辑分析仪更佳 | 命令符号→GPIO/PWM 通道、0 命令、限幅 | A/B 映射与配置一致；边界输入全通过 |
| `test_motor_openloop` | 是 | 单电机起停、正反、占空比扫描 | 满足 03/B01-B03 |
| `test_encoder_math` | 否 | 16 位回绕、正负增量、累计值 | 边界样例无跳变 |
| `test_encoder_count` | 是 | AB 相、方向、每圈计数 | 满足 03/B04-B05 |
| `test_speed_estimator` | 可先离线 | 计数/dt/RPM 换算、无效配置 | 已知向量误差为 0 或浮点容差内 |
| `test_scheduler` | 示波器/逻辑分析仪 | 10 ms 周期、抖动、超时 | 实测记录符合项目阈值 |
| `test_command_parser` | 否 | 正常、缺字段、越界、乱码、超时 | 非法输入不能驱动电机 |
| `test_telemetry_load` | 是 | 断开/拥塞串口不扰动控制 | tick 周期不因遥测变化 |
| `test_pi_offline` | 否 | 饱和、积分冻结、复位 | 输出有界、恢复符合预期 |
| `test_pi_hardware` | 是 | P→PI 阶跃与扰动 | 满足 03/B09-B11 |

## 7. 实施顺序与复用判定

1. 从当前 C8T6 CubeMX/HAL 工程重新生成基础外设；只拿厂家 `.ioc` 做对照。
2. 先完成 `board_config + motor_driver + test_motor_openloop`。
3. 再完成 `encoder + test_encoder_count`。
4. 标定计数比例后做 `speed_estimator + telemetry`。
5. 加 `system_state + safety + command timeout` 后才允许 PI。
6. 最后做 `pi_controller`、anti-windup 和可选前馈。

可直接采用的是**硬件真值表、已核对的引脚映射和外设目标**；可借鉴的是定时器编码器模式与增量 PI 公式；必须重写的是 motor API、周期调度、速度物理量、命令、遥测、安全状态和闭环实现。

## 8. 版本化参数记录

每个参数保存来源与验证状态：

```text
name: counts_per_output_rev_left
value: <number>
unit: count/rev
source: bench_test B05 / motor datasheet
hardware_revision: D153C V?.?
motor_sku: MG513XP28_12V
date: YYYY-MM-DD
status: PROVISIONAL | VERIFIED
```

这样后续即使更换电机、编码器、驱动板版本或底盘，控制模块不变，只替换板级映射和标定数据。

## 9. 当前已落地资产与集成边界

以下模块已在本工作区实现，并于 2026-09-21 通过 AppleClang 主机测试；这只证明纯 C 行为，不等于上板验证：

| 模块 | 文件 | 已测试内容 | 仍未验证 |
|---|---|---|---|
| motor | `firmware/motor/motor.c/.h` | 输入范围、极性、slew、PWM count、stop | HAL 真值表、实际方向、电流 |
| encoder/speed | `firmware/encoder/encoder.c/.h` | 16 位回绕、方向、累计、RPM 公式与未标定拒绝 | A/B 波形、滤波、counts/rev |
| pid | `firmware/pid/pid.c/.h` | 输出限幅、条件积分、reset、简单仿真闭环 | 实机增益与动态稳定性 |
| command | `firmware/command/command.c/.h` | 命令识别、数值语法/范围拒绝、旧 `S:` 命令 | UART 缓冲、超时状态机 |
| telemetry | `firmware/telemetry/telemetry.c/.h` | 固定 CSV 格式、缓冲区容量 | 非阻塞 UART/DMA 发送 |

历史基线：2026-09-21 为 5/5 主机测试和 Cortex-M3 对象编译。2026-09-22 已扩展为 7 项 C 测试、9 项 Python 测试、7 个泊车/故障场景，且独立单电机工程完成 ARM ELF 链接；结果以 `results/verification.json` 为准。均不代表烧录或实机通过。

### 对当前 `test01` 的处理

`test01` 保持不变。其 servo 位于 PA6/TIM3_CH1、50 Hz，而 motor 参考需要 TIM3 CH3/CH4、10 kHz；同一 TIM3 不能提供两种 PSC/ARR。先在受保护的集成副本中验证 DEC-009 的资源重分配，再把 `firmware/` 作为 CMake user sources 引入。详见 `firmware/platform/stm32f103_hal/README.md`。

### 现在实现与只预留

- 现在实现：motor、encoder/speed、pid、command、telemetry 的纯逻辑和薄 HAL 适配。
- 已新增：单电机 bench 安全层、离线 vision 算子适配和实验 parking 闭环；不是正式整车集成。
- 下一阶段实现：dual-wheel vehicle API、power monitor、真实感知接入。
- 只预留：实车 odometry、正式 RDK transport、出库与恢复。
- 暂不创建：ROS2 包、RTOS task、完整 parking/arm 代码。
