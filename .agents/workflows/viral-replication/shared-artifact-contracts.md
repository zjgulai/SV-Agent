# Shared Artifact Contracts

六类 workflow 共享同一 artifact chain。九类新增 artifact 的 executable machine-schema authority 是 `tools/viral_replication/artifact_contracts.py`；它提供本地 JSON Schema projection、digest binding 和 validator。本文只解释 handoff 与证据边界，不复制第二套 machine schema。当前没有为这些 artifact 新增 PostgreSQL 表、migration、Task/Run runtime persistence 或外部写能力。

ScriptVersion 与 StoryboardVersion 是既有 FactFrame append-only artifact，不属于上述九类新增 schema；它们仍是 chain 中两个独立、连续的节点。

## Common envelope and status

每个新增 artifact 必须使用共享 envelope：`schema_version`、`artifact_id`、`artifact_type`、非空 `task_ref`、非空 `run_ref`、`version`、`status`、`input_refs`、`source_refs`、`subject_binding`、`content_digest`、`evidence_level`、`proof_level`、`limitations`、`created_at` 和可选 `supersedes_artifact_id`。本地 fixture 可使用有界 synthetic refs，但这些 refs 不证明 PostgreSQL Task/Run persistence 已存在。

Artifact status 是闭合集合：`draft`、`validated`、`awaiting_approval`、`blocked`、`approved`、`stale`、`superseded`、`final_with_limits`。它不替代 Run、ToolRun、Approval 或 Media Integrity disposition。

FactMap 与 ReplicationContract 使用 executable closed `claim_scope = product_claims | no_product_claims`；它不是 common-envelope 字段。本地 validator 验证 scope、subject binding、Fact-set 规则和两类 artifact 的跨链一致性：

- `product_claims`：必须使用 exact 或 reviewed Product Snapshot binding；FactMap 至少有一个 `confirmed`/`locked` bind，ReplicationContract 必须保留 selected Facts。非商品表达可以在同一 FactMap 中单独标为 `non_product_claim`。
- `no_product_claims`：仅用于完全不含商品声明的 Brand Voice / Social Resonance artifact；必须使用 `subject_binding.state=not_applicable`，Product Snapshot identity、claim mappings、selected/excluded Fact sets 和 unsupported claims 全部为空，limitations 明确边界。
- 只要 artifact 出现一个商品声明，就不得使用 `no_product_claims` 或用 `not_applicable` 绕过 Product Truth。

## Canonical chain

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

每个箭头必须保留 typed input ref、digest、subject/claim scope、source refs、limitations 和失败边界。标准完整执行链必须同时保留 ScriptVersion 与 StoryboardVersion；早期 bounded `preflight` 可只绑定其中一个 typed ref，此时 `storyboard_lineage=null`，该部分记录不代表完整链闭合，也不能进入 ReplicationFinding 或下一阶段。两个 ref 同时存在时，必须提供与顶层 refs 精确一致的声明式 `storyboard_lineage`。没有受控媒体 Artifact 时只能形成 bounded preflight。

## ReferenceBundle

必须固定 `reference_id`、source locator/digest、平台、Performance Window、捕获时间、rights/playability/candidate state、观察值、限制和 source refs。参考可播放不等于允许改编、媒体复用或发布。

## DecompositionMap

必须包含时间线、Hook、Pain/Tension、Narrative Beats、Proof Device、Experience Cues、Visual/Audio/Text Grammar、CTA、声明候选、unsupported claims、未知项和 primary mechanism。`mechanism_observations` 是以 `mechanism` 为 discriminator 的六分支 closed union：narrative beats、proof steps、experience cues、timed attention observations、conversion component observations 或 trend component observations。primary mechanism 唯一时，该字段必填且 discriminator 必须一致；`primary_mechanism=null` 的 ambiguous route 必须同时保持 `mechanism_observations=null`，再阻断或拆 Variant，不能伪造某一机制 payload。

Attention 分支保留 Pattern identity 与有时间范围的 observation；Conversion 分支完整列出四个 conversion components，并固定 `reference_surface_is_target_copy=false`；Trend 分支完整列出四个 trend components 与 source-reuse boundary，并固定 `target_execution_inclusion=false`。这些字段只闭合可观察 decomposition，不授权复用来源表层、平台动作或执行。

Attention 路由还必须保存 timed component、carrier、surface class、Pattern anchor 和 availability。Conversion 路由必须分开 objection、Promotion、CTA 和 action path。Trend 路由必须分开 `trend_signal_binding`、`trend_semantic_frame`、`template_grammar`、`audio_function`，并区分有界观察与 source identity/audio/template reuse。

## PatternHypothesis

必须拆分 `invariant_elements`、`replaceable_elements`、`prohibited_elements`、`adaptation_constraints`、evidence scope 和 unknowns。它是待验证机制，不是 winner、causal lift 或 Product Fact。

## ReplicationPlan

是合同冻结前可修订的 planning artifact。它必须记录唯一 Primary Replication Mechanism、唯一 selected component、Control/Variant、changed dimension、frozen configuration、目标平台/时长、execution budget、rights state、stop conditions、acceptance gates 和 human-approval requirement。它不能直接授权 provider、render、publish 或外部行动。

## FactMap

`claim_scope=product_claims` 时，必须将每个目标 claim 分为 `bind`、`exclude`、`non_product_claim` 或 `unsupported`，保留同一 exact/reviewed Product Snapshot identity、selected/excluded Fact sets 和证据 refs，并至少有一个 `confirmed` 或 `locked` Fact 进入 `bind`；`non_product_claim` 不得携带 Fact identity。`claim_scope=no_product_claims` 时，必须遵守上面的空 mapping、空 Fact set 与 `subject_binding.state=not_applicable` 规则。

## ReplicationContract

必须绑定 ReplicationPlan、FactMap、DecompositionMap，并冻结 Reference、Control、Variant、唯一 mechanism/component、语言、市场、平台、时长、配置、rights state、停止条件、验收门、approval ref 和 immutable state。其 `claim_scope` 必须与 FactMap 一致；`product_claims` 保留 eligible selected Facts，`no_product_claims` 保持 subject not applicable 且 selected/excluded Facts 为空。

Attention 合同冻结其余 attention components；Conversion 合同保持 Promotion、CTA ownership 和 action-path boundary 独立；Trend 合同冻结其余 Trend Components 与 TrendAdmissionRecord。任何一项都不代表 rights、platform、commercial、publish 或 production approval。

## AdaptationPackage

使用一个共享 envelope，并且只允许一个与 `primary_mechanism`、`selected_component` 一致的 typed mechanism payload：narrative adaptation、proof demonstration、experience POV、attention grammar、conversion action 或 trend native。它只把不可变合同编译成下一阶段输入，不是 mutable prompt bundle，也不产生媒体。

## ScriptVersion and StoryboardVersion

AdaptationPackage 先进入 fact-bound ScriptVersion，再进入 immutable StoryboardVersion。两者沿用既有 FactFrame append-only、validation、preflight 和 human-approval contracts；不能合并成一个可选节点。

## MediaIntegrityRecord

在标准完整执行链中，它位于 StoryboardVersion 后、ReplicationFinding 前，对冻结合同执行六个互不替代的 gate：`artifact_traceability`、`technical_profile`、`communicative_surface`、`target_identity_continuity`、`source_use_scope`、`originality_delta`。记录还必须保留 typed ScriptVersion ref 或 StoryboardVersion ref、`storyboard_lineage`、mode、tool/human fallback、blockers、unknowns、evidence limits 和 `blocked | proceed_with_limits | ready_for_next_gate` disposition。

`preflight` 至少绑定 ScriptVersion 或 StoryboardVersion 其中一个 typed ref，依赖未来媒体 Artifact 的状态必须是 `not_applicable_pending_artifact`。仅一个 version ref 时 `storyboard_lineage` 必须为空；两个 refs 同时存在时，lineage 必须包含精确匹配的 `storyboard_version_ref`、`source_script_version_ref` 和 closed `evidence_scope=declared_artifact_lineage`。`artifact_review` 必须同时具备两个 refs、完整 lineage 与受控媒体 Artifact；完整 ReplicationFinding 再检查同一 lineage。该字段只证明声明式 artifact refs 一致，不证明 runtime database derivation。Asset Bundle、Aggregate Index、Private Gate receipt、技术 probe、模型相似度或单一人审不能跨门替代版权、商业、平台或发布许可。

## ReplicationFinding

必须分开 `observations`、`bounded_inferences`、`unknowns`、`anomalies`、`next_actions`、evidence scope 和 limitations，并绑定 ReplicationContract、AdaptationPackage 与 MediaIntegrityRecord。不得写成 Product Fact、winner、causal lift 或 production acceptance。

## Adversarial fixture contract

Fixture 的 `expected` 不是事实来源。消费 fixture 时必须保留原始状态，先独立推导 disposition，再与 oracle 对照。Fixture-shape validation、canonical artifact validation 与 workflow expectation oracle 是三层不同证据；通过其中一层不能替代另外两层，也不表示真实媒体、平台或生产验收通过。
