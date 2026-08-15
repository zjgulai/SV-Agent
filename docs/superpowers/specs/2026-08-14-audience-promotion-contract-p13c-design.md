# P1.3c 受众创意槽与 Promotion Fact 合同

## 决策

P1.3c 为未来 generation 写入 `p1.3c` / Pattern `1.3` 的冻结合同。它不把自由受众或促销文案交给 Provider，不改变历史 `p1.3a`、`p1.3b` 或 legacy generation。

干净室实验 S-A01 显示自由受众会诱发价格、比较与身份结论；S-P01 显示测试折扣会被扩写为实时优惠。因此两者都必须是结构化、可复检的服务器合同，而不是文本提示。

## Audience profile

API 只接受：`general`、`study_routine`、`work_routine`、`home_routine`、`on_the_go`。服务端将 profile 解析为冻结的场景、通用道具、日常时刻和中性语气，并且只写入 `visual`、`action`、`acceptance_shot`、`titles`、`tags`、`shooting_list`。

它不得改变 `voiceover`、`caption`、`product_claims`、事实 ID、phase、shot role、时间预算、语速，或产生价格、比较、稀缺、功效和适用人群断言。Provider payload 会移除 profile、解析后的 server-owned copy 与 CTA policy；Provider 输出随后仍由冻结 copy 覆盖。

## Promotion Fact

仅专用 `POST /api/v1/products/{product_id}/promotion-facts` 能创建 Promotion Fact。它固定为 `claim_type=promotion`、`user_assertion/manual-form`，通用 facts endpoint 显式拒绝该类型。

当前唯一支持的范围为 TikTok Shop US / `America/Los_Angeles`：`promotion-v1`、`percent_off` 或 `amount_off`、百分比或金额+USD（二选一）、`effective_from < effective_to` 且两个时间都带 UTC offset。无优惠码、原价、比较价、限量、倒计时、叠加或自由 CTA。

`active` 是派生状态：Fact 为 `confirmed/locked`、属于冻结 snapshot、摘要匹配且 PostgreSQL `statement_timestamp()` 落在有效窗。修正一律创建新 Fact；旧 Fact、generation 和版本保持不变。

Fact 创建通过 `operation_key + operation_input_digest` 幂等：同键同输入返回原记录，同键不同输入返回 `IDEMPOTENCY_CONFLICT`。0011 migration 把操作元数据与 Promotion 值合同加入数据库约束，并将操作元数据纳入事实不可变触发器。

## 生成、验证与审核

`promotion_fact_id` 是 generation 的可选独立字段，不能出现在 selected/excluded Fact 列表。生成时冻结 Fact ID、value digest 与语言化 server render。Worker 在 Provider 前、保存 Version 前均复检；失败写 `PROMOTION_NOT_ACTIVE`，不能降级为无优惠继续成功。

Promotion 只能由 `enforce_creative_contract()` 写入最终一镜、role 为 `cta` 的 `ScriptShot.promotion`。它不进入 product claim、caption 或 voiceover。validator 阻断 `PROMOTION_UNAUTHORIZED`、`PROMOTION_SLOT_INVALID`、`PROMOTION_RENDER_MISMATCH`。Storyboard preflight 与审批会对相同冻结合同重新检查，过期或失效即 blocked/stale。

## 验收

1. 闭合受众 profile 仅改变 server-owned copy，事实/结构/时长不变，Provider payload 不含 profile 或 copy。
2. 通用 facts endpoint 不能伪造 Promotion Fact；专用入口的幂等、快照归属、值形状和不可变字段受 API 与数据库双重约束。
3. Promotion 不进入 selected facts；仅最终 CTA 持有精确 server render，非 CTA 或 provider 伪造均失败。
4. Queue、Provider 前、保存、preflight 与 approval 对 inactive/changed promotion 均失败关闭。
5. 导出包含冻结 configuration；历史 p1.3a/p1.3b 可读且不重解释。

Docker/PostgreSQL 可用后必须执行 0010→head→base→head 迁移回归、真实 PostgreSQL API/worker/storyboard 集成测试，再把本批视为可发布。
