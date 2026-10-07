# 2026-09-19 舵机调试：GPIO → PWM → 舵机控制

> 状态说明：本文件是 2026-09-19 学习/实操阶段记录，保留当时的工具链、舵机称呼与参数口径；不自动升级为当前整车硬件事实或最终配置。

## 1. 开发环境与工具链

最终采用：Mac + VS Code + STM32CubeMX + STM32 官方 VS Code 插件 + ST-LINK。

- CubeMX：芯片、GPIO、时钟、Timer、UART 等硬件配置并生成初始化代码。
- VS Code：业务代码、Build、Debug。
- GNU Tools for STM32：C/C++ 编译。
- ST-LINK：烧录和调试。
- GDB：暂停、继续、单步、查看变量、修改 RAM。
- SWD：ST-LINK 与 STM32 之间的调试协议。

踩坑：Homebrew 的 `arm-none-eabi-gcc 16.2.0` 当时缺完整 newlib 头文件，出现 `stdint.h`、`errno.h`、`sys/stat.h` 找不到。最后改用 STM32 官方插件管理的 GNU Tools for STM32。经验：STM32 工程尽量不要同时混用多套 ARM GCC，避免 CMake 选错工具链。

## 2. Build / Flash / Debug / Reset

- 改源代码 → 必须重新 Build + Flash。
- 调试器直接改 RAM 变量 → 不需要重新 Build。
- 仅重新上电或 Reset → 仍运行上一次烧录进 Flash 的程序。

## 3. CubeMX 与 VS Code 的关系

`.ioc` 是 CubeMX 的硬件配置文件。CubeMX Generate Code 后会直接更新当前工程目录里的 `.c/.h/CMake` 文件；VS Code 打开的也是同一目录，一般无需关闭重开。

CubeMX 会保留：

```c
/* USER CODE BEGIN ... */
/* USER CODE END ... */
```

之间的代码。自己的逻辑尽量放在 USER CODE 区域。

## 4. STM32 时钟配置

本次配置：

```text
HSE = 8 MHz
PLL ×9
SYSCLK = 72 MHz
AHB = 72 MHz
APB1 = 36 MHz
APB2 = 72 MHz
```

TIM3 挂在 APB1。STM32F1 中，当 APB 分频不为 1 时，Timer Clock = APB Clock ×2，因此 TIM3 Clock = 72 MHz。

经验：以后配置 Timer，第一个问题先确认“这个 Timer 实际收到多少 MHz”。

## 5. Timer / PWM 原理

TIM3 时钟 72 MHz，Prescaler = 71：

```text
72 MHz / (71 + 1) = 1 MHz
```

所以 1 tick = 1 μs。

ARR = 19999，则 0 → 19999 共 20000 tick：

```text
20000 × 1 μs = 20 ms = 50 Hz
```

所以 PSC=71、ARR=19999 得到 50 Hz PWM。CCR/Pulse 决定高电平持续时间，例如 CCR=1500 表示 1500 μs = 1.5 ms。

## 6. 舵机 PWM 的真正含义

位置舵机真正关心的是脉宽，而不是占空比本身。当时采用的经验范围：

```text
约 1000 μs → 一侧
约 1500 μs → 中位附近
约 2000 μs → 另一侧
```

这不是所有舵机统一的严格公式。不同舵机的安全脉宽、机械中位、最大角度、死区都可能不同，因此工程上需要标定：

```text
角度 ≈ f(脉宽)
```

## 7. 舵机为什么不会一直转

STM32 每 20 ms 重复发送 1500 μs，并不是“每 20 ms 再转一次”，而是在持续声明同一个目标位置。

普通位置舵机内部大致是：

```text
PWM 解码 → 目标位置 → 电机/齿轮 → 位置反馈 → 内部闭环控制
```

到达目标后停止并保持。

## 8. Init 和 Start 的区别

CubeMX 生成的 `MX_TIM3_Init()` 只是完成配置；真正开始输出 PWM 还需要：

```c
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
```

理解：Init/Config = 告诉硬件以后怎么工作；Start = 现在开始工作。UART、ADC、DMA、Timer 后面都会反复出现这个模式。

## 9. 舵机供电最大的坑：共地

当时接法：

```text
STM32 PA6        → 舵机 Signal
独立 5V+         → 舵机 VCC
独立 5V GND      → 舵机 GND
STM32 GND        → 独立 5V GND
```

必须共地。STM32 的 3.3 V 高电平是相对 STM32 GND 定义的；舵机判断 Signal 也是相对自己的 GND。两边没有共同 0 V 参考时，PWM 可能漂移，表现为乱转、摆动、抖动或无法稳定定位。

## 10. 实时调参：不要每改一个数就重新烧录

低效方式：源码 1500 → 1600 → 1700，每次 Build → Flash → 测试。

当时使用：

```c
static volatile uint16_t servo_target = 1500;
```

程序烧录一次后，在 Debug 状态暂停 MCU，通过 GDB：

```gdb
set variable servo_target = 1800
print servo_target
```

再 Continue。这里改的是 RAM，不是源码，所以不需要重新 Build。

## 11. static / volatile / 函数原型

```c
static volatile uint16_t servo_target = 1500;
```

- `static`：变量或函数只在当前 `.c` 文件内部可见。
- `volatile`：值可能被正常执行流之外修改，例如调试器、中断、DMA、硬件寄存器，编译器不要擅自优化掉。

只在 `main.c` 使用的函数可写：

```c
static void Servo_Update(void);
```

如果 `main()` 先调用、函数定义在后面，需要提前声明，适合放在：

```c
/* USER CODE BEGIN PFP */
/* USER CODE END PFP */
```

PFP = Private Function Prototypes。

## 12. 舵机抖动与工程处理

当时总结的常见原因：

1. 没有共地。
2. 供电能力不足，舵机启动电流导致 5 V 掉压。
3. 当时记录中使用的低成本舵机存在齿轮间隙、电位器噪声、内部死区等。
4. 目标值阶跃过大，例如 1500 → 1800，容易产生机械冲击、超调和回摆。

## 13. Slew Rate Limiting（变化率限制）

不要直接：

```text
1500 → 1800
```

而是：

```text
1500 → 1510 → 1520 → ... → 1800
```

当时实现思路：

```c
static volatile uint16_t servo_target = 1500;
static uint16_t servo_current = 1500;
```

每 10 ms 调一次 `Servo_Update()`，每次只让 `servo_current` 朝 `servo_target` 改变 10 μs。

数据链：

```text
target
→ slew-rate limiting
→ command
→ 舵机
```

目的：减小机械冲击、超调和明显回摆。

## 14. 工程排障习惯

硬件异常优先按：

```text
供电 → 接线 → 共地 → 时钟 → 外设配置 → 信号 → 软件逻辑 → 算法
```

出现异常先缩成最小系统。例如舵机问题就先固定 PWM、尽量清空 `while(1)`，判断问题在软件还是硬件；原型阶段先验证最短链路，再逐层增加模块。

## 15. 常用快捷键

- Cmd + F：当前文件搜索
- Cmd + Shift + O：当前文件函数/符号跳转
- Control + G：跳到指定行
- Fn + F12 / Cmd + 点击：跳到函数定义
- Shift + Option + F：格式化代码

## 阶段结果

当时实际跑通：

```text
CubeMX 配置
→ 时钟树
→ GPIO
→ Timer
→ PWM
→ ST-LINK 烧录
→ GDB 调试
→ Debug Console 在线调参
→ 独立电源 + 共地
→ 位置舵机控制
→ PWM 平滑变化
→ 基础舵机稳定性处理
```
