# 06 参考实现复用策略

本文件是 `02_reference_code_map.md` 的执行层结论。

## 可以直接复用

“直接复用”仍要求目标 MCU/版本匹配，并保留原许可证。

- 针对所选 STM32F103C8T6 配置重新生成的 STM32Cube HAL/CMSIS。
- 厂家真值表与已经交叉核对的 D153 引脚映射；它们作为配置输入，而不是应用架构。
- 当前台架链路的 USART1 115200 8N1。[来源：D153 GMR HAL `Core/Src/usart.c:55-72,95-108`；当前 `test01/Core/Src/main.c:269-276`]
- 当前 `test01` 的舵机命令与遥测行为，作为回归基线，不作为最终模块结构。[来源：`test01/Core/Src/main.c:120-158,320-368`]
- 通过主机测试后的 `firmware/` 纯 C 模块。

## 只复用配置/思路，随后重写

- D153 对 TIM2/TIM4 Encoder Mode 的选择与 GPIO 映射。
- 10 kHz Motor PWM 目标和 D153 A/B 方向真值关系。
- 把 16 位计数器转换为有符号 delta 的思路。
- 厂家增量式 PI 公式，只用于学习和对照。
- 确认板版本并标定 ADC 后，使用 D153 的 1/11 分压关系。

必须重写的原因：HAL 示例 PWM A/B 通道写反；所谓“10 ms”实际为 5 ms；ISR 内直接打印；控制量是原始窗口计数而不是物理速度。证据见 `02_reference_code_map.md` 第 3 节。

## 必须由本项目实现

- 集中记录 left/right、motor polarity、encoder polarity 的 Board Config。
- 明确的 stop mode、slew/limit 和命令超时。
- 使用真实 `dt` 与每输出轴一圈计数的速度估计器。
- 统一单位下的 P/PI、复位和 anti-windup。
- 与控制状态解耦的类型化命令 parser。
- 非阻塞遥测快照与传输。
- Chassis/Vehicle API、里程计质量、STM32↔RDK 接口。
- 泊车状态机、定位有效性、轨迹/跟踪与恢复。

这些模块承载本项目特有的单位、安全和所有权；复制 demo 只会隐藏工作，不会消除工作。

## 目前没必要使用

- 把 D24A F103RCT6/TIM5/TIM8 工程当 C8T6 基线。
- 把 Arduino 或 STM32 标准库工程当正式 HAL 源码。
- 厂家默认 target count 与 Kp/Ki。
- 压缩包内预编译的 AXF/HEX/OBJ。
- 尚未取得的百度网盘底盘源码。
- 尚未出现需求时引入完整 ROS2/SLAM、RTOS、二进制协议或第二块 STM32。

## 当前工程复用结论

| 资产 | 复用判断 | 原因 |
|---|---|---|
| `test01.ioc` 时钟/UART/SWD | 直接作为基线 | 当前可构建，准确位置已记录在 `PROJECT_CONTEXT.md` |
| `test01` Servo TIM3_CH1 | 只保留回归行为 | 与 10 kHz TIM3 Motor 基频冲突，计划迁移到 TIM1 |
| `test01` 逐字节 UART ISR | 借鉴接收结构 | Parser/Buffer 所有权应移到 `command`；只有出现需求时再加 ring buffer |
| `test01` 的 `S:` 命令 | 保留兼容 | 已经使用；Servo 范围仍由 safety 层限制 |
| `test01` 阻塞式 telemetry | 替换 | `HAL_MAX_DELAY` 不得进入未来控制路径 |
| 新增 `firmware/*` | CubeMX 复审后集成 | 已通过主机测试且独立于 HAL；硬件行为仍未验证 |

## 外部实现进入主工程前的检查

1. 硬件、MCU 和库版本准确匹配。
2. 单位和时基写清楚。
3. 方向与 `CONVENTIONS.md` 一致。
4. 控制时序内没有阻塞操作。
5. 饱和、超时和 disabled 行为有定义。
6. 有主机测试或台架测试支持所声称的行为。
7. Reviewer 确认没有静默修改接口。

任一项不满足，就归类为“借鉴后重写”，不能标为“直接复用”。
