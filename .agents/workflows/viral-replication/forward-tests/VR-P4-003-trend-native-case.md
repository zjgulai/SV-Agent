# VR-P4-003 Trend Native：独立前向测试场景

## 目的

验证新 workflow 能把一个确由外部趋势模板主导、但不复用来源音频或模板实体的合成参考样本，编译为只改变 `template_grammar` 的受限本地合同。测试不要求趋势发现、当前热度验证、音频/模板授权、平台兼容验证、模板激活、账号、上传、发布、媒体生成、商业批准或表现结论。

## 输入

### ReferenceBundle、DecompositionMap 和 PatternHypothesis

- `reference_id`: `ref-trend-forward-001`
- `source_digest`: `sha256:fixture-only-trend-forward-digest`
- platform: `short_video`；market: `US`；language: `en`；capture time: `2026-09-20T10:00:00Z`；观察窗口：`2026-09-19T00:00:00Z`–`2026-09-20T23:59:59Z`；初次与刷新均可播放、capture 可复现。
- rights: `confirmed_for_internal_analysis_only`。这个状态只允许观察参考；不允许 source audio、template ID、原口播、人物、品牌视觉、贴纸或平台上传表层进入 target execution input。
- Performance Window: `view_count=12000, state=observed`；`trend_rank=not_collected`；`conversion_rate=not_reported`。
- `trend_signal_binding`: 一个有 source ref 的短视频 challenge 观察；可确定其 signal kind、platform、market、language、capture 和 window，但不声称现在仍热门、被推荐、可调用或可发布。
- `trend_semantic_frame`: 0.0–4.0s 的共享前提与 4.0–7.0s 的反转；原文、人物身份和品牌表层均为 prohibited surface，target 侧另写非商品性的原创表达。
- `template_grammar`: 0.0–4.0s 的 role `setup`，4.0–7.0s 的 role `turn`，7.0–12.0s 的 role `resolution`；可观察函数是“由建立、反转到结果的三段角色交接”。reference template 不存在可调用的 target `template_id`。
- `audio_function`: 4.0s 的观察到 cue 用于标记反转；source audio 只作观察，target sound policy 是 `independent_authorized_sound_A`，不使用、下载或仿制 source audio。
- PatternHypothesis 的唯一 `primary_mechanism=trend-native`；移除 trend template grammar 后，表达的三段参与结构不再成立。不存在 proof、experience、attention、conversion 或 narrative 的并列主机制。

### Target Product Truth、TrendAdmissionRecord 和合同

- target Snapshot: `snap-trend-forward-001`
- eligible Fact: `fact-product-feature-confirmed`，只支持目标结果段的一句已冻结商品信息；excluded Facts 为空。其它 trend semantic copy 明确为 `not_a_product_claim`。
- frozen Pattern anchor: `trend_local_template`、version `1.0`、12 秒、`en`；所有 phase/shot role、CTA policy、duration 和 budget 已冻结。
- `TrendNativePlan.selected_trend_component=template_grammar`；frozen components: `trend_signal_binding`、`trend_semantic_frame`、`audio_function`。
- frozen `TrendAdmissionRecord.rights_scope`: `reference_analysis_state=confirmed_for_internal_analysis_only`；`adaptation_scope_state=target_independent_expression_only`；`source_audio_reuse_state=not_requested`；`template_usage_state=not_requested`；每项有 fixture-only evidence ref。
- frozen `TrendAdmissionRecord.platform_compatibility`: `target_platform=short_video`、`market=US`、`locale=en-US`、`observed_constraints=[vertical_9_16, duration_12_seconds]`、`assessment_state=constraints_observed`、`execution_capability=not_implemented`、`external_action_requested=false`。
- frozen `TrendAdmissionRecord.originality_delta`: target text、visual 和 audio substitutions 已记录；source identity exclusions 包含 source audio、original script、performer identity、brand visuals 和 template ID；`review_state=deferred_to_vr_p4_004`、`formal_gate=VR-P4-004`。
- Control 与 Variant 固定：Snapshot、selected/excluded Fact 顺序、Pattern Definition、平台、市场、locale、时长、语言、模型、target assets、target audio policy、rights、TrendAdmissionRecord 和预算。
- 唯一变化：`template_grammar`。Control 使用 target-created “setup → result → reflection” 的角色交接；Variant 使用 target-created “setup → turn → resolution” 的角色交接。二者不复用参考角色、镜头、原口播、音频或 template ID。
- provider input：仅 selected facts 与必要 generation parameters；不包含 reference URL、source audio/template、source identity、rights assessment、platform constraints/operation、CTA policy 或 server-owned copy。
- 请求 Finding：仅判定本地合同 / fact-bound Script-Storyboard preflight 是否可继续，以及不可得结论；不请求当前趋势、授权、平台兼容、template activation、上传、发布、媒体质量、表现、因果、winner、商业批准、live 或 production 结论。

## 独立评估要求

使用 `routing-decision-tree.md`、`06-trend-native/SOP.md`、`viral-trend-native`、`factframe-product-truth`、`viral-fact-mapping`、`viral-replication-contract` 与 `factframe-readiness` 独立判定 disposition。输出：primary mechanism、selected component、admission record 状态、blockers、允许下一步、不可得结论和 evidence level。不要预先读取结果文件。

## 预期验收

`proceed_with_limits`：只有 `template_grammar` 改变，三个趋势组件和完整 admission record 已冻结；目标商品信息有 confirmed Fact；source audio/template/identity 没有进入 target input；平台仅记录 `constraints_observed`，`execution_capability=not_implemented`；originality 仅移交 `VR-P4-004`，没有被写成已批准。允许下一步是冻结本地 TrendNativePlan/ReplicationContract 后进入 fact-bound Script/Storyboard preflight，并申请独立 rights、platform-compatibility 和 originality gates。
