# 普通车位线与泊车离线工作台

更新：2026-09-23。`[IMPLEMENTED][EXPERIMENTAL]`；电脑端测试范围见 HANDOFF。没有真实相机效果、真实控制或跨场地成功率证据。

## 这轮能实际运行什么

1. 本地图片/录像 → OpenCV LSD 线段 → 几何合并/筛选 → 普通 U 形线框候选及入口假设 → 诊断叠图/JSON。
2. 有固定安装相机的真实内参与地面测量对应点时：去畸变 → 单应变换 → 覆盖区域内鸟瞰 → 米制几何候选。禁止越出标定凸包外推。
3. 现有 PythonRobotics Reeds–Shepp 增加末段方向约束；与原 C 速度环/跟踪器跑模拟停车，再从实际模拟停稳点重新规划出库；出库目标被占用时拒绝。
4. 固定种子 24 个随机位置/朝向的几何规划检查；不是随机搜索，不是随机起点闭环成功率。

没有新增依赖包，没有自写线段检测器、标定算法、RS 规划器或另一份速度 PI。项目代码只做接口、几何假设筛选、边界和测试。

## 一条命令看合成演示

```sh
uv run --frozen python tools/run_offline.py
```

打开本地 `results/阶段一软件实验.html`：三组合成图像候选和倒库/出库/拒绝的轨迹链接；原七场景仍在 `results/离线验证结果.html`。这些是普通 HTML 本地回放，不是实车控制台。首次复跑需要按根 README 初始化子模块和依赖。

## 接入自己的实拍图片或录像

仅接受可信的本地文件/图片目录，不打开摄像头、不枚举设备、不连接网络视频，也不发送电机命令。原始媒体放 `data/raw/` 或 `local/`，输出放 `results/`；这些默认不上传 GitHub。

```sh
uv run --frozen python -m offline.slot_cli data/raw/session-a \
  --scene-id room-a-session-a --split dev --output results/slot-session-a

uv run --frozen python -m offline.slot_cli data/raw/session-b.mp4 \
  --scene-id room-b-session-b --split validation \
  --max-frames 30 --stride 15 --output results/slot-session-b

uv run --frozen python -m offline.dataset_audit \
  results/slot-session-a/manifest.json results/slot-session-b/manifest.json
```

输出目录必须是新目录，不能位于图片输入目录内；避免覆盖旧证据或把结果再次当输入。每批输出叠图与 manifest，包含场景/split、图像哈希、媒体时间、OpenCV 版本、检测配置、标定摘要和候选。处理失败有 FAILED 状态，不把半批成功冒充整批通过。

视频默认至多 30 帧，每 15 帧取一次；允许上限 200 帧、间隔 300。图像边长限制 16～4096，鸟瞰最多 2048。它不是恶意媒体解码的内存/墙钟沙箱；不使用不可信巨型文件。统一复跑入口的每步另有 120 秒限制。

数据集检查仅查同名场景和完全相同图像跨 split；不能发现改名房间、裁剪图或相邻帧泄漏。必须按房间/采集会话分组，不能随机拆相邻视频帧。通过数据集检查不等于识别精度达标，尚无带真值标注的实拍精度评测。

## 米制投影怎么准备（不允许猜参数）

1. 保持真实相机安装、分辨率、对焦不变，先用 `tools/calibrate_camera.py` 和实测格尺寸获得内参。低重投影误差仍需独立验证。
2. 在车体参考系中测量同一平面至少 4 个不共线点，记录其原始图像像素与地面 x/y（m）。必须正确逐点配对、覆盖将分析区域；+x 前、+y 左。它们是离线标定测量，不是每次停车时输入的车位答案。
3. 复制 `templates/GROUND_PROFILE_TEMPLATE.json` 到 `local/` 填实测值；空模板不可运行。地面点只确定固定安装的相机—地面映射，不提供运行时车位位置。更改相机安装须重新标定。
4. 添加 `--ground-profile local/ground-profile.json`。使用不同的独立测点检查尺度、符号与误差。四点完美拟合不证明配对/尺度正确；代码只能排除部分退化、地平线穿越和错配。

地面映射仅适用平面、固定相机和 pinhole 畸变模型；鱼眼/镜面/运动云台未支持。`camera_id/mount_id` 是人工登记，不自动证明图像来自该安装；调用者必须核对。遮挡、错误平面、错误尺度和反射仍可能产生错误几何。

结果 `corners_px` 位于当前检测画布：无标定时是原图像素，有标定时是鸟瞰像素。四角顺序为入口两端、后边两端；`slot_inward_yaw_rad` 是库内方向，不是车辆目标朝向。`corners_ground_m` 只有提供标定时出现，但状态仍 `CALIBRATION_SUPPLIED_UNVERIFIED`。

## 必须理解的限制

- 只检测三边完整可见的近矩形 U 形几何。地砖/图案也可能形成 U 形；无语义车位分类，无稳健遮挡/弱光/阴影能力。两平行线和闭矩形在这版保守拒绝，不代表现实里它们不是车位。
- 所有输出始终 `valid_for_control=false`，占用始终 UNKNOWN。没有多帧跟踪、时钟新鲜度、障碍或通路判断；不能直接传给真实停车控制。
- 参数是像素实验阈值，不是所有相机/车位的通用标准。真实图像到位后按开发集调参，冻结后用独立集检验。
- 最后路径段为负速度方向，不等于已验证车身越过车位入口时全程倒车；还缺车位坐标边界、扫掠碰撞和任务状态机。
- 出库只复用规划/模拟跟踪，不包含实车 EXIT 命令、搜索、CANCEL、正式会话协议、未知空间感知或视觉闭环。不要把图片候选和真值仿真拼起来宣称全自主。

## 你下一次采样只需要准备这些

先不用添置摄像头。车辆断开电机动力/保持静止，把已有相机临时固定在拟安装位置，记录高度、俯仰、分辨率和安装照片。只在安全环境采集，不测试未验收车辆自主运动。

- 开发场景：同一普通车位的近/中/远、左/中/右视角；靠近入口与模拟倒库末端的视野；空地、地砖/反光干扰、被物品遮挡的负例。
- 每张图记录相机安装是否改变；手持变角度的图可做像素候选测试，不能套用另一安装的米制标定。
- 另一个房间/场景留作独立验证，不用它先调参。保留失败图，不只交成功截图。
- 不需要在运行场地放二维码或 AprilTag。棋盘与测量点仅在离线标定时使用；避开人脸、屏幕和寝室私人信息。

有上述样本后，才值得判断固定单相机是否够用、是否需要云台/镜面/第二相机，以及传统几何是否要升级学习模型。

## 开源来源与本轮技术调整

- [OpenCV LSD 官方接口](https://docs.opencv.org/4.x/db/d73/classcv_1_1LineSegmentDetector.html)：直接调用 `createLineSegmentDetector`，不复制底层实现。原 Canny/Hough 基线在透视重采样合成测试中碎线，有限排查后换用现成 LSD；未降低米制误差断言。
- [OpenCV 平面单应说明](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html)：复用 `undistort/undistortPoints/findHomography/warpPerspective/perspectiveTransform`，项目增加退化/覆盖验证。
- [OpenCV 许可证](https://github.com/opencv/opencv/blob/4.x/LICENSE)：上游 Apache-2.0；具体包与组件通知由锁定发行包保留。未复制旧许可冲突版本的 LSD 源码。
- PythonRobotics 固定子模块、MIT 归属与适配边界见 `../third_party/README.md`。原上游源文件未修改。
