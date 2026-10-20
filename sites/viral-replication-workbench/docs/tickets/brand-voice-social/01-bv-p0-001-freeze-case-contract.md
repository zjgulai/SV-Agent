# 01 — BV-P0-001 Freeze brand-voice social case contract

**What to build:** 从用户视角冻结品牌声量案例的轨道、目标、证据状态、权利/儿童安全状态、媒体状态和 `BrandAwarenessBrief` 字段，使品牌声量案例不会被误读为产品销售案例或已验证爆款。

**Blocked by:** None — can start immediately

**Status:** verified_local

- [x] `brand_voice_social` 被定义为案例轨道/目标包装层，而不是第七种 primary mechanism
- [x] `brand_awareness_only` 明确排除 conversion、sales lift 和 CTA
- [x] Performance Window、Performance Observation、Observation Availability、Creative Signal 和 proof level 语义与现有上下文一致
- [x] source-use、music、child-safety、commercial-disclosure 和 media-state 可独立表达
- [x] `proceed_with_limits`、`hold_rights`、`blocked` 和 `counterexample` 的停止条件明确
- [x] 第二位审阅者可根据 spec 和 ticket ledger 重建上述决定

**Validation:** 文档结构检查、术语交叉检查、与现有六类机制和媒体完整性门的边界检查。

**Out of scope:** 站点 UI、外部连接器、原始媒体、发布、部署和真实 Brand Lift。
