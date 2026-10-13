# 系统复用与 RDK 最小链路：首轮证据及实施提案

任务 [#11](https://github.com/Sisu-z/smart-car-parking/issues/11)，修订 r1，run_id `SYS-20261013-01`；2026-10-13。依据 main `838d61d14cc0383e8ade947f1c7bdaacdf882398`（PR #16）、DEC-013～020及固定团队指南 v0.3.0。本篇是计划附录，状态 **[DESIGN / UNVERIFIED-ON-HARDWARE]**；接受与任务状态仅看原 Issue。所有新模块、字段、进程和阈值均为提案，未改变正式接口。

**暂定建议**：保留 STM32 确定性执行/安全边界；RDK 从已有单 USB 相机、CPU 图像算子和离线资产起步，先回放，再无执行器连接的影子运行。借鉴 F1TENTH 的车辆抽象、Duckietown 的视觉分层、RDK 的取流适配，分别补差距。三个来源没有一个证明本车已实现普通线随机找位、倒库及独立出库；本轮不整套移植、不安装 ROS2/模型栈、不冻结多摄。

## 1. 已有资产与真正缺口

本车阿克曼、X5 8GB、单标称90°相机、约15cm车宽是 PROJECT-CONTEXT；视野/几何/电源未实测。日常约宽1～1.5m、长2～3m不等于最终地图；新增预算优先1000元，不能据案例采购。附件是历史资料，现行约束以本轮 main 为准。

| 基线文件/检查位置 | 可直接复用 | 必须补的能力 |
|---|---|---|
| [slot_cli.py](../../offline/slot_cli.py) `frames/run`；[slot_lines.py](../../offline/slot_lines.py) | 本地媒体→LSD/U形候选→叠图、manifest；标定摘要、图像哈希、split | 在线取流、真实采集时刻/队列龄期、普通线语义/跟踪/占用。图片无时间，录像 POS_MSEC 仅媒体时间；仍保持 valid_for_control=false、occupancy=UNKNOWN |
| [dataset_audit.py](../../offline/dataset_audit.py) `audit`；[calibrate_camera.py](../../tools/calibrate_camera.py) | 场景/完全重复图泄漏检查，固定相机离线标定入口 | 独立实拍标注与误差评估；改名场景/相邻帧不能靠哈希查出；固定平面投影不能直接支持云台/镜面 |
| [parking.py](../../offline/parking.py) `plan/run_scenario/run_exit_scenario`；[third_party](../../third_party/README.md) | 固定 PythonRobotics `08b453a8e3b7a161b6fbbe6b73737758a8ec3482`（MIT）、几何规划、模拟跟踪、独立重规划出库 | 真值输入隔离；真实相对位姿/空间质量、搜索、入口跨越/扫掠、业务状态机。仿真尺寸/超时不复制进实车配置 |
| [analyze_log.py](../../tools/analyze_log.py) `analyze`；[run_offline.py](../../tools/run_offline.py) | V0遥测非法行/无效RPM/故障位/间隔分析、现有回放页与回归入口 | RDK事件时间线及命令关联。20Hz遥测间隔不能证明100Hz控制周期；电脑通过不能证明物理停稳 |

上述是本轮源码静态核查，未重跑历史控制/视觉测试。[pyproject.toml](../../pyproject.toml)要求 Python >=3.12,<3.14，依赖为 headless OpenCV；板上 Python/包/ABI未知，且不能直接运行依赖 `imshow` 的GUI示例。先清点已有环境，版本不合则登记兼容缺口，由后续授权任务适配，不能本轮安装解决。

## 2. 三个原作者系统：成果、差异与复用等级

### 2.1 F1TENTH：阿克曼车辆的系统分层

原作者构建案例是 Traxxas Slash 4x4 + Jetson Xavier NX + VESC/BLDC驱动及舵机、LiDAR，使用LiPo和配套供电板；不是本车直流编码器电机/TB6612/STM32。官方自主入口要求先完成车辆构建、遥控及里程计标定，由自主节点订阅传感数据并发布速度/转向；需按住自主使能键。**驱动栈提供自主接入和遥控链路，不自带本任务完整找位/泊车算法**。[F1资料]描述原作者可运行条件；本轮未复现。

实核 `jazzy-devel@cffbbd7a89d14d59bfd6123d8abdc5ad4d955105`：[README/launch/config](https://github.com/f1tenth/f1tenth_system/tree/cffbbd7a89d14d59bfd6123d8abdc5ad4d955105/f1tenth_stack)。`bringup_launch.py`连接 joy、mux、ackermann_to_vesc、vesc_driver、vesc_to_odom、LiDAR/TF；`mux.yaml`区分控制来源及超时；`vesc.yaml`映射 m/s→ERPM、rad→舵机值，并可用舵机命令估计转向。命令角不等于实际轮角。官方标定要求方向、转向中位/增益、速度比例的独立测量；案例长直线/半圆测试不能照搬进本项目小空间。

- **仅借鉴**：车辆级目标→驱动适配→反馈/里程计的分层；显式控制权、新鲜度、标定版本和调试观察点。不能把软件mux或手柄键当独立断能。
- **需适配**：本车输出轴RPM/CPR、轮位、实测转向/回差/轴距，不能照搬 ERPM、电流、增益、限速、TF和超时常量。
- **本轮不引入**：VESC驱动、Jetson镜像、LiDAR定位/SLAM、整套ROS2驱动栈。去掉LiDAR也不会自动补出相机找位能力。
- **版本/许可**：系统顶层MIT（固定提交LICENSE），子模块/依赖需分别核；文档页CC BY-NC-SA 4.0不等于代码许可。旧 `ros2` 查询指向 `ros2-roadmap`，后者404，停止追该入口；当前README仍混合Foxy/Humble与Jazzy分支信息，不能作为X5 Humble安装配方。本轮无代码复制/依赖导入。

### 2.2 Duckietown LF：最贴近视觉循迹，但不是阿克曼泊车

[DT资料]的 `ente` LF 实车演示是在已校准Duckiebot、可见车道线、标准Duckietown道路和良好漫射照明下自主循迹；由键盘启停。该演示范围排除障碍/路口/其他车辆，不能推成随机姿态主动找位或倒车。原车前视相机、差速双DC电机；DB21系列用Jetson Nano，含编码器/IMU/ToF与专用Duckiebattery。本车没有后两类传感器，也没有标准场景或同款电源，不能借用其安全/续航结论。

实核 `ente@0b91e7da68a9cdbb6df9ab7183ce5c3ecf47b077`：[lane_following.launch](https://github.com/duckietown/dt-core/blob/0b91e7da68a9cdbb6df9ab7183ce5c3ecf47b077/packages/duckietown_demos/launch/lane_following.launch)及 `packages/{line_detector,ground_projection,lane_control}/src/*_node.py`。链路是压缩图像→颜色线段→内外参地面投影→车道位姿估计→v/omega→差速执行，ROS1/rospy与Docker/DTROS组织；逐层有调试图，检测/控制保留源消息时间。

- **仅借鉴**：像素→米制→带质量的位姿→控制逐层验证；图像/标定/控制关联回放；按真实光照调参后留独立场景验证。
- **需适配**：两条道路边界的实际颜色/宽度/曲率、普通车位语义、阿克曼转向与倒车约束；不能把差速omega或轮命令直接映射舵机，不照搬固定速度/增益。
- **不值得引入**：duckie-OS、全套Docker/ROS1/DTROS、标准瓦片地图；AprilTag/Autolab定位不进入本项目运行链路。现有OpenCV投影/检测先用，避免换平台重做。
- **许可未闭合**：固定提交 `packages/lane_control/package.xml`标GPLv3；根 `LICENSE 2.0.pdf`实取为Git LFS指针（对象SHA256 `47e23ce4f2f7ea36f7b19deda363834caa13b2e859b59610ec102d2848b5aae2`），未取得正文；官网许可页也未呈现可读条款。不能认定整栈MIT或许可一致。本轮不复制其实现，直接引入前由后续任务取得准确许可及依赖通知。

### 2.3 RDK官方：取流/发布/推理的运行案例

[RDK资料]的X5 USB案例实现相机取流与显示；另一官方例程接USB→模型推理→显示检测框，`hobot_usb_cam`实现V4L2→ROS2图像/相机内参。**均没有本项目车位识别、泊车控制和多摄实时性验证**。演示画面/官方日志只是作者证据，本轮没有X5运行结果；YOLO通用目标框也不是车位入口/空闲空间证明。

固定 `rdk_doc@2ab42f3c295c1dd1fa94fbf0df24a81442cd642b`，USB采集支持表给X5 Ubuntu22.04/Humble；硬件介绍“供电接口”要求支持5V/5A适配器，禁止电脑USB供电；“USB接口”四个Type-A经HUB扩展。现用电源/线缆仍UNKNOWN，端口数量不证明多摄总带宽或供电足够。

实核 `hobot_usb_cam@1edaad9a5ff3063bb71aa7d68a46331dfcdcb40a`（package.xml 2.3.1）：`src/hobot_usb_cam.cpp` mmap/userptr取V4L2 buffer timestamp；`include/hobot_usb_cam/utils.hpp`用进程启动时epoch偏移转换时间；`src/hobot_usb_cam_node.cpp`向消息传递时间并发布。必须验证实际驱动时钟/缓冲/时间戳语义，不能宣称是曝光时间或已同步多摄。README的默认尺寸/话题描述与launch不完全一致：固定launch为960×480、30fps、MJPEG、video8，node的MJPEG分支发布CompressedImage；不能复制默认值或凭README猜消息类型。

- **可直接依赖（有条件）**：已有兼容OpenCV/V4L2后端用于单摄读取；若板上已装且兼容，可评估官方USB节点作替代适配器。相机格式/尺寸/帧率和设备身份必须实查。
- **需适配**：设备身份、逐帧时间语义、有限队列、失效/退出、标定和headless诊断；不是直接运行GUI/NPU演示就接控制。
- **不先引入**：tros完整链路、hbmem零拷贝、Web直播、YOLO模型转换。仅当测得瓶颈/算法需要时再议。
- **许可**：rdk_doc及USB包顶层Apache-2.0；USB node/utils保留Bosch BSD条款。包许可不覆盖所有模型/运行库，导入时逐件核对并保留归属。本轮只引用。

## 3. 最小运行链路与中间件选择（提案）

| 角色 | 实现增量与输入/输出 | 首轮实施后如何验 |
|---|---|---|
| capture适配器 | 仅拥有指定单摄；读帧→身份/序号/时间/图像。对实际支持格式选一低负载模式，读回设置；保留驱动缓冲诊断 | 电机动力断开且另获设备授权后测真实fps、断帧、读阻塞；不误开另一个video节点 |
| perception/任务worker | 先直接调用现有 `slot_lines.analyze`；最新帧信箱容量1，处理慢则统计丢帧；未来接算法#12已审查接口 | 与离线同帧/同配置比对；输出仍候选/UNKNOWN，不发车辆命令；规划耗时不阻塞取流 |
| supervisor/command gate | 独立于视觉阻塞地检查进程、观测/反馈龄期和模式；首版唯一输出为内存dry-run sink，不打开串口 | 注入超时/退出/重启/乱序，拒绝旧目标和自动恢复；生成事件证据 |
| link适配器（后续） | 仅在M2/契约审核后把车辆级目标映射正式帧，接受反馈/故障/已接受序列；不让PARK/EXIT变PWM | 替身STM32先测；V0单电机协议只调试，不拼成联合底盘；不确定feedback不得报停稳 |
| bounded recorder | 非阻塞记录事件、指标与有限图像/录像，满队列丢诊断并计数；磁盘配额/结束摘要 | 磁盘满/写入失败可退出诊断，不能阻塞控制；关键证据缺失则本次验收无效 |

逻辑模块先保持纯函数、统一米/rad和项目坐标；部署优先少量轻量进程：阻塞取流隔离、视觉/任务worker、独立监督与可选link。共享最新帧或有限IPC的具体方式待性能检查，不能用无界队列保存旧画面。进程重启只回待命，不续上次运动。未来STM32本机超时/故障锁存必须独立保留；Linux监督不是物理断能。

| 路径 | 当前收益/成本 | 选择条件 |
|---|---|---|
| 轻量Python进程 + 已有OpenCV/JSON日志 | 最快接既有离线资产；需补进程监督/背压/回放时钟，Python版本适配待核 | **暂定首选**，先证明单摄影子链路和可诊断性 |
| 已装tros/ROS2 + 官方USB节点 | 可用驱动/话题/rosbag；存在消息/编码、DDS队列、时钟、Python/ABI和依赖成本 | 仅当已有环境或测得具体收益；recording验证与命令topic隔离，回放不连执行器 |
| 新装ROS2/SLAM/大型仿真栈 | 当前没有解除普通线语义/盲区/电源门槛的证据 | 不作为前置；另立授权和明确收益后再议 |

## 4. 时间、回放、性能与故障验收

**时间字段提案**：每帧保存 camera/mount/calibration ID、frame序号、驱动时间及其clock_domain/语义、RDK monotonic接收/处理起止时间。OpenCV `read()`返回后打戳只能叫接收时间，不能假装曝光时间；`POS_MSEC`只用于录像。无可信采集时间或缓冲上界时，只量接收后处理耗时，真正观测龄期未知，不批准运动。未来MCU报文附RDK接收时刻；未同步MCU/RDK时钟不能相减。session/sequence/checksum及新鲜度沿用契约草案方向，字段/频率/超时待总监与#15审查。

**记录/回放增量**：沿用现有manifest，旁挂本地事件JSONL（提案，非V0协议）：session、源帧/观察ID、标定/配置/提交、时间域、阶段/拒绝原因、候选、车辆目标dry-run、发送/接受序列及反馈fault。只存逻辑相对媒体索引，原图/视频/设备原日志留local/results不公开；有配额和RUNNING/COMPLETE/FAILED摘要。重放以保存事件时刻驱动可注入时钟，禁止用回放速度掩盖超时，禁止导入真实串口适配器；1倍/暂停/单步只影响查看。真实视觉→候选回放与真值规划仿真分别标注，不能拼成相机闭环成功。

**指标**：取流间隔、驱动帧丢失/worker丢帧、读阻塞、队列深度、解码/感知/规划/日志耗时、可信条件下观测龄期、命令到ACK/反馈的同域往返；报告样本数、p50/p95/p99与最大值。并记每进程CPU/RSS、系统空闲、温度/频率（已有接口可用时）、磁盘写量。USB拓扑/格式/分辨率/压缩/实测fps同时登记；Web显示延迟不代表控制延迟，fps不代表最坏时延。

上板影子试验拟每模式短测及一次约10分钟稳定运行；这是采样提案，不是安全阈值。用实际帧率和候选负载比较低分辨率/原始与MJPEG，限定模式数，失败三次无新证据即记录。先关闭直播/逐帧叠图，再看CPU是否仍不足；无证据不增加相机/NPU。速度、停止包络、误差/间隙到齐后，预算检查 `v_max × 观测/链路最坏延迟 + 实测停止距离 + 定位/车身余量 < 已确认可通行余量`；这是保守筛选，不代替动态障碍或完整扫掠证明。阈值在试验前审查冻结，不能借用仿真0.25s或F1 0.2s。

| 故障注入（先替身/回放） | 必须观察到的退出 | 仍需现实证明 |
|---|---|---|
| 断帧/冻结帧号/旧戳、worker阻塞/崩溃 | 拒绝新目标、FAULT/停止请求；恢复也需显式新会话/使能 | 不能仅凭新receive戳发现相机冻结；曝光年龄/缓冲证据缺失保持未知 |
| link丢失、ACK缺失/乱序/跨重启旧帧、无效RPM/里程计 | 旧目标不续租；停止请求与STOP_NOT_CONFIRMED分别报告 | STM32独立超时和实际停止/断能，不能声称一次STOP确保停稳 |
| 超负载/磁盘满、CANCEL、未知/遮挡通路 | 日志不拖住监督；拒绝/退出，不将UNKNOWN变FREE | 单前摄的侧后盲区与通路质量仍由#12/#13证明 |

## 5. 前两个低成本验证与依赖

**验证A：离线闭环证据链（无需设备/新采购）**。在已有合规环境，用可信本地dev与独立validation媒体，每批≤30帧，按[offline用法](../../offline/README.md)运行 `python -m offline.slot_cli`（包含scene-id/split/output），再 `python -m offline.dataset_audit`检查两批manifest；已有冻结环境可加 `uv run --frozen`，缺包/子模块只记阻塞、不安装。审叠图/候选/负例、失败摘要、标定ID与哈希；候选始终不可控制、UNKNOWN。未来另获实现授权后加时间/故障dry-run事件回放，验重复帧、暂停/超时、损坏记录不触发执行器。无实拍可继续合成/替身并明确标签；退出条件是得到一份可复现的输入→候选→拒绝/诊断链，不能算识别或泊车达标。

**验证B：单摄RDK影子链路（本轮仅计划）**。电源#14审核、设备权限/连接另获授权后：清点板型/镜像/内核/Python/OpenCV/tros/可用空间；若已有v4l2-ctl则查指定相机的formats/intervals与USB拓扑，不执行安装。仅使用现有兼容后端读取单摄，有限采样、记录实际格式/时间/CPU/RSS/温度/队列，输出现有候选及dry-run，电机动力断开且不打开串口。读失败/进程退出/超负载先用替身注入，不故意制造供电故障。退出条件：身份/模式可重复、性能报告可复核、旧帧能拒绝、回放可对齐；时戳/队列不可证则只接受“取流/候选验证”，拒绝升为运动准入。当前无设备数据，A/B均未实际执行。

| 需要谁提供/接受 | 准确输入 | 解锁/仍阻塞 |
|---|---|---|
| 算法#12 | 车道/车位/空闲/相对位姿输出及质量/龄期需求；搜索/倒库/出库阶段所需视野；允许拒绝条件、负载样本 | 确定worker与性能试验；不要求先训练模型，不接纳真值作运行答案 |
| 机械#13 | 车身包络/轴距/转向极限与回差、camera-mount坐标和实测视场/盲区、安装是否固定 | 标定/地面投影、时延空间预算及单摄是否够；不给最终地图/多摄采购结论 |
| 电源#14 | 实物X5板型、现用台架/车载候选电源与线缆、5V轨能力/动态负载、USB相机余量和独立断能 | 验证B供电准入；官方5V/5A要求不是已购/实测电源树，不能从Type-C电池推定够用 |
| 固件#15 | V0与联合底盘差距、CPR/RPM/轮位/转向模型质量、命令/反馈/会话语义、停止/超时/故障证据 | link替身及未来M2；UART/CAN、电平/帧格式/频率不在此冻结 |
| 总监询问用户 | 相机铭牌与现用镜像/供电；可用采样/标定工具、固定方式、地面照明/展示条件和独立场景可用性 | 只问会改变下一步的缺口。未答保持候选；采购/加工/地图/目标调整必须先确认 |

本轮范围到此：三来源核查、差异、最小链路、两项验证和依赖；不扩大到实施代码、整套框架安装或最终硬件选型。提交专题PR后停待总监审查；其他窗口未确认采用前不声称同步/已冻结。

## 来源定位与验证记录

- **[F1资料]** 原作者 [构建](https://f1tenth.readthedocs.io/en/main/getting_started/build_car/index.html)、[自主入口](https://f1tenth.readthedocs.io/en/main/getting_started/driving/drive_autonomous.html)、[里程计标定](https://f1tenth.readthedocs.io/en/main/getting_started/driving/drive_calib_odom.html)。代码固定提交见上，检查 README、LICENSE、.gitmodules、bringup_launch.py、config/{vesc,mux,joy_teleop}.yaml；动态文档核查日2026-10-13，不混作锁定发行版。
- **[DT资料]** 原作者 [LF前提/启停/调试](https://docs.duckietown.com/ente/duckietown-manual/40-demonstrations/lane-following-lf.html)、[平台](https://duckietown.com/platform/)、[型号表](https://docs.duckietown.com/ente/duckietown-manual/99-further-reading/duckiebot-configurations-explained.html)。固定代码 [dt-core](https://github.com/duckietown/dt-core/tree/0b91e7da68a9cdbb6df9ab7183ce5c3ecf47b077)，文件定位见2.2；根许可正文获取缺口保留，不凭搜索摘要认定许可。
- **[RDK资料]** 原作者 [X5单摄显示案例](https://developer.d-robotics.cc/x5_cases_doc/en/getting_started/usb)，[固定官方文档树](https://github.com/D-Robotics/rdk_doc/tree/2ab42f3c295c1dd1fa94fbf0df24a81442cd642b)：`docs/01_Quick_start/hardware_introduction/rdk_x5.md`供电/USB章节，`docs/05_Robot_development/02_quick_demo/demo_sensor.md`USB采集支持表/准备/用法/标定，`docs/03_Basic_Application/04_vision/RDK_X5/usb_camera.md`示例简介；[固定USB包](https://github.com/D-Robotics/hobot_usb_cam/tree/1edaad9a5ff3063bb71aa7d68a46331dfcdcb40a)的README、LICENSE、package.xml、launch及源码位置见2.3。

实际执行者为本可见系统窗口；环境是GitHub连接器/官方网页及scratch文本检查。实读main/Issue/源码、官方文档和版本许可标识，已建立独立分支和原Issue检查点；远端文件/PR提交结果另回填Issue。没有安装、连设备、烧录、运动、编译或仿真复跑；实车/原作者复现、X5性能/多摄、真实视觉与停止均未验证。本篇未复制第三方实现/模型/厂家包/私图，未改中央真源、代码或正式契约。
