# 复用清单（2026-09-22）

公开仓库使用 Git 子模块锁定 PythonRobotics，不把嵌套 .git 当普通文件上传。克隆用 `--recurse-submodules`，已有克隆运行 `git submodule update --init --recursive`。不随本仓库分发外部 test01/HAL 或厂商资料。

- PythonRobotics：`https://github.com/AtsushiSakai/PythonRobotics`，固定提交 `08b453a8e3b7a161b6fbbe6b73737758a8ec3482`，MIT；许可证保存在 `PythonRobotics/LICENSE`。稀疏检出 ReedsSheppPath、pure_pursuit、utils；上游代码未修改。
- `offline/parking.py` 直接调用原版 Reeds–Shepp `calc_paths`。Pure Pursuit 只取几何公式并注明来源；适配后轴中心、有符号速度、有界索引、转向限幅与换向等待。未直接使用上游全尺寸车辆、全局参数、显示循环及索引循环。
- OpenCV：通过 `uv.lock` 锁定发布包；保留的 AprilTag/IPPE 是隔离实验。2026-09-23 新增直接调用 LSD 线段、去畸变、单应/透视变换的普通 U 形线框候选；仅合成图片/录像及数学回归验证，无真实车位/空闲语义保证。来源、许可与限制见 `../offline/README.md`，没有新增视觉依赖包。
- NumPy/SciPy/Matplotlib：满足上游依赖；按 `uv.lock` 精确版本复现，不安装整个机器人全栈。
- STM32 HAL/CMSIS/startup/linker：只读引用已有 `test01`；原始版权/许可头保留，没有重新编写 HAL，也没有复制或改写学习工程。迁移机器时须显式指定 `BASELINE` 路径。

复用级别：规划库/通用视觉算子可直接作为依赖；演示程序只做参考；硬件引脚、计数、增益、停止映射必须按本项目复审。固定版本是为了可复现，不代表代码没有缺陷或供应链已经完整审计。
