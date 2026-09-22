# 01 硬件事实库

基准日期：2026-09-21

资料根目录：`<HARDWARE_SOURCE_ROOT>`（仓库外只读硬件资料）
规则：只记录本地资料直接支持的事实；项目口述但资料未支持者标为 `PROJECT-CONTEXT`；没有证据者标为 `UNKNOWN`；不同型号/版本不互相外推。

## 证据状态

### 2026-09-22 用户库存补充（不升级为厂商事实）

- `PROJECT-CONTEXT`：RDK X5 为 8GB，已有标称 90° 广角 USB 相机，目前无 IMU/雷达。来源：用户在项目对话中对硬件/预算问题的明确回复，已转录于 `PROJECT_CONTEXT.md`“当前硬件”。未取得精确型号/资料/实测前，视场方向、分辨率/帧率、延迟、内外参和接口供电均为 `UNKNOWN`。
- 预算与相机选型流程属于设计决定，见 DEC-015；不据此确认任何相机或 RDK 电气兼容。

下述厂商证据来自仓库外只读资料；公共仓库保留引用但不分发原件，未取得原件的 Agent 不得声称重新核验。

- `VERIFIED-IN-SOURCE`：在指定文件、页码/章节或源码位置直接出现。
- `CONFLICT`：两个来源不能同时作为同一实物的事实使用。
- `UNKNOWN`：资料集中未发现精确型号所需信息。
- `PROPOSAL`：工程建议，不是厂家硬件事实。

## 1. STM32F103C8T6 与 D153C/D153B 参考接口

| 项目 | 事实 | 状态与来源 |
|---|---|---|
| 例程目标 MCU | D153 双路 HAL 工程目标为 STM32F103C8T6、LQFP48，系统时钟配置为 72 MHz | `VERIFIED-IN-SOURCE`：`.../D153B_GMR编码器HAL库例程_2026.8.20.zip` 内 `tb6612demo/tb6612demo.ioc:14-27, 138-157` |
| 电机 A 编码器 | E1A→PB6/TIM4_CH1，E1B→PB7/TIM4_CH2 | `VERIFIED-IN-SOURCE`：`电机驱动模块使用手册—TB6612(2025.08.27).pdf`，p.17，4.2 节；同 ZIP `tb6612demo/tb6612demo.ioc:87-88,170-173` |
| 电机 B 编码器 | E2A→PA0/TIM2_CH1，E2B→PA1/TIM2_CH2 | `VERIFIED-IN-SOURCE`：同上手册 p.17；同 ZIP `tb6612demo/tb6612demo.ioc:66-67,162-165` |
| PWM 接线 | PWMA→PB1/TIM3_CH4；PWMB→PB0/TIM3_CH3 | `VERIFIED-IN-SOURCE`：同上手册 p.17；`D153C模块与STM32F103C8T6核心板接线说明.png` 的引脚标注；同 ZIP `tb6612demo/tb6612demo.ioc:77-78,166-169` |
| 方向脚 | AIN1→PB14，AIN2→PB15；BIN1→PB13，BIN2→PB12 | `VERIFIED-IN-SOURCE`：同上手册 p.17；同 ZIP `tb6612demo/Core/Src/gpio.c:52-60` 与 `Core/Src/tim.c:423-441` |
| 电压采样 | D153 ADC→PA6/ADC1_IN6；板上 100 kΩ/10 kΩ（V1.1 原理图）构成 1/11 分压；例程按 `ADC*3.3*11/4096` 换算 | `VERIFIED-IN-SOURCE`：`TB6612双路驱动稳压模块原理图_V1.1_2026.04.20（D153C）.pdf`，p.1，左上；HAL ZIP `Core/Src/adc.c:57-68,84-90` 与 `Core/Src/main.c:110-114` |
| 串口 | USART1，TX=PA9，RX=PA10，115200 8N1 | `VERIFIED-IN-SOURCE`：HAL ZIP `Core/Src/usart.c:55-72,95-108`；外层 `使用说明.txt` 第 1-2 行 |
| STBY | STBY 必须为高才工作；参考接线把它直接接 3.3 V，而不是 MCU GPIO | `VERIFIED-IN-SOURCE`：TB6612 数据手册 p.2、p.4；用户手册 p.11；接线表 p.17 |

注意：上表是**厂家参考映射**，不是最终项目引脚冻结。尤其 PWM A/B 在 HAL 应用函数中被写反，见 `02_reference_code_map.md`。

## 2. TB6612FNG 芯片本体

| 参数 | 事实 | 状态与来源 |
|---|---|---|
| 电机电源绝对最大值 | VM=15 V max | `VERIFIED-IN-SOURCE`：`6.芯片手册/TB6612FNG芯片手册.pdf`，p.1、p.3 |
| 推荐工作范围 | VM=2.5-13.5 V；当 VM≥4.5 V 时单通道工作电流上限表列 1.0 A | `VERIFIED-IN-SOURCE`：同数据手册 p.3，Operating Range |
| 逻辑电源 | VCC=2.7-5.5 V 工作；绝对最大 6 V | `VERIFIED-IN-SOURCE`：同数据手册 p.3 |
| 输出电流 | 1.2 A/通道连续额定；2 A 为 20 ms、Duty≤20% 连续脉冲条件；3.2 A 为 10 ms 单脉冲峰值 | `VERIFIED-IN-SOURCE`：同数据手册 p.3，Absolute Maximum Ratings |
| PWM | 最大 100 kHz | `VERIFIED-IN-SOURCE`：同数据手册 p.3 |
| 工作模式 | 正转、反转、短刹车、停止（高阻）和待机 | `VERIFIED-IN-SOURCE`：同数据手册 p.4，H-SW Control Function |
| 默认输入状态 | PWMA/PWMB、AIN/BIN 和 STBY 有内部 200 kΩ 下拉；STBY 低为待机 | `VERIFIED-IN-SOURCE`：同数据手册 p.2 |
| 保护 | 芯片内置热关断和低压检测；仍要求系统级保险/限流及感性负载保护评估 | `VERIFIED-IN-SOURCE`：同数据手册 p.1、p.9，IC Usage Considerations |
| 静电 | MOS 结构对 ESD 敏感 | `VERIFIED-IN-SOURCE`：同数据手册 p.1 |

## 3. D153C 双路稳压模块

### 3.1 型号与版本

- 厂家例程目录仍名为 D153B，但资料明确写“D153C 与 D153B 例程仅丝印差异，其余均相同”。`VERIFIED-IN-SOURCE`：[来源：`4.例程源码/1.STM32F1例程/说明文档（必看）.txt`，第 4 行]
- D153C 有 V1.0 和 V1.1；V1.1 的实物版本号位置见 `5.原理图/2.D153C双路驱动稳压模块/不同版本D153C识别方法.png`。`VERIFIED-IN-SOURCE`
- V1.1 相比 V1.0 增加控制信号串联电阻、电源 TVS 和输入防反接，尺寸孔位和控制使用不变。`VERIFIED-IN-SOURCE`：[来源：同目录 `不同硬件版本更新内容.txt`，第 1-5 行；V1.1 原理图 p.1]

### 3.2 电源与接口

| 项目 | 事实 | 状态与来源 |
|---|---|---|
| 模块输入标称 | 厂家用户手册/排障手册写 4.5-15 V 或 5-15 V | `CONFLICT-WITH-CHIP-MARGIN`：用户手册 p.15、p.17；`TB6612带稳压模块问题排查和检测方法(2025.07.10).pdf`，p.5-6；`TB6612稳压版随货手册.pdf`，p.1-2 |
| 推荐供电示例 | 随货手册推荐 7.4 V 或 12 V | `VERIFIED-IN-SOURCE`：`TB6612稳压版随货手册.pdf`，p.2，“电源（最易烧毁）” |
| 5 V 稳压 | 用户手册称板载 5 V/5 A 输出；V1.1 原理图使用 RT8279 | `VERIFIED-IN-SOURCE`：用户手册 p.8；V1.1 原理图 p.1；`6.芯片手册/RT8279.PDF`，p.1-2 |
| RT8279 边界 | RT8279 芯片给出的输入工作范围是 5.5-36 V、连续输出能力声明为 5 A；板级实际持续能力仍取决于散热与外围件 | `VERIFIED-IN-SOURCE`：`RT8279.PDF`，p.1-2。最后一句为工程边界，不把芯片能力等同板端保证 |
| 3.3 V 稳压 | V1.1 原理图使用 RT9013-33GB；RT9013 是 500 mA LDO，输入工作 2.2-5.5 V | `VERIFIED-IN-SOURCE`：V1.1 原理图 p.1；`6.芯片手册/RT9013-33GB.PDF`，p.1、p.3 |
| 编码器通道 | 模块只做编码器供电和 A/B 信号透传，最终 A/B 仍接 MCU | `VERIFIED-IN-SOURCE`：排障手册 p.7，4 节 |
| 电源监测 | 1/11 分压送 ADC | `VERIFIED-IN-SOURCE`：用户手册 p.8；V1.1 原理图 p.1 |
| 使能 | STBY 参考接法为 3.3 V 或 5 V | `VERIFIED-IN-SOURCE`：`D153C模块与STM32F103C8T6核心板接线说明.png` 底部黄色说明；用户手册 p.17 |
| 安全禁令 | 禁止反接、短路、带电插拔电机、长时间堵转，板底应绝缘 | `VERIFIED-IN-SOURCE`：`TB6612稳压版随货手册.pdf`，p.1-2 |

### 3.3 不得混用的版本事实

- V1.0 原理图的 6-pin 电机接口给编码器提供 5 V；V1.1 原理图给 E1/E2 接口提供 3.3 V。`CONFLICT/REVISION-DEPENDENT`：[来源：`TB6612双路驱动稳压模块原理图_V1.0（D153C）.pdf`，p.1，MOTORC1/2；V1.1 原理图 p.1，MOTORC1/2]
- V1.1 原理图和版本更新说明显示输入防反接；随货安全手册仍写“本模块无防反接，反接必烧”。`CONFLICT/REVISION-DEPENDENT`：[来源：V1.1 原理图 p.1，右下“防反接电路”；`不同硬件版本更新内容.txt` 第 1-5 行；`TB6612稳压版随货手册.pdf` p.2]
- 结论：未识别实物版本前，按**最保守边界**操作：禁止反接、先断电接线、测量编码器供电，不根据资料包日期猜版本。

## 4. WHEELTEC MG513XP28_12V 电机

| 参数 | 当前结论 | 证据 |
|---|---|---|
| 项目指定型号 | WHEELTEC MG513XP28_12V | `PROJECT-CONTEXT`：用户给定；本地未发现该完整 SKU 的数据页 |
| 额定电压 | 名称含 12V，但精确数据页缺失 | `UNKNOWN`：不得只依据命名扩展为完整额定参数 |
| 额定转速/空载转速 | UNKNOWN | 本地资料无精确 SKU 参数表 |
| 减速比 | UNKNOWN | 本地资料无精确 SKU 参数表 |
| 额定电流/空载电流/堵转电流 | UNKNOWN | 本地资料无精确 SKU 参数表；这会阻塞 TB6612 匹配结论 |
| 额定/堵转扭矩 | UNKNOWN | 同上 |
| 输出轴尺寸 | UNKNOWN（不能用 R3X 装配图反推精确电机规格） | 同上 |
| 底盘兼容证据 | R3X 孔位图标注有 MG513X 电机支架孔；阿克曼安装手册示例件写“12V30F MG513X 电机-霍尔” | `VERIFIED-IN-SOURCE-BUT-DIFFERENT-VARIANT`：三类孔位图 p.1；`R3X阿克曼底盘安装手册（20260718）.pdf` p.3、p.14。不得外推为 XP28/GMR 参数 |

## 5. 编码器（项目称 GMR 版本）

| 项目 | 事实 | 状态与来源 |
|---|---|---|
| 输出形式 | A/B 双通道，相位存在相位差，可判断方向 | `VERIFIED-IN-SOURCE`：`编码器波形与原理简述.png` 图中文字 |
| 供电范围（教程层） | 厂家测试说明写 3.3-5 V；输出高电平等于编码器供电电压 | `VERIFIED-IN-SOURCE`：`编码器测试相关说明.txt` 第 1-2 条；`编码器波形与原理简述.png` 底部说明 |
| 无示波器判据 | 电机转动时，万用表测 A/GND 或 B/GND，资料称约 1.5-1.8 V 为正常平均读数，且与转速无关 | `VERIFIED-IN-SOURCE`：`编码器无示波器情况排查方法.png`；`编码器测试相关说明.txt` 第 2 条。该方法只证明有跳变，不证明相位、频率或 CPR |
| HAL 计数方式 | TIM2/TIM4 编码器接口，16 位计数；例程每个采样窗读 `(short)CNT` 后清零 | `VERIFIED-IN-SOURCE`：GMR HAL ZIP `Core/Src/tim.c:81-115,185-219,410-420` |
| GMR 与霍尔例程差异 | 厂家说明主要是精度导致的目标计数与 PI 参数不同；HAL 代码对比只看到目标值/Gain 不同，其余核心实现相同 | `VERIFIED-IN-SOURCE`：`说明文档（必看）.txt` 第 1 行；GMR/Hall HAL 两 ZIP 的 `Core/Src/main.c:49-51` |
| 编码器型号、PPR/CPR、倍频定义 | UNKNOWN | 本地没有 MG513XP28_12V GMR 精确编码器数据页 |
| 每输出轴一圈计数 | UNKNOWN | 不能用示例目标 800 或 20 反推 |

## 6. 舵机

| 项目 | 事实 | 状态与来源 |
|---|---|---|
| 线序概述 | 红=电源+，黑/棕=电源-，黄/白=控制信号 | `VERIFIED-IN-SOURCE`：`WHEELTEC R3X系列底盘客户资料/.../R3X阿克曼车/注意事项.txt` 第 3 行 |
| PWM 脉宽 | 0.5-2.5 ms 对应正负极限，1.5 ms 为零点 | `VERIFIED-IN-SOURCE`：同文件第 3 行 |
| 机械装配要求 | 安装转向拉杆前先发送 1.5 ms 置中；否则左右转角可能不对称 | `VERIFIED-IN-SOURCE`：同文件第 5-6 行；`R3X阿克曼底盘安装手册（20260718）.pdf` p.7 |
| 舵机固定螺丝风险 | 安装手册指定 M3*5；长螺丝可能与内部齿轮干涉 | `VERIFIED-IN-SOURCE`：同安装手册 p.7 |
| 型号、供电电压、空载/堵转电流、PWM 周期 | UNKNOWN | 本地无舵机数据页；不要从通用舵机经验外推 |

## 7. R3X 底盘系列（不选择最终车型）

| 资料中的变体 | 可确认机械包络/关键尺寸 | 来源 |
|---|---|---|
| 三轮两驱 | 图纸给出约 145 mm 总宽、203.5 mm 总长、轮直径 65 mm；板面宽 119.2 mm | `R3X三轮两驱差速小车.pdf`，p.1 尺寸图 |
| 四轮两驱 | 图纸给出约 145 mm 总宽、203.5 mm 总长、轮直径 65 mm；板面宽 119.2 mm | `R3X四轮两驱差速小车.pdf`，p.1 尺寸图 |
| 四驱差速 | 图纸给出约 145 mm 总宽、203.5 mm 总长、轮直径 65 mm、同侧轮轴距 100 mm | `R3X四驱底盘.pdf`，p.1 尺寸图 |
| 阿克曼 | 图纸给出约 145.2 mm 总宽、230 mm 总长、轮直径 65 mm、前后轴距 141.7 mm | `R3X阿克曼底盘.pdf`，p.1 尺寸图 |
| 孔位生态 | 孔位图标注 TB6612、MG513X 电机支架、C30D/树莓派、Orin、TI 控制器、CCD/巡线和云台等孔位 | `1.孔位说明与孔位图纸/` 下三个 PDF，均 p.1 |
| 具体项目底盘 | UNKNOWN | 资料包包含多个变体，用户尚未指定/本次不冻结 |

麦轮包有 STP/DWG 和安装视频，但没有同层级的 PDF 总尺寸图；本次未把 CAD 模型尺寸外推为项目参数。

## 8. RDK X5

| 项目 | 当前结论 |
|---|---|
| 项目角色 | `PROJECT-CONTEXT`：上位计算平台 |
| 供电、电流、接口电平、通信接口、安装孔 | `UNKNOWN`：本地来源集中没有 RDK X5 官方资料 |
| 与当前 bring-up 的依赖 | `PROPOSAL`：电机开环、编码器测速和速度 PI 不依赖 RDK X5；先保持串口/通信层可替换，后续再接入 |

## 9. 目前允许写入固件配置的值

下面是工程建议，不是新的硬件事实：

```text
PWM_FREQUENCY_HZ = 10000
CONTROL_PERIOD_S = 0.010        # 必须实测验证
PWM_LIMIT = timer_arr           # 初始测试再加更低的软件限幅
ENCODER_COUNTS_PER_OUTPUT_REV = UNKNOWN
MOTOR_RATED_CURRENT_A = UNKNOWN
MOTOR_STALL_CURRENT_A = UNKNOWN
DRIVER_BOARD_REVISION = UNKNOWN
SERVO_CENTER_PULSE_US = 1500
SERVO_MIN_PULSE_US = 500        # 只来自底盘说明，仍须与实物型号核对
SERVO_MAX_PULSE_US = 2500
```

在 `UNKNOWN` 被补齐前，不允许把原始编码器计数称为 RPM，也不允许声称 MG513XP28_12V 与 TB6612 已完成电流匹配。
