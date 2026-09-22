# TUNE-YYYYMMDD-NN——速度环调参记录

- 固件/配置 ID：
- 硬件配置 ID：
- 电机侧：Left / Right
- 车轮状态/负载：
- 供电电压/电流限制：
- 实测控制周期：
- 遥测周期：
- 每输出轴一圈计数及来源：

## 控制器配置

| 参数 | 数值 | 单位 |
|---|---:|---|
| Kp | | normalized duty / RPM |
| Ki | | normalized duty / (RPM·s) |
| Kd | | normalized duty·s / RPM |
| output min/max | | normalized duty |
| integral min/max | | normalized duty |
| slew/ramp | | 每次更新或 RPM/s |

## 目标曲线

```text
time → target RPM
```

## 实测响应

- 上升时间：
- 超调：
- 稳态误差：
- 稳定时间/振荡：
- 饱和持续时间及恢复：
- 电压/电流/温度：
- VOFA+/CSV 证据：

## 结论

- `[TESTED-PASS] | [TESTED-FAIL] | [INCONCLUSIVE]`
- 一个解释：
- 下一次只修改一个参数：
- 是否提升为项目默认参数：`NO`，除非已经独立复测并通过 Review。
