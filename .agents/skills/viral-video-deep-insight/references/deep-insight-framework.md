# 爆款视频深度洞察分析框架

版本：`viral-video-deep-insight-v1`

## 0. 这不是“爆款公式”，而是一套决策系统

本框架研究的是：在明确的主体、平台、市场和时间窗内，一个内容候选为什么值得继续研究，
其中哪些表达机制可以被重新编译为目标商品的可验证假设，以及下一步最小成本要验证什么。

因此，报告中使用以下术语：

- **Viral Candidate**：在有界 `Performance Window` 内表现突出、值得进入研究的候选；不是
  `winner`。
- **Performance Observation**：来源直接显示的计数、排序或分布；不是因果结论。
- **Creative Signal**：观察到的表达与表现之间值得测试的关联；不是增长驱动或通用公式。
- **PatternHypothesis**：把表层表达拆成 invariant、replaceable、prohibited、unknown 后形成的
  待验证机制；不是已批准的 Creative Pattern。
- **Insight Brief**：面向决策者的有界判断，必须同时呈现观察、推断、替代解释、未知、行动和护栏。

任何“爆款”字样都应在报告标题或脚注中绑定来源、窗口和证据级别。没有独立的实验、平台和
发布门禁时，不得写成“爆款原因”“必爆”“复制即可成功”。

## 1. 北极星故事线：从结果倒推可验证机制

咨询式报告不是按素材字段堆叠，而是按决策者的认知顺序推进：

```text
Question
  → Scope / Subject / Window
  → What actually happened (Observed)
  → Where the signal may be misleading (Counter-intuition)
  → Why it might happen (Mechanism hypothesis)
  → What can transfer / what cannot (Adaptation delta)
  → What would falsify it (Alternative explanation)
  → Smallest controlled test
  → Decision / next action
  → Guardrail / proof level
```

### 1.1 十幕叙事

| 幕 | 要回答的问题 | 必须留下的证据 | 典型错误 |
|---|---|---|---|
| 1. 决策问题 | 这份分析要支持哪个决定？ | `decision_question`、不支持的结论 | 先写“爆款分析”，没有决策对象 |
| 2. 观察边界 | 我们究竟观察了谁、哪个窗口、哪个平台？ | subject binding、window、source digest、capture time | 用品牌名或标题相似做模糊绑定 |
| 3. 信号事实 | 发生了什么，计数口径是什么？ | 原始值、分母、precision、availability | 把 UI 圆整值当精确值，或把短横线当 0 |
| 4. 反转 | 哪个看似合理的解释可能是错的？ | confounder、missing method、alternative explanation | 直接把排名写成原因 |
| 5. 机制 | 内容如何组织信息、情绪、证明和行动？ | 时间化 `DecompositionMap`、唯一主机制 | 把所有元素称为“风格” |
| 6. 信念迁移 | 观众的理解或信任可能在哪一刻改变？ | observation → bounded inference | 把体验语言升级成功效事实 |
| 7. 可迁移性 | 哪个功能可重编译，哪些表层必须替换？ | PatternHypothesis、Adaptation Delta | 复制台词、人物、音乐或镜头 |
| 8. 证伪 | 如果解释不成立，最可能是什么替代解释？ | falsifier、test design、stop condition | 只写支持证据，不写反证 |
| 9. 下一步 | 最小的可比实验是什么？ | Control/Variant、一个 changed dimension、digest | 同时改 Hook、时长、平台和卖点 |
| 10. 决策护栏 | 现在能说到哪一层？ | action、proof level、limitations | 把本地通过写成 production ready |

### 1.2 一页执行摘要顺序

执行摘要只保留六块：

1. **一句话结论**：候选在什么范围内呈现了什么观察；主机制仍是何种假设。
2. **最大反直觉**：最容易被误读的表象，以及它为什么不能直接支持结论。
3. **三条关键证据**：每条有 source ref、窗口和 availability。
4. **最大未知**：最可能改变判断的缺口，而不是把所有缺口都罗列。
5. **最小验证动作**：只改变一个 Creative Dimension，其他条件冻结。
6. **当前动作与护栏**：`revise`、`collect_evidence`、`test`、`hold` 或 `stop`，以及仍未通过的门。

## 2. 反直觉审计：先拆穿“为什么会爆”的直觉

以下命题是本框架的必过审计。报告每次至少挑三条与当前样本最相关的命题，并写出证据或
明确 `unknown`。

| 直觉 | 反直觉重述 | 审计动作 |
|---|---|---|
| 播放量高，所以内容好 | 播放量首先是分发机会与计数口径的观察 | 查账号基数、paid/organic、发布时间、样本、平台推荐、去重和快照；没有就保留未知 |
| Top 10 占比高，所以该机制带来 lift | 集中度可能只是报告排序、样本小或同一分发批次的结果 | 把集中度写成 distribution observation；要求 Control/Variant 或重复样本才能测试贡献 |
| 视频可播放，所以可以复用 | 可播放只证明读取路径，不证明 source-use scope、权利或原创 | 分开 `playable`、`rights`、`source_use_scope` 和 `originality_delta` |
| 有热门音频或标签，所以是 trend-native | 趋势可能只是装饰；去掉它，主机制仍可能是 proof、experience 或 narrative | 按 routing tree 重新问“趋势是否决定主要表达”，不能因 CTA、tag、背景音误路由 |
| 物理演示就是产品功效 | 现象、测量和允许结论是三件事 | 记录 `input → operation → observed phenomenon → allowed conclusion`；杀菌、疗效、精准等必须 Fact Gate |
| 卖点越多越有说服力 | 每增加一个可见表面，就增加一个 unsupported/excluded claim 风险 | 逐项做 claim map；selected/excluded deny-set 不得被模型补写 |
| CTA 存在，所以内容是转化型 | CTA 可能只是结尾惯例，不是决定表达的机制 | 只有 objection、promotion、CTA invitation 或 action path 成为主变量时才路由 conversion |
| 体验让人舒服，所以省时/有效 | 情绪和感官是表达观察，不是产品性能事实 | 将 `experience_pov` 与 `Product Fact` 分开，禁止从镜头顺序推导功效 |
| 同一品牌可以直接比较 | 品牌 workspace 不是 Product Family/Model/Variant binding | 要求 Snapshot、subject、window 和 digest；模糊 join 直接 blocked |
| 技术 QA 通过就是发布准备好 | 技术规格、事实、身份、来源范围、商业批准和平台能力是独立门 | 用六道 Media Integrity gate 和 Readiness proof levels 分层报告 |
| 一次成功就找到了赢家 | n=1 只能描述该次观察，不能估计方差或因果 | 写重复计划、停止条件和样本限制；禁止 winner/causal/universal 语言 |
| 缺少评论或分享就是低互动 | `0`、`not_reported`、`not_collected`、`source_ambiguous` 含义不同 | 复原原始 availability，不做空值填充或排序 |

## 3. “为什么可能扩散”的五层解释模型

把“为什么会爆”拆成五层，每层都要有观察、假设、替代解释和验证动作。五层不是因果链的
证明，而是防止把不同问题混在一起的诊断地图。

### L1 分发机会与样本环境

观察平台、账号规模、历史基线、发布时间、语言、市场、视频长度、付费/自然流量、样本分母、
推荐环境、报告采集和去重规则。它回答“有多少机会被看到”，不回答“为什么值得看”。

关键问题：

- 候选是否有帖级身份，还是只有账号级/播放列表级语境？
- 观看数是原始累计、去重数、跨平台合计还是报告内部排序？
- 该窗口是否把同一批分发、活动或付费合作混在一起？
- 数据缺口是否足以改变 Top 10 或平台比较？

### L2 即时理解与注意力语法

观察前三秒/前一拍的承诺、信息缺口、揭示顺序、字幕节拍、视觉反差、声音时序和认知负担。
项目中 `attention-grammar` 的五个互斥组件是：

`hook_trigger`、`reveal_cadence`、`caption_cadence`、`visual_contrast`、`sonic_timing`。

必须使用时间范围和 frozen Pattern 的 phase/shot anchor。可写“在 0–2 秒先呈现问题，再在
5 秒揭示操作”，不可写“因此提高留存”，除非有独立对照和测量。

### L3 信念、情绪与身份回报

观察问题/张力、惊讶、松弛、熟悉感、身份投射、POV/ASMR、动作连续性和产品在生活序列中的
位置。它回答“观众可能获得什么心理回报或理解路径”，不把情绪推断成睡眠改善、省时或疗效。

可用三个非因果标签：

- **recognition**：观众识别出自己的日常情境；
- **relief**：复杂任务被表达为更轻的动作序列；
- **surprise**：预期与可见结果之间有清晰差异。

标签只能进入 bounded inference；每个标签都要写至少一个替代解释（如账号人设、音乐、
季节性或样本选择）。

### L4 证明、可信度与行动摩擦

`proof-demonstration` 关注可观察的实验、对比、倒计时、量化或物理演示；`conversion-action`
关注异议、Promotion Fact、CTA invitation 和受控 action path。两者都要求把现象/行动和结论
拆开：

- 看到温度数字 ≠ 已证明精准控温；
- 看到黄油融化 ≠ 已证明杀菌或适合其他用途；
- 看到按钮和 CTA ≠ 已证明外链、下单或真实转化能力；
- 有 Promotion ≠ 可以让 provider 自由写最终文案，Promotion 必须是独立 Fact 且由服务端拥有最终 CTA。

### L5 平台语境、趋势与传播性

`trend-native` 只在外部趋势、共享语境、挑战/模板或音频功能决定主要表达时成立，且只允许
选择一个 `trend_signal_binding`、`trend_semantic_frame`、`template_grammar` 或 `audio_function`。
必须冻结 `TrendAdmissionRecord`：观察窗、市场/语言、source identity、target substitutions、
rights/use scope 和 originality handoff。它不证明当前热度、授权、平台兼容、模板激活、上传、
发布或原创批准。

## 4. 维度矩阵：爆款洞察究竟要看什么

每个维度都用同一行格式记录：

`Observation → Bounded inference → Alternative explanation → Evidence state → Transferability → Test/Action`。

未观察到的字段写 `not_present` 或 `unavailable`，不要填 0。

| 维度 | 要观察什么 | 可形成的有限假设 | 必问的反证 | 最小验证 |
|---|---|---|---|---|
| 1. 来源与主体有效性 | locator、digest、capture、playability、refreshability、rights、subject | 候选在指定窗口内可复核 | 是否只有 UI 卡片、账号总量或模糊品牌名？ | 重新读取同一 digest，建立 exact/source-scoped binding |
| 2. 表现信号与分母 | views/likes/comments/shares、precision、baseline、Top concentration、platform split | 某种表达值得进入测试池 | paid/organic、账号基数、发布时间、排序/去重是否解释了差异？ | 同窗口同主体的分层比较或复算 |
| 3. 受众张力/任务 | Problem、Pain、Tension、JTBD、场景和情绪代价 | 该场景可能更快建立相关性 | 是否是演员/账号身份或季节活动造成的相关性？ | 同一目标受众只改变张力 framing |
| 4. Hook 与注意力 | hook trigger、信息缺口、揭示 cadence、caption、contrast、sonic timing | 观众更容易继续理解下一拍 | Hook 是否与时长、语言、封面或平台分发混淆？ | 单独改变一个 attention component |
| 5. 叙事转化 | Problem → Intervention → Result/CTA 的关系和顺序 | 关系结构可能降低理解摩擦 | 结果是否只由文字/演员/产品知名度带来？ | 固定产品事实和时长，只改叙事关系 |
| 6. 可见证明 | 输入、操作、现象、测量、单位、允许结论 | 可信度信号可能提升理解 | 物理类比是否被过度外推成 efficacy/safety？ | 预注册 proof protocol，逐项 claim map |
| 7. 体验与身份 | POV、ASMR、感官、动作连续性、人物/产品身份 | 体验可能提升代入和记忆 | 是体验本身，还是音乐、色调、人物关系？ | 保持身份/音乐，单改体验组织关系 |
| 8. 转化行动 | objection、Promotion、CTA invitation、action path | 内容可能减少某种决策摩擦 | CTA 是否只是尾部模板？Promotion 是否失效？路径是否未实现？ | 只改一个 conversion component，独立校验 Promotion |
| 9. 趋势原生 | signal、semantic frame、template grammar、audio function、freshness | 外部语境可能降低进入门槛 | 去掉趋势表面后主机制是否仍成立？权利/平台证据是否缺失？ | 记录 TrendAdmissionRecord，先做 source substitution |
| 10. 商品事实与主张 | VO/caption/OCR/visual/title/tag/action/promo 的 Fact ID、Snapshot、deny-set | 目标表达可安全重编译 | AI selling point、参考台词或模型视觉是否越权？ | `viral-fact-mapping`，unsupported/excluded=0 才继续 |
| 11. 表层、原创与来源范围 | invariant/replaceable/prohibited/unknown、source-use、identity delta | 功能可迁移而表面不复制 | 人物、音乐、品牌、模板、构图是否仍可识别？ | `MediaIntegrityRecord` 六门独立审计 |
| 12. 目标身份与资产 | 颜色、Logo、组件、数量、跨镜连续性、Bundle provenance、QA | 目标表达可被准确识别 | 技术通过是否掩盖身份漂移或商用未知？ | 逐镜 target identity review + Asset refs |
| 13. 执行与实验性 | contract digest、Control/Variant、terminal、ledger、artifact hash、n | 结果可重建、可比较 | 是否只是一条成功样本或 broker/UI 假完成？ | 复核 PostgreSQL/ledger/artifact，计划重复 |
| 14. 媒体完整性与准备度 | artifact、technical profile、communicative surface、identity、source scope、originality | 可进入下一道明确门 | 是否把 local/CI/Private Gate 当 production？ | 六门逐项 `pass/pending/blocked`，不跨层升级 |
| 15. 证据与决策 | Fact/Inference/Unknown、proof level、action、guardrail | 现在最安全的下一步是什么 | 结论是否超过证据范围？ | `revise/collect_evidence/test/hold/stop` 之一 |

### 4.1 维度状态与迁移性

每行使用两个独立状态，避免“看起来强”被误读为“可复制”：

**Evidence state**

- `observed`：直接来源有范围、有定位；
- `inferred`：由一个或多个观察形成的有限假设；
- `unknown`：缺失、冲突、不可重现或方法未披露；
- `blocked`：下一道门不能安全继续。

**Transferability**

- `portable_function`：换产品、人物、文案和素材后仍能保持功能；
- `context_bound`：依赖平台、窗口、账号、受众或趋势语境；
- `surface_bound`：依赖人物、台词、音乐、品牌或特定构图；
- `unknown`：无法判断，先收集证据。

## 5. 主机制路由与“机制—维度”关系

一个 Reference 只能有一个 `Primary Replication Mechanism`：

1. `trend-native`：趋势/音频/平台梗决定主要表达；
2. `conversion-action`：异议、促销、CTA、行动决定主要表达；
3. `proof-demonstration`：实验、对比、量化、物理演示决定主要表达；
4. `experience-pov`：POV、ASMR、感官、日常情绪决定主要表达；
5. `attention-grammar`：Hook、揭示、字幕、视觉反差、声音时序决定主要表达；
6. `narrative-transformation`：问题—转折—解决—结果关系决定主要表达。

CTA、背景音、标签或一次明显的 cut 不能单独决定路由。两个机制不能用一个可观察维度分离时，
输出 `blocked: primary_mechanism_ambiguous`，拆成两个 Variant 或缩小问题。

### 5.1 次级机制处理

次级机制不是删除，而是写入 frozen context：

- 明确它的观察范围；
- 写明本轮不改变它；
- 不让它进入“为什么会爆”的主结论；
- 若后续要测试它，建立新的 Control/Variant 和 digest。

这一步防止把 Hook、ASMR、proof、trend 和 CTA 全部打包为不可证伪的“风格”。

## 6. 从洞察到实验：把故事收敛为一个反事实

一个好的洞察最终要能回答：**如果只改变 X，其他都不变，Y 是否仍出现？**

### 6.1 反事实句式

```text
在同一 Product Snapshot、同一平台/市场/语言/时长/素材/预算和同一事实集合下，
仅改变 [一个 Creative Dimension]，我们观察 [预注册现象/行为]；
若 [替代解释] 成立，则 [可观测反证] 应出现。
```

### 6.2 冻结清单

Control 与 Variant 除唯一 changed dimension 外，至少冻结：

- subject identity、Product Snapshot、selected/excluded Fact 顺序；
- 时长、phase/shot budget、语言、市场、平台、受众 profile；
- provider/model/version、输入素材、数量、分辨率、预算、sound policy；
- Promotion Fact、CTA ownership、rights/use scope、target identity；
- execution terminal、ledger、artifact/hash 记录方式。

### 6.3 最小结果口径

预先声明观察指标及其 canonical `MeasurementState`：`observed`、`missing`、`unknown`、
`not_reported`、`not_collected`、`not_applicable`、`redacted`、`source_ambiguous`。
当 `state=observed` 且数值为 `0` 时，报告文案可称“observed zero”，但机器字段仍是
`state=observed, value=0`；`unavailable` 只用于 section/gate。未测量不填 0。

即使重复后出现差异，也只能在样本、窗口和设计范围内描述；没有独立设计时不得写 causal lift。

## 7. 证据分层与四个平面

项目要求四个 typed evidence plane 不互相升级：

在输出字段中严格区分两个概念：`evidence_level` 表示结论本身是 `Fact`、`Inference` 还是
`Unknown`；`proof_level` 表示验证发生在 `local`、`CI`、`private`、`deployment`、`live` 或
`production` 哪一层。一个 brief 可以同时有 `evidence_level=Inference` 和
`proof_level=local`，不能把二者写成同一个“置信度分数”。

| 平面 | 回答什么 | 可以支持什么 | 不能支持什么 |
|---|---|---|---|
| Product Truth | 商品在某 Snapshot 中可说什么 | `confirmed`/`locked` Fact-bound claims | 排名、热度、模型推断 |
| Performance | 指定窗口发生了什么 | Performance Observation、Creative Signal | 因果、winner、通用偏好 |
| Experiment | 冻结配置下发生了什么 | 可复核能力/执行/样本观察 | 产品事实、商业批准 |
| Asset / Media | 某 artifact 如何生成、质量与身份如何 | provenance、technical/identity QA | 权利、平台、发布、生产批准 |

Insight Brief 必须在文中标出每条结论属于哪个平面，并在交界处写 handoff，而不是创建一个
“万能 evidence”列表。

### 7.1 Proof level

至少保留以下层级：

`local` → `CI` → `private` → `deployment` → `live` → `production`。

较低层级通过不能自动升级到较高层级。Skill quick validation 只证明结构和合成边界；
Private Gate 只证明被批准本地库的技术一致性；图谱只提供导航。

## 8. 项目案例的正确讲法

### 8.1 Leap：高集中度是入口，不是结论

项目审计的德国奶瓶清洗/暖奶器报告在 2026-08-21 至 2026-08-27 的有界窗口内记录 22 个视频、
10,312 views 和 37 likes；Top 10 贡献 8,878 views（86.09%）。这能支持：

- 报告内部的表现集中观察；
- 三组待测 Creative Signals：relief transformation、visible proof、embodied experience；
- 需要复算或测试的候选方向。

它不能支持：

- 某个方向造成了 86.09% 的贡献；
- 该窗口代表所有市场、产品或周期；
- `杀菌`、`精准控温`、`保温`、`煮蛋`等 Reported Product Claim 已被确认；
- 评论/分享显示为短横线就等于 observed zero。

报告未披露采集、去重、排序、paid/organic、账号规模、发布时间、快照和模型复核方法；这些缺口
必须进入 Unknown/Guardrail，而不是被“高集中度”掩盖。

### 8.2 KleanPal Pro：机制可拆不等于热度已证

本地案例把一条约 28 秒官方片拆为 `experience-pov`：生活任务进入 → 产品作为中段动作 →
生活收尾；`Proof`、显式 `CTA` 和帖级 TikTok 热度没有被观察到。它说明：

- `DecompositionMap` 可以在有界范围内重建时间、视觉、音频和 claim candidates；
- `PatternHypothesis` 可以把生活序列写成 invariant，把人物、音乐、构图和无依据功效写成
  replaceable/prohibited；
- 目标版本的技术规格通过或存在，不代表 reference 的帖级身份、热度、权利或发布权限闭合。

因此案例的结论仍是“本地筛查、热度未获证、不得声称爆款”，而不是成功复刻。

### 8.3 Oumomo：技术成功与内容失败可以同时成立

clean-room 实验显示：Job/媒体技术链路可以成功，但 ASR/OCR 或脚本表面仍会产生无依据功效、
包装、比较和单位错误。这个反例说明：

- Provider succeeded ≠ factually acceptable；
- 生成了 MP4 ≠ 产品身份/claim/权利通过；
- 付费 dry-run ≠ OAuth、账号、发布或 production；
- 事实 allow-list、deny-set、版本与媒体门必须在服务端和审阅链中独立存在。

## 9. 质量闸门：交付前的挑剔审阅

审阅者按以下顺序问，不要先被漂亮画面或排名带走：

1. 我能否复现主体、窗口、来源和 digest？
2. 我是否把 0、缺失和来源歧义分开？
3. 时间线是否足以重建主机制？
4. 主机制是否唯一，次级机制是否冻结？
5. 每条目标 claim 是否回到同一 Snapshot 的 `confirmed`/`locked` Fact？
6. 我是否写出了至少一个替代解释和一个证伪测试？
7. Invariant、replaceable、prohibited、unknown 是否分开？
8. Control/Variant 是否只改变一个 Creative Dimension？
9. Media Integrity 六门、rights、source-use、originality 是否各自有状态？
10. Action 是否属于 `revise/collect_evidence/test/hold/stop`，且 proof level 没被升级？

任一问题无法回答，就把状态降为 `proceed_with_limits` 或 `blocked`，不要用更强的语言填补空白。

## 10. 推荐的最终结论句式

```text
在 [subject + platform + market + window] 内，来源显示 [observation]，其中 [availability/分母限制]。
这支持一个 [primary mechanism] 的 Creative Signal：内容可能通过 [bounded function] 降低 [理解/情绪/行动]
摩擦；但 [alternative explanation] 尚未排除，且 [unknown] 未闭合。
可迁移的是 [invariant function]，必须替换或禁止的是 [surface/claim/rights boundary]。
下一步只测试 [one changed creative dimension]，冻结 [key fields]，结果只解释到 [proof level/scope]。
当前动作： [revise | collect_evidence | test | hold | stop]。
```

这类句式把“洞察”变成可交接、可复盘的工作物，而不是一次性的聪明解读。
