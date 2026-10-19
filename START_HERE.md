# 新 Agent / 项目成员从这里开始

更新：2026-10-19。日常先读前三份，不必通读全部材料。

本轮现行补充：[库存及S20F来源](01_hardware_source_of_truth.md#2026-10-19-库存与资料核验更新)、[下一步行动与采购状态](NEXT_ACTIONS.md)、[TRACK-V2：黑底白线10mm试验基线](docs/planning/track_visual_spec.md)。已购白色磨砂10mm美纹纸、绝缘胶带和1.2m×3m黑色哑光带背胶卷材；先保留底纸试铺，不重复采购。20mm硬冻结已撤销，最终宽度/几何待实测。

当前优先：从计划转入实施准备与首轮验证，先看[执行附录§0：启动顺序、画板与地图](docs/planning/execution_plan.md#0-现在怎样开始画板和地图放在哪里)及§2现场信息包。当前任务只看[#10](https://github.com/Sisu-z/smart-car-parking/issues/10)；不因启动而放行未审硬件。用户不排固定日期，现场首包约1～2小时，按实际准备缩短。PPT #28独立，不再阻塞研发准备。

1. [项目上下文](PROJECT_CONTEXT.md)：硬件、实现与未验证边界。
2. [初代可行性计划书 v0.1](00_project_master_plan.md)：开头一页结论，§3技术实现链，§5.4工作包与依赖。
3. [下一步行动](NEXT_ACTIONS.md)：现在做什么。

本轮**初代详细计划v0.1已完成技术审查，待用户最终复核**，由总监组织可见工作聊天。专题入口见 [计划书协作说明](docs/planning/README.md)，正式任务只看 [GitHub Issues](https://github.com/Sisu-z/smart-car-parking/issues)。按固定版团队指南v0.3.0工作；计划书完稿和实车通过分别验收。未知硬件参数有对应验证关卡，不要求先测完才交计划。

当前目标：安全区域内随机放置 → 只看普通车位线自主找位 → 倒车入库 → 按指令出库；跨场地展示，禁止运行定位标记和背动作。旧 AprilTag 路线已被 DEC-013 替代。

当前状态：新增普通 U 形线框候选、地面投影/媒体处理工具、模拟倒库后重新规划出库；使用说明在 [offline/README.md](offline/README.md)。**没有实车自主泊车验收证据**，尚无实拍识别与自主找位。仿真输入真值位姿，不是相机闭环。

动手前读 [AGENTS.md](AGENTS.md)，确认任务分支/提交与最近 [HANDOFF.md](HANDOFF.md)。硬件查 [01](01_hardware_source_of_truth.md)，接口查 [INTERFACE_CONTRACTS.md](INTERFACE_CONTRACTS.md) / [CONVENTIONS.md](CONVENTIONS.md)，未知项查 [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)。不改厂商原件，不擅改接口，不以模拟参数解除实机门控。

克隆/复跑见 [README.md](README.md)。结束时同步真实状态、测试/未验证项和交接；任务分支 → 审查 → 集成，不覆盖其他 Agent 工作。

01～11 是同一工作台的专题资料，不是十几个项目版本；历史记录不等于当前决策，总方向只看总体方案和现行决策。
