# Viral Replication Workflow Packs

这是方案 A 的 workflow 编排层。每个目录包含一个权威 `SOP.md` 和一个 `skill-map.md`；实际可发现的 skills 位于 `.agents/skills/`，不在 workflow 内复制。

## Routing

先读取 `routing-decision-tree.md`，为一个 Reference 选择唯一 `Primary Replication Mechanism`。再读取对应 SOP，按 skill-map 顺序执行。跨 workflow 只允许通过已定义 artifact handoff，不能直接共享未审计的模型输出。

六类主机制统一使用以下顺序：

```text
ReferenceBundle
→ DecompositionMap
→ PatternHypothesis
→ ReplicationPlan
→ FactMap
→ immutable ReplicationContract
→ AdaptationPackage
→ ScriptVersion
→ StoryboardVersion
→ MediaIntegrityRecord
→ ReplicationFinding
```

`ReplicationPlan` 是合同冻结前可修订的 workflow planning state；`AdaptationPackage` 是六类现有机制输出的统一 handoff 名称。九类新增 artifact 的 executable machine-schema authority 是 `apps/api/app/domain/sv_agent/artifact_contracts.py`；`tools/viral_replication/artifact_contracts.py` 只兼容导出同一实现。PostgreSQL 已有不可变 envelope 与只读投影，但仍没有 Artifact writer。任何 workflow 都不得跳过 `viral-media-integrity` 直接进入 ReplicationFinding，也不得把这条顺序解释成 render、publish、rights、commercial 或 production capability。

## Current packs

- `01-narrative-transformation`：问题—转折—解决—结果的叙事迁移。
- `02-proof-demonstration`：实验、对比、量化或物理演示迁移。
- `03-experience-pov`：POV、ASMR、感官与动作连续性迁移。
- `04-attention-grammar`：Hook、信息揭示/镜头节奏、字幕节拍、视觉反差或声音时序迁移。
- `05-conversion-action`：决策异议、Promotion Fact、CTA invitation 与受限 action-path 状态迁移。
- `06-trend-native`：有界趋势信号、共享语境、挑战/模板结构或音频功能的单组件迁移。
- `07-media-integrity`：在任一已冻结的主机制合同之后，独立审计 artifact、技术、声画表达、目标身份、来源使用范围和原创差异。

`04-attention-grammar`、`05-conversion-action`、`06-trend-native` 和跨机制的 `07-media-integrity` 已完成文档级 workflow、fixtures 与独立前向测试入口。`07-media-integrity` 不增加新的主机制或 Creative Dimension；它用 `MediaIntegrityRecord` 将 artifact 溯源、技术规格、声画表达、目标身份连续性、来源使用范围、原创差异拆成六道互斥 gate。任何其中一项通过都不替代另一项，更不证明音频/模板许可、法律结论、商业批准、平台兼容、媒体生成、外链/下单、上传、发布或 production acceptance。

## Adversarial fixtures and forward tests

`fixtures/` 保存无私有数据的输入/预期处置样本，用于验证每个 workflow 是否在证据不足时 fail closed；`forward-tests/` 保存独立 agent 可复跑的场景和验收口径。

- `fixtures/README.md`：夹具字段、三层验证边界、消费顺序、SV-004 六机制矩阵和 P3/P4 风险覆盖。
- `forward-tests/VR-P3-006-proof-demo-case.md`：证明型复刻的独立前向测试场景。
- `forward-tests/VR-P4-001-attention-grammar-case.md` 与 `VR-P4-001-attention-grammar-result.md`：注意力语法的独立前向测试场景、首次 anchor blocker、修正与复测结果。
- `forward-tests/VR-P4-002-conversion-action-case.md` 与 `VR-P4-002-conversion-action-result.md`：转化行动的独立前向测试场景、Promotion 生命周期、CTA/provider ownership、action-path 边界与单变量处置结果。
- `forward-tests/VR-P4-003-trend-native-case.md` 与 `VR-P4-003-trend-native-result.md`：趋势机制的独立前向测试场景、TrendAdmissionRecord、source audio/template substitution、platform capability 与原创差异交接结果。
- `forward-tests/VR-P4-004-media-integrity-case.md` 与 `VR-P4-004-media-integrity-result.md`：跨机制媒体门的独立前向测试场景与复测结果；唯一可继续的输出是有范围的 document-level preflight，artifact review、权利、原创、商业、平台和发布仍保留为独立 gate。
- Fixture oracle 只验证 fixture shape、路由、claim boundary、stop condition 和 workflow expectation；只有另行调用 canonical validator 才能报告 artifact contract acceptance。两者都不证明真实媒体生成、平台表现或 production acceptance。
