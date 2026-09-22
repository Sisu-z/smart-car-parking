# 接口契约

版本：`0.1`，状态 `[DESIGN]`。其中已注明的部分已经由可复用模块实现。任何单位、方向、范围或字段顺序变化，都必须经过复审并记录为新决策。

## 0.1 兼容扩展：Bench 安全层（2026-09-22，DEC-012）

所有者：`bench`，纯 C、不访问 HAL。公开函数见 `firmware/bench/bench.h`。`Bench_Tick(now_ms, uint16_counter)` 输入真实毫秒时间和原始计数；返回 `MotorOutput` 并更新 `TelemetryFrame`；`Bench_Command(line,now_ms)` 消费既有 v0.1 命令。不能把它当多车轮/车辆级控制器。

- 上电禁用；板级审核开关关闭时拒绝 ENABLE。运动目标不在禁用期间缓存。
- STOP 禁用并保留故障；DISABLE 才清除故障。故障后必须显式 DISABLE、观察静止、ENABLE、再发送新目标。
- 同一使能周期内禁止目标反向；需先 DISABLE，按 raw delta 观察连续静止再使能。软件静止判据不能替代接线/编码器可靠性审核。
- 只由合法 DUTY/SPEED_RPM 更新运动命令新鲜度；GET/重复 ENABLE 不续租。实际超时值是配置，不是协议保证。
- 台架版只实现 coast，不声称由常高 STBY 接法完成硬件断能。PID 速度过冲时不主动反接制动。
- fault 位：1 超时、2 输入、4 调度、8 标定、16 未经停止的换向、32 硬件审核门控。位可组合。
- 计数未标定时 `actual_rpm/error_rpm` 为 `nan`，不得显示成真实 0 RPM；速度命令被拒绝。20 Hz 文本遥测只供调试，不强迫 VOFA+ 将非法值绘成有效值。
- 单电机候选拒绝 `S:`，原 test01 舵机接口不变。运行中拒绝改增益；先禁用再修改。
- 主机管道 `T,<ms>,<counter>` / `C,<ms>,<line>` 仅是测试注入接口，绝不进入 MCU UART 协议。

输出安全指令不代表物理停止；无独立断能、过流检测或硬件看门狗的证据。本轮没有实现可识别跨会话旧报文的正式 RDK 传输层。

## 通用结果码

```c
typedef enum {
    ROBOT_OK = 0,
    ROBOT_ERR_ARGUMENT,
    ROBOT_ERR_RANGE,
    ROBOT_ERR_UNCALIBRATED,
    ROBOT_ERR_DISABLED,
    ROBOT_ERR_TIMEOUT,
    ROBOT_ERR_FAULT
} RobotResult;
```

当前各 C 模块使用更轻量的模块专属枚举，但语义必须与上表一致。

## Motor API——所有者：`motor`

```c
MotorResult Motor_Init(Motor *motor, const MotorConfig *config);
MotorResult Motor_SetTargetDuty(Motor *motor, float duty);
MotorOutput Motor_Update(Motor *motor);
void Motor_Stop(Motor *motor, MotorStopMode mode);
```

- 输入 duty 必须是有限数，范围 `[-1.0,+1.0]`；经过 polarity 修正后，负数表示反转、正数表示正转。
- 输出包括 `direction {-1,0,+1}`、`pwm_counts [0,pwm_period]` 和 `stop_mode`。
- 调用者按控制周期执行 `Motor_Update()`；模块自身不依赖时钟或 HAL。
- 非法、非有限参数必须返回错误并保持安全零输出。
- 只有 platform 适配层可以把输出转换为 AIN/BIN/PWMA/PWMB 寄存器操作。

## Encoder API——所有者：`encoder`

```c
void Encoder_Init(Encoder *encoder, uint16_t counter, int8_t polarity);
int32_t Encoder_UpdateCounter(Encoder *encoder, uint16_t counter);
EncoderSpeedResult Encoder_DeltaToRpm(int32_t delta, float dt_s,
                                     float counts_per_output_rev,
                                     float *rpm_out);
```

- 硬件原始计数为无符号 16 位。
- Delta 是上次采样到本次采样的有符号计数；单个窗口变化不超过半个计数器范围时可安全处理回绕。
- 经过 polarity 修正后，正 delta 表示车轮向前。
- `dt_s>0` 且 `counts_per_output_rev>0` 并经过验证前，RPM 无效。
- 控制采样基线为 100 Hz，但函数必须显式接收真实 `dt_s`。

## PID API——所有者：`pid`

```c
PidResult PID_Init(PidController *pid, const PidConfig *config);
PidResult PID_Update(PidController *pid, float target, float measured,
                     float dt_s, float *output);
void PID_Reset(PidController *pid);
```

- Target 与 measured 必须使用同一单位；V0 速度环统一为输出轴 RPM。
- 输出为配置范围内的归一化 duty，通常为 `[-1,+1]`。
- 积分采用条件式 anti-windup；设置 `kd=0` 即关闭 D。
- disable、fault 以及状态机定义的换向边界必须调用 `PID_Reset()`。
- 调度由调用者负责，PID 模块不得访问 HAL。

## Command API——所有者：`command`

```c
CommandResult Command_ParseLine(const char *line, RobotCommand *out);
```

换行符只负责传输分帧，不传给 parser。V0 命令：

```text
MOTOR:ENABLE
MOTOR:DISABLE
MOTOR:STOP
DUTY:<-1.0..1.0>
SPEED_RPM:<configured range>
KP:<0..configured max>
KI:<0..configured max>
KD:<0..configured max>
GET:STATUS
S:<servo_us>                 兼容 test01 现有命令
```

- Parser 只返回类型化命令，不得直接修改 motor/controller 状态。
- 未知 key、尾随垃圾字符、非有限数和越界值必须拒绝。
- 当前硬件的更严格范围和命令超时由 state/safety 层处理。

## Telemetry API——所有者：`telemetry`

```c
TelemetryResult Telemetry_FormatCsv(const TelemetryFrame *frame,
                                    char *buffer, size_t capacity);
```

稳定的 v0.1 字段顺序：

```text
T,<timestamp_ms>,<enabled>,<target_rpm>,<actual_rpm>,<error_rpm>,<controller_output>,<pwm_duty>,<encoder_delta>,<fault_flags>\r\n
```

- 默认 20 Hz，必须在控制 ISR 之外发送。
- 未完成标定时不得编造速度值；应拒绝速度环模式或明确报告 invalid/fault。
- `fault_flags` 是无符号位掩码；具体位定义未来由 safety 模块统一管理。

## 未来 STM32 ↔ RDK 命令契约——所有者：Integrator

以下为 `[PROVISIONAL]`，尚未实现、独立于传输方式。2026-09-22 按 DEC-013/014 修订草案：PARK/EXIT 属于 RDK 任务层，不应让 STM32 理解车位或规划。C 模块与台架 v0.1 不变。正式帧须另行版本化、审查和测试：

```text
timestamp
session_id, sequence, protocol_version
mode: DISABLED | MANUAL | TRACK_TRAJECTORY
linear_velocity_mps
steering_angle_rad 或 angular_velocity_radps（由底盘类型决定）
command_timeout_ms
sequence
```

STM32 返回：

```text
timestamp
mode/state
wheel_speed_left/right
steering_angle（若可测或可估计）
odometry increment/quality（后续）
power/fault flags
last_command_sequence
```

UART/CAN 及序列化格式、校验算法、发送频率/超时阈值暂不冻结。会话/序列号/本机接收新鲜度共同使用，不能直接比较不同设备未同步时钟。反馈须有模式、故障、最近接受序列号；失效/重启后不自动恢复目标。

## 未来 perception → parking 契约——所有者：`vision_interface`

`[PROVISIONAL]` 普通车位线观测草案；不是已实现的 AprilTag 输出格式，不含 PWM/电机命令：

| 输入/输出 | 约束 |
|---|---|
| 输入 | 图像、相机/标定版本、采集时间；云台方案另需采集时刻姿态与质量 |
| 输出身份 | `observation_id`、临时 `slot_id`、`camera_id`、`frame_id`；slot_id 是跟踪身份，不是人工标记编号 |
| 几何 | 入口端点、边界、朝向、宽/深（m/rad）、相对变换及被观测/被推定字段的区分；不确定尺寸为 UNKNOWN |
| 质量 | `valid`、观测龄期、置信度及定义、可用时的误差估计、来源与拒绝原因；置信度不冒充经校准概率 |
| 空间 | `occupancy: FREE / OCCUPIED / UNKNOWN` 和空间覆盖范围，未见障碍不能直接置 FREE |
| 频率 | 随实际相机异步输出；控制使用前检查时间与质量，具体最小更新率/超时由实测确认 |
| 错误 | `NO_SLOT / AMBIGUOUS / OUT_OF_VIEW / STALE / UNCALIBRATED / GEOMETRY_INVALID`（草案，编码待冻结） |

对于运动相机必须使用曝光/采集时姿态，不得用稍后接收时云台角替代；多相机外参/时钟关系未验证时不得拼成可信环视。

## 未来 parking → vehicle 契约——所有者：`parking`

`[PROVISIONAL]` Parking 输出受限的车辆级目标（速度 + 转向/曲率，或短时标轨迹）。Vehicle Controller 负责转换为执行器目标；Parking 不得访问 timer 或 HAL。

## 用户/调试端 → RDK 任务契约——所有者：`parking`（设计草案）

- 输入：`task_id + action(PARK/EXIT/CANCEL) + request_id`，不接受人为初始位姿/车位坐标作为自主模式的必要输入。仿真真值接口必须隔离。
- 输出：接受/拒绝、任务状态、候选车位、阶段进度、失败原因、完成证据；重复 request_id 不重新触发运动；任务替换策略须经审查，默认不隐式抢占。
- 状态：`IDLE / SEARCHING / ASSESSING / APPROACHING / REVERSE_PARKING / PARKED / EXITING / STOPPING / FAULT`，尚未实现；业务状态不代替底层 fault。
- EXIT 仅在允许的停止状态、定位与出库通路有效时接受。目标是安全出库区，不保证回到初始随机点。
- CANCEL 可以在任务中提出；返回“收到”不等于停稳，须分开报告停止请求和实测停稳。独立硬件断能不依赖此接口。
- 错误：`NO_SLOT / OCCUPIED / NO_SAFE_PATH / POSE_INVALID / TIMEOUT / LINK_LOST / CANCELLED / STOP_NOT_CONFIRMED`；值/频率/阈值待正式实现前冻结，不混入 v0.1 帧。
