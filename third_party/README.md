# 复用清单（2026-09-22）

公开仓库使用 Git 子模块锁定 PythonRobotics，不把嵌套 .git 当普通文件上传。克隆用 `--recurse-submodules`，已有克隆运行 `git submodule update --init --recursive`。不随本仓库分发外部 test01/HAL 或厂商资料。

- PythonRobotics：`https://github.com/AtsushiSakai/PythonRobotics`，固定提交 `08b453a8e3b7a161b6fbbe6b73737758a8ec3482`，MIT；许可证保存在 `PythonRobotics/LICENSE`。稀疏检出 ReedsSheppPath、pure_pursuit、utils；上游代码未修改。
- `offline/parking.py` 直接调用原版 Reeds–Shepp `calc_paths`。Pure Pursuit 只取几何公式并注明来源；适配后轴中心、有符号速度、有界索引、转向限幅与换向等待。未直接使用上游全尺寸车辆、全局参数、显示循环及索引循环。
- OpenCV：通过 `uv.lock` 锁定发布包；调用现成 AprilTag 字典检测、IPPE 与棋盘标定。AprilTag 是保留实验，不符合本项目普通车位线主线；标定/坐标变换可复用。尚无普通线检测器完成验证。
- NumPy/SciPy/Matplotlib：满足上游依赖；按 `uv.lock` 精确版本复现，不安装整个机器人全栈。
- STM32 HAL/CMSIS/startup/linker：只读引用已有 `test01`；原始版权/许可头保留，没有重新编写 HAL，也没有复制或改写学习工程。迁移机器时须显式指定 `BASELINE` 路径。

复用级别：规划库/通用视觉算子可直接作为依赖；演示程序只做参考；硬件引脚、计数、增益、停止映射必须按本项目复审。固定版本是为了可复现，不代表代码没有缺陷或供应链已经完整审计。
