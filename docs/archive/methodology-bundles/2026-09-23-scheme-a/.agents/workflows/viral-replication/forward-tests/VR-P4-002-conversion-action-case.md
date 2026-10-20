# VR-P4-002 Conversion Action：独立前向测试场景

## 目的

验证新 workflow 能把一个稳定、非趋势、非 proof/experience/attention 主导的参考样本，编译为只改变 `objection_resolution` 的受限合同。测试不要求外链、下单、账号、billing、媒体生成、真实平台数据、发布或 conversion 结论。

## 输入

### ReferenceBundle 和 DecompositionMap

- `reference_id`: `ref-conversion-forward-001`
- `source_digest`: `sha256:fixture-only-conversion-forward-digest`
- platform: `short_video`；初次与刷新均可播放，capture 可复现。
- rights: `confirmed_for_internal_analysis_only`；目标表达使用 target-authorized assets，不复用参考台词、人物、品牌视觉或页面。
- Performance Window: `view_count=12000, state=observed`；`conversion_rate=not_reported`。
- 观察：0.0–5.0s 的 `objection_resolution` 以可观察的 target product information 回答一个日常使用疑问；12.0–15.0s 有已观察的 promotion/CTA，但本次二者均冻结。每项 observation 都有 source ref；没有趋势、proof、体验或 attention 主导的要求。

### Target Product Truth、Promotion 和合同

- target Snapshot: `snap-conversion-forward-001`
- eligible Fact: `fact-product-feature-confirmed`，可支持已冻结的日常使用信息；excluded Facts 为空。
- frozen Promotion Fact: `promo-10-confirmed`，属于该 Snapshot、`status=confirmed`、`kind=percent_off`、`market=US`、`channel=tiktok_shop`、时区 `America/Los_Angeles`，并在 `database_time=2026-09-23T10:00:00Z` 时有效。
- frozen Pattern anchor: `offer_cta`、version `1.3`、15 秒、`en`；`cta_policy=server_promotion_final_cta`，最后一个 shot 的 role 是 `cta`。
- frozen `cta_invitation`: 服务端最终 CTA policy 与 final slot；frozen `action_path=not_applicable`，没有 URL、checkout 或外部执行请求。
- Control 与 Variant 固定：Snapshot、selected/excluded Fact 顺序、Promotion Fact、Pattern Definition、CTA invitation、action path、平台、市场、时长、语言、模型、目标素材、权限和预算。
- 唯一变化：`objection_resolution`。Control 直接给出该 confirmed Fact 支持的日常使用信息；Variant 先重述同一可观察疑问，再给出完全相同、fact-bound 的信息。二者没有改变优惠、CTA、路径或产品 Claim。
- provider input：仅 selected facts 与必要 generation parameters；Promotion、CTA policy、server-owned copy 和 action destination 均不进入 provider。
- 请求 Finding：记录合同可否进入下一 gate 及证据限制；不请求 conversion、销售、收入、checkout、winner 或 production 结论。

## 独立评估要求

使用 `routing-decision-tree.md`、`05-conversion-action/SOP.md`、`viral-conversion-action`、`factframe-product-truth`、`viral-fact-mapping` 与 `viral-replication-contract` 独立判定 disposition。输出：primary mechanism、selected component、blockers、允许下一步、不可得结论和 evidence level。

## 预期验收

`ready_for_next_gate`：只有 `objection_resolution` 改变，目标商品信息有 confirmed Fact，Promotion 独立、同 Snapshot、在数据库时间有效，CTA 只在服务端最终 slot 渲染，`action_path=not_applicable`，且 Finding 明确 `conversion_rate=not_reported`。
