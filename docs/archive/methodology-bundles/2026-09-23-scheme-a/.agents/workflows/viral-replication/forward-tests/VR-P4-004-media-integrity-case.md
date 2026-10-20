# VR-P4-004 Media Integrity：独立前向测试场景

## 目的

验证跨机制 Media Integrity Gate 能在不创建或访问真实媒体、私有素材、平台或账号的前提下，正确区分六个完整性门，并只允许一个符合事实/合同边界的本地 `preflight` 继续。测试不要求 RenderJob、视频生成、真实 `ffprobe`、ASR、OCR、商业审核、版权许可、平台兼容、上传、发布、表现或 production 结论。

## 输入

### Frozen contract 与 Product Truth

- `contract_digest`: `sha256:fixture-only-media-integrity-contract`
- `primary_mechanism`: `trend-native`；唯一 `changed_creative_dimension=template_grammar`；Control/Variant 的 Snapshot、selected/excluded Fact 顺序、Pattern、时长、语言、市场、平台、target assets、audio policy、rights 和预算均声明冻结。
- target Snapshot: `snap-media-integrity-forward-001`
- eligible Fact: `fact-product-feature-confirmed`，只支持 target resolution segment 中的一项商品信息；excluded Facts 为空。所有非商品 trend expression 均标为 `not_a_product_claim`。
- frozen Pattern：12 秒、`en`、`short_video` / `US`、target-created expression；reference URL、source audio/template、source identity、rights assessment、平台操作和 server-owned copy 均不进入 provider input。

### MediaIntegrityRecord：preflight

- `mode=preflight`；不存在生成 Artifact、RenderJob、真实 media file、真实 ASR/OCR/ffprobe 或任何平台操作。artifact-dependent gate 必须被明确写为 `not_applicable_pending_artifact`，而不是 pass。
- `artifact_traceability`: target planned artifact 的 contract/config digest 已冻结，`artifact_state=not_applicable_pending_artifact`；没有借用 Asset Bundle、Aggregate Index 或 Private Gate 的状态来替代未来 generated Artifact 的 identity。
- `technical_profile`: frozen acceptance constraints 为竖版 9:16、12 秒；`review_state=not_applicable_pending_artifact`，规定未来实际 artifact 必须由受控 probe 或范围明确的人工 fallback 验证。
- `communicative_surface`: 冻结 target Script/Storyboard 中所有可见/可听 Product Claim 都已映射到 `fact-product-feature-confirmed`；趋势语义文本为 `not_a_product_claim`；当前无 Artifact，因此 ASR/OCR 是 `not_applicable_pending_artifact`，未来需完整媒体表面复检。
- `target_identity_continuity`: frozen target asset refs、目标颜色和组件数量已列出；当前无 Artifact，frame/shot review 是 `not_applicable_pending_artifact`，未来要逐镜头审计。
- `source_use_scope`: reference audio、template ID、reference text、performer identity、brand visual 均为 `confirmed_for_internal_analysis_only`，并在 target input 中 `not_requested`；target expression 只使用独立 target-controlled text/visual/audio。没有改编、reuse、embedding、redistribution、commercial 或 publishing 权利结论。
- `originality_delta`: target text/visual/audio substitutions 与 source identity exclusions 已列出；`comparison_method=bounded_independent_preflight_review`，`review_state=evidence_collected`，`formal_gate=VR-P4-004-artifact-review`。该状态不是原创、版权、商标、肖像、商业或发布批准。
- `human_fallbacks`: 仅定义未来每个技术/ASR/OCR/identity 工具 unavailable 时应由何种独立、范围明确的人工复核补位；没有捏造已完成的人审。
- requested Finding：只判定本地 preflight 是否可进入后续 fact-bound Script/Storyboard / contract instance 审计，列出 Artifact review、rights、originality、commercial、platform 与发布的独立 blocker。

## 独立评估要求

使用 `07-media-integrity/SOP.md`、`viral-media-integrity`、`viral-replication-contract`、`viral-fact-mapping`、`factframe-script-storyboard`、`factframe-momcozy-assets` 与 `factframe-readiness` 独立输出：mode、六个 gate 的逐项状态、disposition、blockers、允许下一步、evidence level 和绝对不可得结论。不得读取结果文件，也不得将本场景的“目的”或本段落之外的 expected output 当作答案。

## 预期验收

`proceed_with_limits`：此 case 的唯一可继续项是 document-level preflight 和后续 frozen contract/Storyboard claim audit。没有 artifact-dependent gate、rights entitlement、originality approval、commercial approval、Private Gate、platform compatibility、media generation、upload、publish、performance、live 或 production claim 可以被通过。
