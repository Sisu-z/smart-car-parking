# 可复用固件资产

状态：

- 核心模块：`[IMPLEMENTED]`；通过 `tests` 后可标记为 `[HOST-TESTED]`。
- STM32 独立单电机候选：`[BUILD-VERIFIED][UNVERIFIED-ON-HARDWARE]`；未合入 `test01`、没有烧录，默认禁止电机使能。

这些文件刻意避开 CubeMX 生成代码。核心数学和 parser 模块可以同时在 macOS 与 STM32 上编译；硬件寄存器与 HAL 句柄只允许出现在 `platform/stm32f103_hal/`。

## 模块

- `motor/`：归一化 duty、极性、slew 和 stop state 换算。
- `encoder/`：16 位回绕安全的 count delta，以及完成标定后的 RPM 换算。
- `pid/`：带输出边界和条件积分的 P/PI/PID。
- `command/`：换行帧内容 parser，不产生控制副作用。
- `telemetry/`：稳定 CSV 帧格式化，不直接调用 UART。
- `bench/`：单电机安全状态、时序、命令与控制编排；超时/坏输入/换向锁存；供主机模拟和 STM32 共用。

最新复跑入口：在根目录 `uv run python tools/run_offline.py`。本轮结果与限制见根目录 `HANDOFF.md`。

## 集成边界

应用层负责调用顺序和时序：

```c
delta = Encoder_UpdateCounter(...);
Encoder_DeltaToRpm(delta, measured_dt_s, counts_per_rev, &rpm);
PID_Update(&speed_pi, target_rpm, rpm, measured_dt_s, &duty);
Motor_SetTargetDuty(&motor, duty);
output = Motor_Update(&motor);
MotorHal_Apply(&motor_hal, &output);
```

当前 `test01` 必须先完成定时器资源复审。不能只复制这些文件就假设硬件已经就绪。

在受保护的集成工程中引用模块后，只把用户源码加入顶层 `CMakeLists.txt`：

```cmake
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    path/to/motor.c
    path/to/encoder.c
    path/to/pid.c
    path/to/command.c
    path/to/telemetry.c
)
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    path/to/motor
    path/to/encoder
    path/to/pid
    path/to/command
    path/to/telemetry
)
```

不得修改会被重新生成的 `cmake/stm32cubemx/CMakeLists.txt`。

## 主机验证

在本工作区执行：

```sh
cmake -S tests -B tests/build
cmake --build tests/build
ctest --test-dir tests/build --output-on-failure
```

通过主机测试只能证明模块逻辑按测试工作，不能证明接线、定时器频率、电流余量、编码器比例或闭环硬件稳定性。
