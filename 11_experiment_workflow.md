# 11 轻量实验记录流程

实验记录的目的，是让下一次测试可以复现，而不是增加管理负担。

## 只保留三类记录

1. `HARDWARE_CONFIG_TEMPLATE.md`：物理配置改变时保存一次快照。
2. `EXPERIMENT_LOG_TEMPLATE.md`：一次实验只回答一个问题，记录条件、证据和结论。
3. `TUNING_RECORD_TEMPLATE.md`：只用于 P/PI/PID 调参。

模板位于 `templates/`。

## 命名方式

```text
records/
  hardware/HW-YYYYMMDD-01.md
  experiments/EXP-YYYYMMDD-01-short-name.md
  tuning/TUNE-YYYYMMDD-01.md
  captures/<相同 ID>/...
```

第一次产生真实记录时再创建这些目录，不预填虚假测量。

## 最小流程

1. 复制硬件配置模板，拍照并记录板版本与接线。
2. 只提出一个问题，例如：“Motor A 能否按 ±0.10 duty 正确启停？”
3. 上电前先写清通过、失败和立即停止条件。
4. 执行一次受控测试，保存原始日志、示波器或逻辑分析仪证据。
5. 只有准确配置和行为得到证据时，才能标记 `[TESTED]`。
6. 写下唯一的下一步。若硬件事实或决策变化，同步更新共享文档。

## 证据等级

| 证据 | 能支持的状态 |
|---|---|
| 代码存在或可以编译 | `[IMPLEMENTED]` / `[BUILD-VERIFIED]` |
| 主机单元测试 | 只支持纯逻辑的 `[HOST-TESTED]` |
| 示波器/逻辑分析仪波形 | 支持对应引脚与频率的 `[TESTED]` |
| 台架测量 | 支持该硬件配置下的 `[TESTED]` |
| 多次带载运行 | 支持已测试运行范围内的 `[TESTED]` |
| 团队此前口述但没有保留证据 | `[TESTED-BY-TEAM]`，不是本轮独立复现 |

## 更新规则

- 未知项得到可靠证据后，更新 `01_hardware_source_of_truth.md`；若影响方案，同时更新决策和配置。
- 新冲突写入 `05_open_questions_and_conflicts.md`；仍未解决时同步到 `OPEN_QUESTIONS.md`。
- 某阶段通过后更新 `HANDOFF.md` 与 `NEXT_ACTIONS.md`。
- 历史实验记录不回写修改；新结果创建新记录。
