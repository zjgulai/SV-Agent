# Shared Replication Scorecard

未独立测量的维度保持 `unavailable`，不填 0。

| Dimension | Required evidence | Blocking condition |
| --- | --- | --- |
| Reference stability | source digest、capture state、refresh/playability observation | source or replay identity unresolved |
| Mechanism identity | DecompositionMap + unique primary dimension | primary mechanism ambiguous |
| Attention isolation | timed observations + one selected attention component + frozen remainder | component ambiguous or more than one attention component changes |
| Conversion integrity | one objection-resolution/promotion-contract/CTA-invitation/action-path component + frozen remainder, valid Promotion/CTA ownership and path state | component ambiguous, Promotion/CTA policy invalid, path unresolved, or more than one conversion component changes |
| Trend integrity | one trend-signal-binding/trend-semantic-frame/template-grammar/audio-function component + frozen remainder, bounded observation and frozen TrendAdmissionRecord | component ambiguous, trend identity/window unresolved, source audio/template reuse unclear, admission record drifts, or trend surface is not primary |
| Product truth | same Snapshot、confirmed/locked Fact IDs | unsupported claim or fuzzy binding |
| Contract isolation | canonical config digest、Control/Variant diff | more than one changed field |
| Execution | terminal state、ledger、artifact hash | unknown terminal state or ledger mismatch |
| Media traceability | `MediaIntegrityRecord.artifact_traceability`、artifact/config/contract digest、terminal/provenance 或 explicit pending state | artifact 与 frozen contract 不可重建，或 pending artifact 被写成已验收媒体 |
| Media technical profile | `MediaIntegrityRecord.technical_profile`、MIME/bytes/duration/dimensions/fps/codec/audio 与有范围的 tool/human fallback | required technical evidence unavailable without bounded fallback，或不符合 frozen contract |
| Media communicative surface | `MediaIntegrityRecord.communicative_surface`、ASR/OCR/人审、full-surface Fact mapping | unsupported/excluded/expired promotion 或关键 surface 未审计 |
| Target identity continuity | `MediaIntegrityRecord.target_identity_continuity`、target asset refs、跨镜头身份审计 | product color/logo/component/quantity/material drift，或连续性未闭合 |
| Source-use scope | `MediaIntegrityRecord.source_use_scope`、reference/target source class、planned-use matrix、evidence refs | planned use 超出 analysis/adaptation/reuse/embed/redistribution/commercial/publish evidence scope |
| Originality delta | `MediaIntegrityRecord.originality_delta`、target substitutions、source identity exclusions、独立 comparison method/review state | source identity surface 未替换，或模型/相似度被当作原创、法律、商业、平台或发布批准 |
| Evidence strength | Fact / Inference / Unknown with scope | causal or universal language without design |
