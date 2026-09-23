# 新 Agent / 项目成员从这里开始

更新：2026-09-23。日常先读前三份，不必通读全部材料。

1. [项目上下文](PROJECT_CONTEXT.md)：硬件、实现与未验证边界。
2. [总体方案](00_project_master_plan.md)：第一阶段目标与 M0～M6 验收路线。
3. [下一步行动](NEXT_ACTIONS.md)：现在做什么。

当前目标：安全区域内随机放置 → 只看普通车位线自主找位 → 倒车入库 → 按指令出库；跨场地展示，禁止运行定位标记和背动作。旧 AprilTag 路线已被 DEC-013 替代。

当前状态：新增普通 U 形线框候选、地面投影/媒体处理工具、模拟倒库后重新规划出库；使用说明在 [offline/README.md](offline/README.md)。**没有实车自主泊车验收证据**，尚无实拍识别与自主找位。仿真输入真值位姿，不是相机闭环。

动手前读 [AGENTS.md](AGENTS.md)，确认任务分支/提交与最近 [HANDOFF.md](HANDOFF.md)。硬件查 [01](01_hardware_source_of_truth.md)，接口查 [INTERFACE_CONTRACTS.md](INTERFACE_CONTRACTS.md) / [CONVENTIONS.md](CONVENTIONS.md)，未知项查 [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)。不改厂商原件，不擅改接口，不以模拟参数解除实机门控。

克隆/复跑见 [README.md](README.md)。结束时同步真实状态、测试/未验证项和交接；任务分支 → 审查 → 集成，不覆盖其他 Agent 工作。

01～11 是同一工作台的专题资料，不是十几个项目版本；历史记录不等于当前决策，总方向只看总体方案和现行决策。
