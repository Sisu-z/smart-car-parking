# 智能车：普通车位线自主泊车

STM32F103C8T6 + RDK X5 的分阶段工程工作台。当前是**硬件审计、候选固件与离线实验**，不是已经完成的自动泊车产品。

目标：在约定安全区域随机起始 → 自主找普通车位 → 在线规划 → 倒车入库 → 按指令出库；开发与展示场地可不同。运行时不用 AprilTag/二维码，不背场地坐标或定时动作。

## 只看这三份

- [从这里开始](START_HERE.md)：新成员/Agent 的短入口。
- [总体方案与第一阶段七个小阶段](00_project_master_plan.md)：唯一总方案。
- [下一步行动](NEXT_ACTIONS.md)：现在最值得做什么。

[项目上下文](PROJECT_CONTEXT.md) ｜ [最新交接](HANDOFF.md) ｜ [硬件事实](01_hardware_source_of_truth.md) ｜ [未决问题](OPEN_QUESTIONS.md) ｜ [Agent 规则](AGENTS.md)

01～11 是专题资料，不是多套项目版本；不要按文件数量判断项目已完成多少。

## 当前能力边界

已有纯 C motor/encoder/PI/command/telemetry、安全编排与测试，独立单电机 STM32 候选、开源规划适配、电脑端仿真/故障注入、标定/日志/回放工具。

尚无实车完整自主泊车验收。普通线识别、随机找位、出库、真实相机闭环、正式 RDK 通信和跨场地能力仍待实现/验证。仿真用假设模型与真值位姿；AprilTag 代码仅隔离实验。编译、主机测试和仿真不等于上板安全。

用户报告：X5 8GB、现有标称 90° USB 相机、无 IMU/雷达；增补优先 ≤1000 元，必要时讨论 ≤2000 元。相机方案尚未定型。

## 克隆与电脑端复跑

当前复跑入口面向 macOS/Linux，需要 Git、CMake ≥3.22、C 编译器和 uv；Python 3.12～3.13。Windows 原生运行未验证（进程管道使用 POSIX select）。

```sh
git clone --recurse-submodules https://github.com/Sisu-z/smart-car-parking.git
cd smart-car-parking
uv sync --frozen
uv run --frozen python tools/run_offline.py
```

已经克隆但缺依赖：

```sh
git submodule update --init --recursive
```

生成 results/离线验证结果.html 与 results/verification.json。默认仅电脑端，不访问串口、不烧录、不控制设备；单步最多 120 秒，失败记录后继续独立步骤。场景数量/测试范围见交接，结果不是实车成功率。results/build/.venv 默认不提交，新克隆须本地生成。

PythonRobotics 固定在子模块提交，许可证与来源见 [third_party/README.md](third_party/README.md)。下载仓库 ZIP 不会自动包含子模块，优先按上述方式克隆。

### 可选 STM32 编译

HAL/CMSIS/启动/链接文件来自仓库外的只读 test01 基线，未公开打包；还需 arm-none-eabi 工具链。显式指定：

```sh
uv run --frozen python tools/run_offline.py --with-stm32 --baseline /absolute/path/to/test01
```

只构建，不烧录。依赖结构和上板限制见 [固件集成说明](firmware/platform/stm32f103_hal/README.md)。未提供基线时不能宣称新机器完成 MCU 构建；实物未审查前不解除默认门控。

## 多对话 / 多线程协作

把本仓库链接发给新对话，要求先读 START_HERE.md 与 AGENTS.md，并报告 main/任务分支及提交。公开便于读取，但不代表所有 Agent 有网络、GitHub 写权限或实时同步能力。

按“独立任务分支/工作目录 → 测试与交接 → Reviewer → Integrator → main”维护；规则与例外在 AGENTS.md。完成任务时同步文档和代码，不需要另外复制一套最新方案。当前没有声称启用 GitHub 强制分支保护或持续后台维护。

## 公开范围与许可

本仓库公开项目编写的文档/代码/模板及带许可的依赖引用；不含厂商原始资料包、外部学习固件/HAL、原视频、私人配置、密钥和构建日志。硬件引用保留原文件名/页码/源码位置；原件未分发，外部读者不能仅凭仓库重新核验全部厂商结论，待核项仍 UNKNOWN。

项目自有内容的统一再分发许可证尚未由作者确定；公开可读不等于默认 MIT/Apache。第三方仍按其自身许可，衍生/适配内容保留归属和必要通知。使用代码前自行完成适配、风险审查与实物测试，不可直接无人看护运行车辆。
