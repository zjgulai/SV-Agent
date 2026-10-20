# Conversion Action Replication SOP

## Trigger

当复刻价值主要来自一个可观察的决策异议、商业条款、CTA 邀请或行动路径，且该要素可与叙事、proof、体验、attention 和趋势模板分离时使用。结尾出现 CTA 本身不构成该路由的充分条件。

## Preconditions

- ReferenceBundle 的来源、digest、时间窗、可复核状态、分析/适配权限以及 objection/promotion/CTA/path observation 明确。
- DecompositionMap 已分别记录四类 conversion observation 的 source ref、availability state、surface class 和 unknowns。
- PatternHypothesis 的唯一 `primary_mechanism` 是 `conversion-action`。
- Control/Variant 只选择 `objection_resolution`、`promotion_contract`、`cta_invitation` 或 `action_path` 之一。
- 目标 Product Snapshot、ordered selected/excluded Facts 和所有目标商品声明已确定；selected/excluded 集合中没有 Promotion Fact。
- 如选择 `promotion_contract`，Promotion Fact 与 Snapshot 相同、处于 `confirmed`/`locked`、按数据库时间有效，并且 frozen Pattern 暴露 `server_promotion_final_cta`。
- frozen `CompiledPatternDefinition` 的 `pattern_key/version`、duration、language、market、CTA policy、phase sequence、final CTA role 和预算可复核；如声明 action path，已存在受控 path binding，否则明确 `not_applicable`。

## Steps

1. 用 `viral-reference-intake` 固定 ReferenceBundle。
   - 完成标准：来源、digest、平台、观察窗口、可播放性、权利、四类 conversion observation 与限制可复核。
2. 用 `viral-content-decomposition` 建立 conversion-action map。
   - 完成标准：objection、promotion、CTA invitation、action path 分别有 observation、source ref、availability 和表层处置；参考口播不是 target copy 或 Promotion Fact。
3. 用 `viral-pattern-abstraction` 确认唯一主机制。
   - 完成标准：PatternHypothesis 描述可迁移的 conversion function，不含转化、销售、收入或 winner 因果结论。
4. 用 `viral-conversion-action` 选择唯一 conversion component 并生成 `ConversionActionPlan`。
   - 完成标准：选定 component、冻结 components、Fact/Promotion binding、CTA policy/final slot、action-path state、provider exclusion 和外部行动边界完整；两位审阅者能得出同一 component。
5. 用 `factframe-product-truth` 与 `viral-fact-mapping` 审计 target claim 和 Promotion。
   - 完成标准：商品声明全部绑定同一 Snapshot 的 confirmed/locked Fact；Promotion 独立于 selected/excluded，按数据库时间有效；unsupported claim=0、excluded occurrence=0。
6. 用 `factframe-script-storyboard` 编译既有 fact-bound Pattern。
   - 完成标准：provider request 不含 Promotion、CTA policy、server-owned copy 或 action destination；只有服务端把有效 Promotion 渲染到 `server_promotion_final_cta` 的最终 `cta` role。
7. 用 `viral-replication-contract` 固定 Control/Variant。
   - 完成标准：canonical config diff 只包含唯一 selected conversion component；其余 conversion components、Snapshot、Facts、Pattern、时长、语言、市场、平台、模型、素材、权限、预算一致。
8. 用 `viral-media-integrity` 建立 `MediaIntegrityRecord`。
   - 完成标准：Promotion/CTA 的声画表达审计与 source-use/originality/identity/technical/traceability gate 分开；没有 artifact 时只输出 pending preflight state。
9. 用 `viral-experiment-evaluation` 记录 Artifact、Ledger 和 Finding。
   - 完成标准：Finding 分开写 observations、bounded inferences、unknowns、limitations 和 next action；不把一次结果写为转化或销售因果证明。
10. 用 `factframe-readiness` 标明 proof level。
   - 完成标准：local fixture、local validation、CI、Private Gate、deployment、live 和 production 结论分别表述。

## Stop conditions

- 主机制其实是 narrative、proof、experience、attention 或 trend-native，或多个 conversion components 不能拆开。
- objection 的回答依赖 unsupported/excluded Product Fact，或引用跨 Snapshot Fact。
- Promotion 不在独立字段、状态不足、时间窗无效/已失效、市场/渠道/币种不匹配，或 Pattern 没有 promotion CTA slot。
- Promotion 或 CTA/server-owned policy 被送往 provider，或 Promotion 不在最终 `cta` role。
- 请求需要自由 URL、下单、账号、billing、平台发布、真实转化或收入测量；这些不是本 workflow 的 runtime 能力。
- 声明 `action_path` 却无受控 path binding，或把参考链接/第三方页面/平台动作当作已验证的目标路径。
- Contract 同时改变两个 conversion components，或同时改变 Product Truth、Pattern、时长、语言、市场、平台、模型、素材、权限或预算。
- 输出把本地合同、fixture 或单样本结果解释为 conversion lift、销售、winner 或 production proof。
- 将有效 Promotion/CTA、Asset QA、技术 probe 或 model review 误写成 source-use、原创、商业、平台或发布许可，或任一 Media Integrity Gate 的证据范围未闭合。

## Outputs

ReferenceBundle、conversion-action DecompositionMap、PatternHypothesis、ConversionActionPlan、ReplicationContract、fact-bound Script/Storyboard、Promotion/CTA validation、`MediaIntegrityRecord`、Artifact/Ledger 和 bounded ReplicationFinding。
