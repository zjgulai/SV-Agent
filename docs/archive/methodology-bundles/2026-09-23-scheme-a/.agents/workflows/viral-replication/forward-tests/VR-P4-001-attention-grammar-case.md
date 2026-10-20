# VR-P4-001 Attention Grammar：独立前向测试场景

## 目的

验证新 workflow 能将一个稳定、非趋势、非促销、非 proof/experience 主导的参考样本，编译为只改变 `caption_cadence` 的受限合同；测试不要求媒体生成、真实平台数据、发布或 performance 结论。

## 输入

### ReferenceBundle

- `reference_id`: `ref-attention-forward-001`
- `source_digest`: `sha256:fixture-only-attention-forward-digest`
- platform: `short_video`
- playability: 初次与刷新均可播放，capture 可复现。
- rights: `confirmed_for_internal_analysis_only`；目标表达只使用已授权的 target assets 和 target sound policy。
- Performance Window: `view_count=18000, state=observed`；`retention_rate=not_reported`。

### DecompositionMap

| 时间范围 | component | 可观察功能 | 表层处置 | Pattern anchor | source ref |
| --- | --- | --- | --- | --- | --- |
| 0.0–0.8s | `hook_trigger` | 先展示目标结果局部，再提出问题 | target 改写 | `shot=0, hook/problem, budget=2s` | `obs://fixture/forward-frame-001` |
| 0.8–1.6s | `caption_cadence` | 第一条字幕只给出问题的一半 | target 改写 | `shot=0, hook/problem, budget=2s` | `obs://fixture/forward-ocr-001` |
| 1.6–2.0s | `caption_cadence` | 第二条字幕完成解释 | target 改写 | `shot=0, hook/problem, budget=2s` | `obs://fixture/forward-ocr-002` |
| 2.4–5.0s | `reveal_cadence` | 以固定顺序展示完整结果 | frozen | `shot=1, solution/demo, budget=4s` | `obs://fixture/forward-frame-002` |

PatternHypothesis 声明：`primary_mechanism=attention-grammar`；本次只检验 `caption_cadence` 的时序/分块功能，不主张它提高留存或播放。

### Target Fact 和合同

- target Snapshot: `snap-attention-forward-001`
- eligible Fact: `fact-temperature-display-confirmed`，文案可表达“屏幕显示温度读数”。
- excluded Facts: 空集合。
- frozen Pattern anchor: `problem_solution`、version `1.3`、15 秒、`zh-CN`；phase sequence 为 `hook → solution → cta`，shot plan 为 `hook/problem/2s → solution/demo/4s → solution/result/5s → cta/cta/4s`。
- Control 与 Variant 固定：Snapshot、Fact 集合、平台、市场、时长 15 秒、语言 `zh-CN`、Pattern Definition、模型、目标素材、声音政策、Hook、reveal cadence、visual contrast、预算。
- 唯一变化：`caption_cadence`。
  - Control：两条 target caption 分别在 0.8s、1.6s 出现。
  - Variant：三条等义、fact-bound target caption 分别在 0.8s、1.2s、1.6s 出现。
- 请求 Finding：记录合同可否进入下一 gate 及其证据限制；不请求 retention、view、conversion、winner 或 production 结论。

## 独立评估要求

使用 `routing-decision-tree.md`、`04-attention-grammar/SOP.md`、`viral-attention-grammar`、`viral-fact-mapping` 与 `viral-replication-contract` 独立判定 disposition。输出：primary mechanism、selected component、blockers、允许下一步、不可得结论和 evidence level。

## 预期验收

`ready_for_next_gate`：只有 `caption_cadence` 改变，参考/目标 surface 已分离，target claim 有 confirmed Fact，且 Finding 仍明确 `retention_rate=not_reported`。
