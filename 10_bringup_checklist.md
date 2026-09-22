# 10 Bring-up 检查表

本文件只提供当前几个月需要的最短排障路径。详细步骤见 `03_motor_encoder_pid_bringup.md`。

## 建议的初始软件设置

以下属于无负载、有电流观察条件下的 `[DESIGN]` 实验限幅，不代表电机/驱动在这些数值下已经证明安全：

```text
启动状态                   DISABLED / standby
Motor PWM                 10 kHz
第一个非零 duty            +0.10
临时 duty 限幅             ±0.20，直到取得电流与响应记录
每 10 ms 最大 duty 变化    0.02
目标控制周期               10 ms，必须用 GPIO 实测
Telemetry                 50 ms / 20 Hz
Kp、Ki、Kd                 RPM 有效前全部为 0
Servo 中位                1500 us
Servo 临时范围            1000～2000 us（当前工程回归范围）
```

若电流异常上升或 Motor 不转，不得提高电流限制或直接跳到满 duty；先检查负载、接线和电机资料。

## A. 上电前

- [ ] 拍摄 D153C 正反面，确认 V1.0/V1.1。
- [ ] 登记 Motor、Encoder、Servo、电池和稳压模块标签。
- [ ] 断电检查极性与连通性。
- [ ] 确认共地，避免 ST-LINK/CH340 地线形成意外供电路径。
- [ ] 车轮架空或 Motor 脱离机械负载。
- [ ] 第一次只接一台 Motor。
- [ ] 使用可观察/限制电流的电源；限流值来自证据，不猜测。
- [ ] 明确并能立即执行 `MOTOR:STOP`。

危险操作：反接、短路、带电插拔 Motor、堵转。来源：`TB6612稳压版随货手册.pdf` p.1～2。

## B. 第一次上电，Motor 断开

- [ ] 测量驱动板 5 V 与 3.3 V；厂家快速判定范围为 5 V±0.5 V、3.3 V±0.3 V。[来源：同上手册 p.1]
- [ ] 测量 Encoder 接口 VCC，并与板版本对应。
- [ ] 测量 STBY，确认默认处于安全状态。
- [ ] 分别测 PWMA/PWMB：目标 10 kHz；证明 A=TIM3_CH4/PB1、B=TIM3_CH3/PB0。[来源：用户手册 p.11、p.17]
- [ ] 测量调度 GPIO：采用当前设计基线时目标为 10 ms。

任何电压或映射错误时：断电 → 查板版本 → 查线序 → 查 CubeMX Alternate Function → 查 HAL Channel。禁止通过“接上 Motor 看看”来诊断。

## C. 单电机

- [ ] 从 0 开始，enable 后发送较低正 duty。
- [ ] 确认物理方向与电流表现。
- [ ] 回到 0，确认选定 stop mode。
- [ ] 停稳后再测试较低负 duty。
- [ ] 小步扫描，记录起转阈值、duty、电流、电压、温度和声音。

必须立即停止：电流异常、供电塌陷、无法停止错误方向、烟雾/异味、快速升温、明显机械卡滞。

## D. 手转编码器

- [ ] Motor disabled；只手转一个轮子。
- [ ] Raw CNT 变化，修正后的 delta 符合正方向定义。
- [ ] 静止时计数不持续漂移。
- [ ] 正反多圈计数具有重复性。
- [ ] 主机端回绕测试和目标读取路径都通过。
- [ ] 记录每输出轴一圈计数；禁止把厂家示例 800/20 当规格。

没有计数时：按 VCC → GND → A/B 波形 → 引脚 AF/Timer → Mode/Filter 排查。方向错误时，只修改集中式 polarity，不能到处添加负号。

## E. 速度与遥测

- [ ] 采样周期来自实测，不来自注释。
- [ ] RPM 使用实测 `dt` 与已记录每圈计数。
- [ ] 正反 RPM 符号正确。
- [ ] Telemetry 位于 ISR 外，初期为 20 Hz。
- [ ] 断开或阻塞终端后，控制周期仍然稳定。

RPM 刚好 ×2/÷2 时，优先检查 5 ms/10 ms 与 Encoder Decode Multiplier。

## F. P/PI

- [ ] 输出与目标限幅已经生效。
- [ ] 低速 P-only，出现正反馈立即停止。
- [ ] P 稳定后才逐步加 I。
- [ ] 饱和测试证明 anti-windup 与恢复有效。
- [ ] disable/fault/目标归零/换向时，积分按方案复位或处理。
- [ ] 保存调参记录和 VOFA+ 数据。

## G. 定时器迁移后的 Servo/UART 回归

- [ ] 原有 `S:1700` 仍然工作。
- [ ] 在新 Servo timer/pin 上实测频率和脉宽。
- [ ] 舵机型号确认前继续使用保守 1000～2000 us。
- [ ] USART1 115200 接收与 20 Hz Telemetry 稳定。

## 最短故障树

```text
Motor 不动
  → 电压轨 → STBY → PWM 波形/通道 → 方向脚 → Motor/线缆

Motor 转但没有计数
  → Encoder VCC/GND → A/B 波形 → Pin AF/Timer → Mode/Filter

有计数但速度错误
  → 真实 dt → 每圈计数 → 解码倍频 → 方向 → 数值计算

开环正常、闭环异常
  → 反馈方向 → 目标单位 → 饱和 → 先只开 Kp → Ki/anti-windup

连接 VOFA+ 后异常
  → ISR/阻塞发送 → Telemetry 频率/帧长度 → Buffer/Timeout
```
