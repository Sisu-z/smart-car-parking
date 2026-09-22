# 模块所有权与边界

这里的“所有权”指职责边界，不代表永久指定某个人。

| 模块 | 负责内容 | 可以依赖 | 禁止承担 |
|---|---|---|---|
| `platform/stm32f103_hal` | HAL 句柄、GPIO、定时器通道、ADC/UART 传输、ISR 胶水 | CubeMX/HAL | 控制策略、PID 调参、泊车逻辑 |
| `motor` | Duty 校验、极性、slew、输出换算、停止状态请求 | platform 写入接口 | 读取编码器、解析命令、理解车辆路径 |
| `encoder` | 原始计数差、回绕、方向修正；完成标定后换算 RPM | platform 计数读取、配置 | 驱动电机或猜测 CPR |
| `pid` | P/PI/PID 数学、输出限幅、anti-windup、复位 | 数值目标和反馈 | 访问 HAL、UART 或负责单位换算 |
| `command` | 文本命令解析、类型/范围校验、生成命令对象 | 字节/行传输 | 直接写 PWM，或在 ISR 中修改控制器全局变量 |
| `telemetry` | 状态快照结构与格式化 | 不可变状态快照 | 阻塞控制 ISR，或成为安全依赖 |
| `safety/state` | enable/disable/fault 转换、超时、输出门控 | 传感器和命令有效性 | 执行视觉或路径规划 |
| `vehicle`（后续） | 车轮/转向目标、底盘运动学 | motor/servo/speed 接口 | 直接操作定时器寄存器 |
| `odometry`（后续） | 位姿增量和质量/协方差信息 | 车轮、转向、IMU 样本 | 命令执行器 |
| `vision_interface`（后续） | 普通车位边界/入口/位姿、空闲/未知空间、时间与质量 | RDK 感知输出 | 直接控制电机、把标记实验当普通线识别 |
| `parking`（后续） | 泊车状态机、轨迹请求、完成判定 | 定位和 vehicle controller | 访问 HAL、PWM 或编码器计数器 |

## 集成规则

只有 System Integrator 可以在 `app_main`/scheduler 中连接模块。Specialist Agent 可以在接口约束内修改单个模块；如果要修改单位、方向、频率、枚举值或消息字段，必须复审 `INTERFACE_CONTRACTS.md` 并在 `DECISIONS.md` 记录。

## 当前实现边界

2026-09-22：`bench/` 实现单电机安全/控制编排；`offline/` 负责模拟环境、规划适配和验证，不访问真实串口；`tools/` 是构建/标定/日志工具。新 HAL 候选已独立编译链接，仍未上板。后续不得将模拟尺寸/计数复制进硬件配置。

`firmware/` 下的纯 C 逻辑在通过测试后可标记为 `[IMPLEMENTED][HOST-TESTED]`。独立 STM32 单电机候选已经 `[BUILD-VERIFIED]`，但物理行为仍 `[UNVERIFIED]`；未来联合工程另行复审。现有 `test01` 不会自动被替换。

## 分支所有权

所有权是任务级临时写入边界，不是永久占有。领取任务时在任务描述/PR 写明模块、文件范围、基础提交、接口依赖和集成负责人。跨模块改动必须先协调；AGENTS/接口/单位/总方案由 Integrator 统一合并。两项任务不得在同一工作目录或同一分支同时编辑。

`offline/vision.py` 的 AprilTag 检测是保留实验；未来普通线感知应有独立入口和测试。`offline/parking.py` 当前只提供模拟真值闭环，不是实车 parking 模块。`tools/` 不得因调试便利绕过固件安全门控。
