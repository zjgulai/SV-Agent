# Shared Artifact Contracts

所有 workflow 共享以下 artifact。它们是文档级合同，不代表已经进入 PostgreSQL runtime。

## ReferenceBundle

必须包含 `reference_id`、`source_locator`、`source_digest`、平台、Performance Window、捕获时间、权限状态、可播放状态、观察指标、限制和 source refs。

## DecompositionMap

必须包含时间线、Hook、Pain/Tension、Narrative Beats、Proof Device、Experience Cues、Visual/Audio/Text Grammar、CTA、声明候选、unsupported claims、未知项和 primary/secondary mechanism。`attention-grammar` 路由还必须为选定 component 保留 time range、carrier、可观察功能、surface class、source ref、availability state，以及对 frozen Pattern 的 `pattern_key/version`、shot/phase anchor；它们描述表达，不证明表现效果。`conversion-action` 路由还必须将 objection、promotion contract、CTA invitation 和 action path observation 分开，保留唯一 selected conversion component、其余冻结 components、Fact/Promotion refs、availability、source refs、frozen CTA policy/final CTA role、action-path binding 或 `not_applicable` 以及外部行动边界。`trend-native` 路由还必须分别保留 `trend_signal_binding`、`trend_semantic_frame`、`template_grammar`、`audio_function` 的 source/time/availability/surface observation 或 `not_present`，并区分有界观察与 source audio/template/identity 的 target reuse。

## PatternHypothesis

必须拆分 `invariant_elements`、`replaceable_elements`、`prohibited_surface_copy`、`adaptation_constraints`、evidence scope 和 unknowns。

## ReplicationContract

必须冻结 Reference、Control、Variant、唯一 Creative Dimension、Product Snapshot、selected/excluded facts、语言、市场、平台、时长、模型、素材权限、预算、停止条件和验收门。`attention-grammar` 合同还必须命名唯一 selected attention component，并列出所有 frozen attention components、target surface substitutions、sound policy 和 frozen Pattern identity。`conversion-action` 合同还必须命名唯一 `objection_resolution`、`promotion_contract`、`cta_invitation` 或 `action_path`，保留其余 conversion components、独立 Promotion Fact/value digest/database-time validity、Pattern CTA policy/final role、provider exclusion、action-path binding 或 `not_applicable` 与 capability boundary。`trend-native` 合同还必须命名唯一 `trend_signal_binding`、`trend_semantic_frame`、`template_grammar` 或 `audio_function`，冻结其余三项和完整 `TrendAdmissionRecord`；该 record 至少包含 analysis/adaptation/source-audio/template evidence states、platform/market/locale 的 observed constraints、`assessment_state`、`execution_capability=not_implemented`、`external_action_requested=false`、target text/visual/audio substitutions、source identity exclusions 和进入 `MediaIntegrityRecord.originality_delta` 的 handoff。它是文档级 admission record，不是音频/模板授权、平台兼容、平台调用、上传、发布或原创批准。

## MediaIntegrityRecord

在 fact-bound Script/Storyboard preflight 后、ReplicationFinding 前，对每个冻结的 ReplicationContract 创建 `media-integrity-v1` record。它必须写明 `mode=preflight|artifact_review`、contract/snapshot/fact identity、六个互斥 gate（`artifact_traceability`、`technical_profile`、`communicative_surface`、`target_identity_continuity`、`source_use_scope`、`originality_delta`）、tool/human fallback、blockers、unknowns、evidence limits 和 `blocked|proceed_with_limits|ready_for_next_gate` disposition。`preflight` 中所有依赖未来 artifact 的状态必须是 `not_applicable_pending_artifact`，不可伪装成通过；`artifact_review` 也只代表有范围的本地审计。Asset Bundle 的结构有效、Aggregate Index 的 QA/commercial disposition、Private Gate receipt、`ffprobe`、模型相似度或单一人审都不能跨门替代版权、商业、平台或发布许可。

## Finding

输出必须分开写 `observations`、`bounded_inferences`、`unknowns`、`anomalies`、`next_action`、`evidence_level` 和 `limitations`。不得把 Finding 写成 Product Fact、winner、causal lift 或 production acceptance。

## Adversarial fixture contract

P3 fixture 的 `expected` 不是事实来源，而是测试 oracle。消费 fixture 时必须保留输入中的原始状态，先独立推导 disposition，再与 oracle 对照。通过只表示 skill/SOP 在该合成输入上识别出了正确 blocker；不表示真实媒体、平台或生产验收通过。
