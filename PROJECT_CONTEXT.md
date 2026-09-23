# 项目共享上下文

## 项目目标与范围

围绕 STM32F103C8T6 和 RDK X5 建设模块化智能移动机器人。第一阶段：安全可行区域内随机起始位置/朝向，收到停车指令后只凭普通车位线自主找位、在线规划、末段倒车入库并停稳；独立指令出库。开发与展示场地可以不同，不能要求复刻房间或背固定动作。不允许运行时 AprilTag/二维码定位、人工提供初始位姿/车位坐标。见 DEC-013；七个小阶段见总体方案 M0～M6。机械臂是后续可选项。

## 当前能力主线

```text
Motor → Encoder → Speed Estimation → PI → Chassis Motion
      → STM32/RDK 通信 → 感知与定位 → Parking → 稳健性
```

## 当前硬件

- STM32F103C8T6 ×2、RDK X5、ST-LINK、CH340
- `[PROJECT-CONTEXT]` 2026-09-22 用户确认：X5 8GB；已有一台标称 90° 广角 USB 摄像头；目前无 IMU/雷达。型号、实测视场、分辨率/延迟、内外参尚未核验。
- `[DESIGN]` 增补模块优先总额 ≤1000 元，显著收益才讨论 ≤2000 元。单相机/云台/镜面/前后双相机/四相机均未冻结或采购；先 M3 视野实测。
- WHEELTEC R3X 类四轮底盘；实际装配变体尚未登记
- MG513XP28_12V 电机及配套/GMR 编码器；关键电气参数和计数参数仍为 `[UNKNOWN]`
- D153C/D153B TB6612 双路稳压驱动；实物 PCB 版本仍为 `[UNKNOWN]`
- 舵机、12 V 电池、5 V 电源；舵机型号和完整电源树尚未补齐

硬件证据与版本差异见 `01_hardware_source_of_truth.md` 和 `05_open_questions_and_conflicts.md`。

## 当前固件

现有学习工程：

仓库外的只读 `test01` 学习工程（本机位置在本地配置中登记，不随公共仓库分发）。

- `[IMPLEMENTED]` STM32F103C8T6 运行于 72 MHz；PA6/TIM3_CH1 输出 50 Hz 舵机 PWM；USART1 PA9/PA10 为 115200；支持逐行输入、`S:<pulse_us>` 命令、20 Hz 两字段遥测和主循环舵机缓动。[来源：`test01.ioc:8-27,107-135`；`Core/Src/main.c:49-58,102-158,320-368`]
- `[TESTED-BY-TEAM]` 团队此前报告 GPIO/PWM/舵机、独立供电与共地、GDB 调参、缓动、UART 中断、CH340 和 VOFA+ 双向控制均已跑通。
- `[UNVERIFIED-IN-THIS-AUDIT]` 本轮没有执行 ST-LINK 实机连接、电机、编码器或闭环测试。
- `[DESIGN ISSUE]` `test01` 逻辑集中在 `main.c`；TIM3 的 50 Hz 舵机基频与 D153 参考的 TIM3 CH3/CH4 10 kHz 电机 PWM 冲突。
- `[HOST-TESTED]` 2026-09-22：7 项 C 测试（含地址/未定义行为检查）、9 项 Python 测试及 7 个泊车/故障场景通过；测试范围及日志见 `results/verification.json`，不是实机验证。
- `[BUILD-VERIFIED][UNVERIFIED-ON-HARDWARE]` 单电机 Motor A + E1 + UART 候选工程已经完整链接；入口 `firmware/platform/stm32f103_hal/bench_main.c`，默认禁止电机使能，CPR/RPM 上限未填写；没有烧录。
- `[EXPERIMENTAL]` PythonRobotics 规划 + Pure Pursuit 适配 + 同源 C 速度环参与二维阿克曼仿真；尺寸/电机参数是假设，不等同实物。视觉使用 OpenCV 离线测试，尚未接入真实相机或模拟图像闭环。
- `[IMPLEMENTED][EXPERIMENTAL]` 2026-09-23：普通 U 形线框候选（OpenCV LSD）、固定相机地面投影、本地图片/录像批处理与数据泄漏检查；仅合成测试，无真实语义/空闲判断。详见 `offline/README.md`。
- `[HOST-TESTED][SIMULATION-TESTED]` 新增 RS 末段方向筛选、从模拟停稳点重新规划出库及占用目标拒绝；24 个随机起点只检查几何路径，不能当随机自主找位。23 项 Python 回归通过；C 核心保持原样。
- `[UNVERIFIED]` 实拍普通车位识别、主动找位、完整任务状态机、入口跨越倒车约束、真实倒库/出库和跨场地验收均未完成。候选始终 `valid_for_control=false / occupancy=UNKNOWN`，模拟控制仍输入真值；现有 AprilTag 工具不计主线交付。

## 架构基线

- STM32 负责确定性的执行与采样：电机、编码器、速度估算、舵机、安全状态和速度环。
- RDK X5 负责感知、目标/泊车逻辑和高层轨迹命令。由于本地缺少 X5 官方硬件资料，具体接口和能力暂不冻结。
- VOFA+/上位机只负责 bring-up、调参和日志，不得成为运行安全的必要条件。

## 当前关键约束

- 硬件事实必须带来源；没有证据的值保持 `[UNKNOWN]`。
- 电机占空比统一为 `[-1.0,+1.0]`；V0 速度环目标/反馈使用输出轴 RPM。
- 车辆坐标系：`+x` 向前、`+y` 向左、`+z` 向上；正 yaw/转向为向左/逆时针。
- 固定周期控制路径内不得阻塞遥测。
- 底盘运动学与 STM32↔RDK 传输方式，在实物底盘和集成需求确认前保持可调整。
- 未知空间不当作空闲，未看到障碍不等于安全；物理停止不能由 coast 指令或电脑测试替代证明。
- 仓库 main 是集成真源；日常工作走任务分支并同步交接。规则见 AGENTS.md；历史记录不覆盖现行 DEC-013～016。

## 当前明确不做

最终 PCB/CAD、完整 ROS2/SLAM、RTOS、一次性整车固件、最终传感器套装、复杂二进制协议、完整机械臂和对外包装材料。

2026-09-22 执行策略：已有实现和成熟开源优先；学习性重写不是交付前提。离线仿真是分阶段验证资产，不是冻结的整车方案。见 DEC-012。

## 详细文档入口

- 总路线：`00_project_master_plan.md`
- 硬件事实：`01_hardware_source_of_truth.md`
- 复用审查：`02_reference_code_map.md`、`06_reference_reuse_strategy.md`
- Bring-up：`03_motor_encoder_pid_bringup.md`、`10_bringup_checklist.md`
- 固件：`04_firmware_module_plan.md`、`firmware/README.md`
- 接口：`INTERFACE_CONTRACTS.md`、`08_command_telemetry_design.md`
- 未决事项：`OPEN_QUESTIONS.md`、`05_open_questions_and_conflicts.md`
- 当前交接：`HANDOFF.md`
