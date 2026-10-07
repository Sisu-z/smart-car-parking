# 2026-09-20 VOFA+ 上位机调试控制舵机

> 状态说明：本文件是 2026-09-20 学习/实操阶段记录，承接 9-19 舵机控制；参数与协议记录当时实际实现，不自动代表当前整车最终接口。

## 1. 本阶段跑通链路

```text
VOFA+
↕
CH340
↕
STM32 USART1
↕
servo_target
↕
舵机
```

同时 STM32 持续上传 `servo_target`、`servo_current` 到 VOFA+ 画实时曲线。后续电机 PID 调参可以复用“命令下发 + 遥测回传 + 上位机观察”这一框架。

## 2. 串口与上位机

USART1：

```text
PA9  = TX
PA10 = RX
115200 8N1
```

CH340：

```text
TX  → PA10
RX  → PA9
GND → GND
```

TX/RX 交叉，并且必须共地。

Mac 当时可用：

```sh
ls /dev/cu.*
```

确认 CH340 设备，例如 `/dev/cu.usbserial-xxx`。

## 3. STM32 → VOFA+ 遥测

STM32 内部变量是数字，UART 最终发送字节，因此先用 `snprintf` 格式化：

```c
snprintf(tx_buf, sizeof(tx_buf), "%u,%u\r\n",
         servo_target, servo_current);
```

例如：

```text
1800,1530
→ "1800,1530\r\n"
→ UART
→ VOFA+ 解析为两路数据
```

- `snprintf`：数字 → 字符串。
- `strtol`：字符串 → 数字。

工程原则：遥测频率不要和控制频率绑死。当时舵机 10 ms 更新一次，遥测 50 ms 发送一次；高速控制环里不要频繁 `snprintf`。

## 4. VOFA+ 波形

右侧出现 I0/I1 只代表数据已解析，不代表波形控件已显示。

需要把波形 Y 轴手动绑定到 I0、I1。Δt 要与发送周期一致，例如 50 ms 上传一次就设置 50 ms。Auto 只有在通道绑定正确后才有意义。

## 5. UART 中断接收

CubeMX：

```text
USART1 → NVIC Settings → USART1 global interrupt
```

启动接收：

```c
HAL_UART_Receive_IT(&huart1, &uart_rx_byte, 1);
```

含义：预约接收 1 byte，收到后通过中断通知 CPU，不阻塞主循环。

流程：

```text
UART 收到字节
→ NVIC 触发中断
→ USART1_IRQHandler()
→ HAL_UART_IRQHandler()
→ 数据写入 uart_rx_byte
→ HAL_UART_RxCpltCallback()
→ 用户处理字符
→ 再次 HAL_UART_Receive_IT()
→ 返回 main
```

回调中：

```c
if (huart->Instance == USART1)
```

用于判断这次回调是否来自 USART1。

工程原则：中断只做轻量工作，如收数据、写 buffer、置 flag；字符串解析和控制计算放主循环。

## 6. 自定义串口协议

当时协议：

```text
S:1700\n
```

含义：

```text
S     = Servo
:     = 分隔符
1700  = 目标脉宽
\n    = 一条命令结束
```

STM32 判断：

```c
strncmp(uart_rx_line, "S:", 2) == 0
```

再用：

```c
strtol(&uart_rx_line[2], NULL, 10)
```

把字符串转成数字。

必须有换行结束符，否则程序不知道一条命令何时结束，`uart_rx_ready` 不会置 1。

## 7. VOFA+ 滑块

Slider：

```text
Min  = 1000
Max  = 2000
Step = 10
```

这里 Step 是滑块目标值的最小变化量，与 STM32 中 `servo_current += 10` 不是同一个概念。

VOFA+ 自定义命令：

```text
名称：Servo
发送内容：S:%.0f\n
```

例如：

```text
滑块 1680
→ S:1680\n
→ STM32 解析
→ servo_target = 1680
```

如果“绑定命令”没有选项，先创建命令。控制滑块只绑定发送命令，不要随意绑定 I0/I1，否则遥测可能把滑块值刷回去。

## 8. 舵机现象

- 手碰舵盘后舵机会顶回来或抖一下：位置闭环在纠偏。
- 接近 2000 μs 时更容易抖：可能接近机械/控制极限，也可能受齿轮间隙、电位器噪声、内部控制和供电影响。
- 1000～2000 μs 不是绝对安全范围，实际仍要标定安全最小值、中位值和最大值。
- 端点出现持续抖动、嗡鸣、硬顶时应缩小范围。

## 9. 工程套路

- 先单向，再双向：先验证 STM32 → PC，再做 PC → STM32。
- 控制与遥测解耦。
- 通信不要阻塞主控制。
- 中断只负责“收和通知”，主循环负责“解析和处理”。
- 串口协议至少包含：命令类型 + 数据 + 结束标志。

## 阶段结果

完成：

```text
VOFA+ ↔ CH340 ↔ STM32 USART1 ↔ servo_target ↔ 舵机
```

并形成了后续可复用的“上位机调参 + 实时遥测”基础框架。
