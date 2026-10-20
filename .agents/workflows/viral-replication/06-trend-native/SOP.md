# Trend Native Replication SOP

## Trigger

当外部趋势信号、平台梗/社群语境、挑战/模板结构或音频功能决定参考内容的主要表达时使用。仅出现热门标签、背景音频、短暂梗或平台格式并不充分；移除该表层后若 proof、experience、attention、conversion 或 narrative 仍完整，应路由到其实际主机制并把趋势表层冻结。

## Preconditions

- ReferenceBundle 已固定 source locator/digest、capture time、platform、market、language、观察窗口、可播放/刷新/复现状态、rights state、limitations 与每项趋势 observation 的 source ref。
- DecompositionMap 已分别记录 `trend_signal_binding`、`trend_semantic_frame`、`template_grammar`、`audio_function` 的观察或明确 `not_present`；来源音频、模板、原文、人物、品牌和身份表层已分类。
- PatternHypothesis 的唯一 `primary_mechanism` 是 `trend-native`；不能分离的其它机制已冻结、拆 Variant 或 `blocked`。
- Control/Variant 仅选择四个 Trend Component 之一；其余三个完整进入 `frozen_trend_components`。
- Target Product Snapshot、ordered selected/excluded Facts、target assets、target audio policy、Pattern identity、时长、语言、市场、平台、模型和预算可复核；商品声明只有同 Snapshot `confirmed`/`locked` Fact 支持。
- TrendAdmissionRecord 已记录 reference analysis、adaptation、source-audio reuse、template-use evidence，平台约束、target substitutions、source identity exclusions 和 originality handoff；当前 `execution_capability=not_implemented`、`external_action_requested=false`。

## Steps

1. 用 `viral-reference-intake` 固定 ReferenceBundle。
   - 完成标准：趋势观察有时间窗、来源、digest、平台/市场/语言和 availability；“当前热门”“平台可用”只在有独立一手证据时才可描述。
2. 用 `viral-content-decomposition` 建立 trend-native `DecompositionMap`。
   - 完成标准：四类 Trend Component 各有 source ref、time range 或 `not_present`、observed function、surface class、unknowns；参考音频/模板/原文从不变成 target execution copy。
3. 用 `viral-pattern-abstraction` 确认唯一主机制。
   - 完成标准：PatternHypothesis 描述趋势所支配的表达函数，不含热度、推荐、曝光、留存、转化、因果或 winner 结论。
4. 用 `viral-trend-native` 形成可修订 `ReplicationPlan`，并保留候选 TrendNativePlan 与 TrendAdmissionRecord。
   - 完成标准：唯一 selected component、三个冻结 component、target substitutions、prohibited surface copy、Pattern anchors 和 admission evidence 完整；两位审阅者可得出同一 component，计划尚不授权执行。
5. 用 `factframe-product-truth` 与 `viral-fact-mapping` 审计 target claim，形成 `FactMap`。
   - 完成标准：所有商品声明绑定同一 Snapshot 的 confirmed/locked Fact；trend semantic language 不得替代商品证据；unsupported claim=0、excluded occurrence=0。
6. 用 `viral-replication-contract` 固定 Control/Variant，形成不可变 ReplicationContract。
   - 完成标准：canonical diff 只包含唯一 selected Trend Component；四类 admission record、其它 trend components、Snapshot、Facts、Pattern、时长、语言、市场、平台、模型、target assets、audio policy、rights 和预算一致，digest 可重算。
7. 在不可变合同下将 TrendNativePlan 和 frozen TrendAdmissionRecord 编译为 `AdaptationPackage`。
   - 完成标准：selected/frozen components、source substitutions、identity exclusions、rights/platform/originality handoff 可复核；该 package 通过本地 machine schema 验证，保持 `execution_capability=not_implemented`，不产生 PostgreSQL/runtime persistence。
8. 用 `factframe-script-storyboard` 依次编译既有 fact-bound Pattern 为 ScriptVersion、StoryboardVersion。
   - 完成标准：provider 只接收选定 Facts 和必要 generation parameters；reference URL、named source audio/template、source identity surface、rights assessment、平台操作和 server-owned policy 不进入 provider。此结果不证明存在 trend metadata runtime exclusion。
9. 用 `viral-media-integrity` 将 `TrendAdmissionRecord` 移交为 `MediaIntegrityRecord` 的 source-use/originality evidence input。
   - 完成标准：六个 gate 分别保留 state 与 blocker；source audio/template 的 observed/access state 不替代 reuse scope，target substitutions 不替代独立 originality review，preflight 不伪造 artifact 或工具结果。
10. 用 `viral-experiment-evaluation` 记录 Artifact、Ledger 和 `ReplicationFinding`。
   - 完成标准：Finding 分开写 observations、bounded inferences、unknowns、limitations 和 next action；不把本地合同或单样本写成趋势热度、授权、平台可用、原创通过、表现或因果证明。
11. 用 `factframe-readiness` 标明 proof level。
   - 完成标准：fixture/local validation、CI、Private Gate、commercial approval、deployment、live、platform verification 和 production 的结论分别表述。

## Stop conditions

- 背景趋势表层被误写为主机制，或 trend 与其它机制不能拆成唯一变量。
- 趋势信号身份、平台/市场/语言/时间窗、source refs、capture/replay state 或可复核性缺失；标签、旧截图或 AI 摘要不得填补缺口。
- 从 source audio/template 的可播放、可见或可访问性推断 adaptation、embedding、AI imitation、redistribution、publishing 或平台许可。
- 原音频、原台词、可识别人物、品牌表层、platform-native sticker、模板 ID、固定角色/镜头组合会进入 target 表达，却没有匹配的 scope 和差异化记录。
- 把 `constraints_observed` 写成“已兼容”，请求平台模板调用、上传、账号、发布、外链、下单、billing 或真实平台验证；当前 workflow 没有这些 runtime capability。
- 把 `originality_delta` 写成“已通过”而未进入 `viral-media-integrity` 的独立 `MediaIntegrityRecord`；Asset Bundle、QA、Aggregate Index 或 Private Gate receipt 不能替代这一门。
- Control/Variant 同时改变两个 Trend Component，或改变 TrendAdmissionRecord、Product Truth、Pattern、时长、语言、市场、平台、模型、target assets、audio policy、rights 或预算。
- 输出声称当前趋势、授权、模板可用、平台兼容、媒体质量、分发、转化、商业批准、live 或 production acceptance，却没有对应独立证据门。

## Outputs

ReferenceBundle、trend-native DecompositionMap、PatternHypothesis、ReplicationPlan、FactMap、不可变 ReplicationContract、trend AdaptationPackage（含 frozen TrendAdmissionRecord）、fact-bound ScriptVersion、StoryboardVersion、claim validation、`MediaIntegrityRecord`、Artifact/Ledger 和 bounded ReplicationFinding。它们只构成本地 artifact/合同链；rights/权利、平台兼容、原创批准、媒体生成、render、publish、commercial 和 production acceptance 另行进入独立 gate。
