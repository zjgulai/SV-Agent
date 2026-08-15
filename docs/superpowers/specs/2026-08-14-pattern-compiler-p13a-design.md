# P1.3a Pattern compiler 合同

## 目标与范围

P1.3a 把现有仅含 key、阶段列表和镜头角色的 pattern registry 编译为完整、
版本化且可验证的 `PatternDefinition`，并在每个新 `ScriptGeneration` 中冻结该
编译结果。它不调用额外 Provider、不创建候选、不改变事实选择、不会生成促销，
也不开放受众自由场景、语气或文案编辑。

本记录的实现曾维持每种 pattern 在 15/30/45 秒均为四阶段/四镜头。后续获批准的
P1.3b 已为**未来** generation 采用时长敏感默认结构；该决定与证据边界见
`2026-08-14-duration-sensitive-storyboard-p13b-design.md`。本 P1.3a 记录及已冻结
的 `1.1` generation 保持历史事实，不得被新 registry 重解释。

## 编译产物

新 generation 的 `configuration.pattern_definition` 必须是以下冻结对象，且完整
进入 generation `input_digest`：

```text
contract_version: "p1.3a"
key / version / name / hook_type
duration_seconds / language
phases: [{key, purpose, shot_role, fact_role: "required_selected"}]
shots: [{phase_key, role, fact_role: "required_selected", budget_weight}]
speaking_rate: {unit, max}
field_policy:
  fact_bound: [voiceover, caption, product_claims, supported_fact_ids]
  server_owned: [phase.purpose, visual, action, acceptance_shot, titles, tags, shooting_list]
cta_policy: {mode: "server_generic_no_offer"}
audience_policy: {mode: "record_only", allowed_slots: []}
acceptance_checks: [phase_order, shot_plan, timeline_budget, speaking_rate,
                    fact_binding, excluded_deny_set, server_owned_copy]
```

每个 pattern 的阶段 key、purpose、shot role、budget weight 都是 registry 的
server-owned 数据。每个镜头必须有一个 selected fact；CTA 不能引入价格、折扣、
限时或其它促销文本。`audience` 仍作为 ScriptDraft 元数据保存，但不得进入 Provider
提示或改变任何可见字段。

## 编译、历史与执行边界

`compile_pattern(key, duration, language)` 只接受 registry 已声明的 key、时长和
`en` / `zh-CN`，否则 queue 返回现有稳定的 422 pattern/duration 错误。它产生
`1.1` 新版本的完整合同；不需要 database migration，因为 `configuration` 是
追加式 generation 事实，并已经被 input digest 覆盖。

Worker、provider、creative renderer 和 validator 必须从已持久化的 compiled object
读取，而不是再根据 key 查询当前 registry。缺失或损坏的 P1.3a compiled contract
属于执行失败，不能保存 ScriptVersion。旧 `1.0` generation 缺少
`contract_version` 时走只读 legacy adapter：仅使用其已持久化的 phase/role 列表，
保留原先检查，绝不按新 registry 重新解释历史版本。

validator 新增或收紧：阶段顺序、每镜 `phase_key`/role 对应的 shot plan、每个镜头
与 selected fact 的绑定、按 compiled speaking rate 的时长预算，以及 server-owned
字段。Provider 少镜头、多镜头、错序、错误 role、超语速或可见促销都只能得到
validation failure。

## Web 与 API

`GET /api/v1/creative-patterns` 公开可选 catalog 和按受支持时长/语言可解析的只读
contract。生成页选择 pattern、时长和语言后显示“阶段 → 镜头角色 → required fact →
预算”，并明确“受众当前只记录，不改变生成内容”“CTA 不含优惠”。页面不保存或发送
creative slot、promotion、price、percent、scene 或 tone 字段。

## 明确延期的产品选择

以下均不属于 P1.3a，实施前必须另行确认并设计：

1. audience profile taxonomy，及其可改变的场景/语气槽；
2. promotion Fact 的值、币种、市场、渠道、时区、有效期、来源与历史版本语义；
3. 是否采用 Oumomo 实验观察到的不同长度 phase/shot 布局。

## 验收

1. 七种 pattern 在三种时长和两种语言下均可编译出确定性 P1.3a 合同。
2. 新 generation 冻结 `1.1` 合同；registry 后续变动不改变 worker、validator、
   export 或 storyboard 对该 generation 的行为。
3. legacy `1.0` generation 的读取、preflight、导出与已有回归不退化。
4. 少/多/错序镜头、错误 role、超语速、未绑定事实、价格/促销 CTA 都不会成为
   acceptable ScriptVersion。
5. S-A01 边界：`audience="大学生"` 不进入 Provider payload，也不能产生价格、
   affordability、身份或比较语句。
6. API/Web contract、lint、typecheck、全套 backend/Web tests 与隔离 migration
   head 检查通过。
