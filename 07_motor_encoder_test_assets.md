# 07 Motor / Encoder / PI 测试资产

2026-09-22 更新：最新完整运行记录为 `results/verification.json`：7 项 C 测试、9 项 Python 测试、7 个泊车/故障场景；独立 ARM ELF 已链接、未上板。新增 `bench` 和行接收测试。下方 2026-09-21 数量是历史基线，不是最近结果。

## 已交付资产

| 资产 | 路径 | 当前状态 | 能证明 | 不能证明 |
|---|---|---|---|---|
| Motor 核心 | `firmware/motor/motor.c/.h` | `[IMPLEMENTED][HOST-TESTED]` | duty 范围、极性、slew、stop、PWM count 换算 | GPIO 真值表、物理方向、电流安全 |
| Encoder 核心 | `firmware/encoder/encoder.c/.h` | `[IMPLEMENTED][HOST-TESTED]` | 16 位回绕、方向、累计、count→RPM 数学 | 编码器接线、噪声、解码倍频、每圈计数 |
| PID 核心 | `firmware/pid/pid.c/.h` | `[IMPLEMENTED][HOST-TESTED]` | 有边界 P/PI/PID、条件积分、复位 | 实机稳定增益 |
| Command Parser | `firmware/command/command.c/.h` | `[IMPLEMENTED][HOST-TESTED]` | 命令识别、语法/范围拒绝 | UART buffer、超时、硬件安全范围 |
| Telemetry Formatter | `firmware/telemetry/telemetry.c/.h` | `[IMPLEMENTED][HOST-TESTED]` | 固定 CSV 格式、容量检查 | 非阻塞 UART/DMA 传输 |
| 单电机 HAL 候选 | `firmware/platform/stm32f103_hal/bench_main.c` | `[BUILD-VERIFIED][UNVERIFIED-ON-HARDWARE]` | 完整链接、只读复用已有 HAL | 烧录、波形、物理停机与电流 |

2026-09-21 验证结果：

- 使用 AppleClang 和 `-Wall -Wextra -Werror -pedantic`，5/5 主机测试通过。
- 五个模块源文件均使用 STM32 GNU Tools `arm-none-eabi-gcc 14.3.1` 编译为 Cortex-M3 对象文件，警告按错误处理。
- 两项结果都不是烧录或实机验证。

## 测试程序

### `tests/motor_open_loop`

主机端验证初始化、duty 范围、每次更新 0.1 的 slew、正反方向、PWM count 和 standby 请求。以下只是协议顺序示意，绝非已确认安全的实机参数；新候选默认禁用，审核解锁后才能按 B01～B03 逐项试验：

```text
MOTOR:ENABLE
DUTY:0.05
DUTY:0.00
MOTOR:DISABLE
# 等待编码器连续静止（不能把此注释直接发给 parser）
MOTOR:ENABLE
DUTY:-0.05
MOTOR:STOP
```

正方向和停止行为没有实测通过前，不得发送负方向命令。

运动命令必须按小于配置 timeout 的间隔重发；上述行不能作为带长时间人工停顿的串口脚本。STOP 后仍需要 DISABLE 才能清除既有故障。未标定 RPM 会输出 nan，速度模式拒绝使能。

### `tests/encoder_count`

主机端覆盖 16 位正反回绕和 polarity。上板时先禁用电机、手转轮子，记录 CNT 和 delta；此时保持 `counts_per_output_rev` 未设置。

### `tests/encoder_speed`

主机端验证速度公式，并拒绝 0/无效标定值。只有 B05 已记录每圈计数、10 ms 已实测后，输出才是有效 RPM。

### `tests/speed_pi`

主机端在一个刻意简化的一阶对象上闭环，检查输出边界、积分和 reset。它只是控制器回归测试，不是电机模型，也不能提供实机增益。

## 构建与运行

```sh
cmake -S tests -B tests/build
cmake --build tests/build
ctest --test-dir tests/build --output-on-failure
```

## 上板前的 CubeMX 配置

按照 `firmware/platform/stm32f103_hal/README.md` 的暂定方案，在 `test01` 保护副本中复审：

- TIM3 CH3/CH4：10 kHz Motor PWM。
- PB12～PB15：四路方向 GPIO。
- TIM2/TIM4：E2/E1 Encoder Mode。
- 舵机需要同时工作时，必须迁出 TIM3。
- 保留 USART1 给 VOFA+。
- 使用 10 ms 非阻塞调度，并用 GPIO 验证实际周期。

## 上板验收顺序

1. 无警告构建，核对生成的 pin map。
2. 电机断开：测 PWMA/PWMB、方向脚和调度 GPIO。
3. 驱动板上电但不接电机：测逻辑电平、电压轨和 stop state。
4. 只接一台电机，轮子架空并观察电流：B01～B03。
5. 手转编码器：B04～B05。
6. 电机 + 编码器开环遥测：B06～B08。
7. 低目标 P-only，再进入 PI：B09～B11。

每个门槛都必须产生实验记录；失败时停止，不得用猜测常量掩盖问题。
