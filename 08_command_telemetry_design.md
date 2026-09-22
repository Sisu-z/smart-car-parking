# 08 Command 与 Telemetry 设计

版本：`0.1`。V0 台架阶段采用换行分隔的 ASCII 文本。

## 设计目标

- 可在串口终端和 VOFA+ 中直接阅读。
- 一行一个命令，语法严格，parser 输出类型化结果。
- Parser 与状态修改、电机输出分离。
- Safety/State 层再次检查范围和新鲜度。
- Telemetry 字段顺序稳定，频率低于控制环。

## 命令

| 命令 | 含义 | Parser 范围 | State 层规则 |
|---|---|---|---|
| `MOTOR:ENABLE` | 请求使能执行器 | 无值 | 只有配置和安全门槛有效时允许 |
| `MOTOR:DISABLE` | 禁用软件输出并清故障 | 无值 | 当前 bench 请求 coast 并复位 PID，不是物理 STBY 断能 |
| `MOTOR:STOP` | 禁用并保留故障 | 无值 | 当前 bench 请求 coast；不声称主动刹停 |
| `DUTY:<x>` | 开环归一化 duty | `-1..+1` | B01～B05 期间施加更低实验限幅 |
| `SPEED_RPM:<x>` | 输出轴速度目标 | Parser 只做合理性检查 | counts/rev 和上限未验证时拒绝 |
| `KP:<x>` | 比例增益 | 非负 | 当前实验定义更严格边界 |
| `KI:<x>` | 积分增益 | 非负 | 当前实验定义更严格边界 |
| `KD:<x>` | 微分增益 | 非负 | PI 证据证明需要 D 之前保持 0 |
| `GET:STATUS` | 请求状态帧 | 无值 | 不得改变执行器状态 |
| `S:<us>` | 兼容已有 Servo 命令 | 当前 Parser 为 1000～2000 | 保留当前保守范围；精确舵机边界仍未知 |

示例：

```text
MOTOR:ENABLE
DUTY:0.15
SPEED_RPM:80
KP:0.012
KI:0.040
MOTOR:STOP
```

`DUTY:2`、`KP:nan`、尾随垃圾字符、空值和未知 key 都必须拒绝。

## 处理流程

```text
UART ISR 接收字节
  → line buffer / ready flag
主循环 Command_ParseLine()
  → RobotCommand
Safety/State 检查 mode、标定、范围与新鲜度
  → 更新目标/参数，或拒绝
固定周期控制只读取不可变命令快照
```

ISR 不得执行 PID、直接写 Motor PWM、解析浮点数或格式化回复。

## 命令新鲜度

`[IMPLEMENTED]` 以 `INTERFACE_CONTRACTS.md` 的 Bench 扩展为准：只有合法 DUTY/SPEED_RPM 刷新运动命令时刻，GET/重复 ENABLE 不续租；超时故障锁存、禁用并请求 coast，不是先斜坡减速再物理 standby。恢复要显式 DISABLE、观察静止、ENABLE、发送新目标。真实停止效果尚未实测。正式 RDK 协议还需会话/序列/校验，不能靠本机接收时间排除延迟旧包。

## 遥测帧

```text
T,<timestamp_ms>,<enabled>,<target_rpm>,<actual_rpm>,<error_rpm>,<controller_output>,<pwm_duty>,<encoder_delta>,<fault_flags>\r\n
```

示例：

```text
T,18420,1,80.000,77.350,2.650,0.24100,0.24100,52,0
```

- Timestamp 为本机单调递增毫秒。
- 只有标定完成后 speed 字段才有效；否则拒绝进入速度环，不能输出伪 RPM。
- `controller_output` 与 `pwm_duty` 都是归一化值。
- `encoder_delta` 是当前控制窗口中的有符号计数。
- `fault_flags` 是数值位掩码，具体位定义后续统一版本化。

当前参考 formatter 使用 `snprintf` 输出浮点数。部分嵌入式 newlib 默认不支持浮点格式，启用后还会增加 Flash 占用。STM32 集成时先检查链接和体积；如不可接受，只替换为定点/缩放整数 formatter，不改变 `TelemetryFrame` 和字段语义。

## 频率

- 控制：目标 100 Hz，必须实测。
- Telemetry：默认 20 Hz；通过负载/时序测试后最多提高到 50 Hz。
- Command receive：异步接收；在主循环/服务上下文解析。

## 与当前 `test01` 的兼容

现有 `S:1700\n` 命令继续有效。当前遥测为 `servo_target,servo_current`；集成副本中可以保留独立的 `SERVO,...` 帧，或在升级协议版本后增加字段。不得静默把原两列解释为电机数据。

## 未来 RDK 链路

当前台架协议不自动成为正式 RDK 协议。保留类型化 command/state 对象，未来才能在不改 motor、encoder、PID API 的情况下，将文本 UART 替换为带分帧 UART 或 CAN。
