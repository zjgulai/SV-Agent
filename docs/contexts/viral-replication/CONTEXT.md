# Viral Replication Intelligence

定义如何从一个有界的高表现参考内容中提取可验证的创意机制，再把它编译成事实受约束、单变量可比较、可追溯的复刻实验。这个上下文不把排名当成因果，不把参考视频台词当成 Product Fact，也不承担媒体生成、账号发布或商业批准。

## Language

### Agent runtime

**SV-Agent Task**:
一个持续保存用户目标、决策问题、范围与停止条件的任务身份；它可以包含多次 Run，但不表示任何一次技术执行。
_Avoid_: Job, conversation, browser draft

**SV-Agent Run**:
针对一个 Task revision 的有界执行尝试，保存计划、业务状态、artifact frontier 与待处理决定；它不使用 Job 的技术状态表示业务完成。
_Avoid_: Job attempt, workflow status, succeeded

**Run State Semantics**:
对 Run state 含义的显式分类：`orchestration`、`business_disposition`、`approval_pause` 或 `technical_terminal`。分类用于避免 UI 和应用层把 Job 成功、Human Decision、业务 blocker 与 review-ready 结果压成一个笼统状态。
_Avoid_: one global status, Job outcome, commercial approval

**Run Plan**:
SV-Agent 为一个 Run 编译的版本化 orchestration plan，描述能力步骤、前置条件、checkpoint 和下一安全动作。
_Avoid_: Replication Plan, Skill file, arbitrary DAG

**Tool Run**:
SV-Agent 对一个 typed capability 的一次逻辑调用，可关联一个技术 Job，但不继承 Job 的业务含义。
_Avoid_: Job, provider approval, business completion

**Approval Request**:
绑定精确 Task/Run revision、gate、artifact version/digest、预期影响和 stale 条件的不可变人类决定请求。
_Avoid_: generic approval, Agent recommendation

**Decision Event**:
可信 Human 对一个 Approval Request 作出的追加式决定；Agent 或 System 的推荐、状态转换和技术结果不是 Decision Event。
_Avoid_: Agent approval, status update

**Runtime Lineage Link**:
由权威 record 或 application service 验证后追加的 artifact 派生关系；它与 artifact payload 中的 declarative lineage 分开。
_Avoid_: declared input ref, inferred relationship

**Command Receipt**:
由服务器生成 scope、规范化输入 digest 并绑定 Task 的不可变恢复记录；同 scope/key/digest 只返回原结果，不执行第二次写入，不同 digest 必须冲突。
_Avoid_: client-generated digest, retry token without result, Job idempotency

**Factual Replay**:
按共享数据库 sequence 合并 Task、ToolRun 与 Human Decision 的已持久化事实，并在首个分页请求冻结 through-sequence。Replay 只验证并读取记录，不运行 Skill、Tool、Job、provider 或模型推理。
_Avoid_: event sourcing rebuild, model explanation, workflow resume

### Replication method

**Goal Track**:
Task revision 上的产品目标，只允许 `product_replication` 或 `brand_voice_social_resonance`。它回答为什么做这项任务，不参与六种 Primary Replication Mechanism 的路由。
_Avoid_: Primary Replication Mechanism, content type

**Reference Bundle**:
一次被范围、来源、digest、平台、时间窗和权限状态约束的参考内容观察。
_Avoid_: viral video, winning asset

**Viral Candidate**:
在有界 Performance Window 内表现突出、值得进入复刻研究的内容候选；它是观察标签，不是普适 winner。
_Avoid_: proven winner, universal formula

**Primary Replication Mechanism**:
一次复刻中唯一被允许作为主变量的机制：`narrative-transformation`、`proof-demonstration`、`experience-pov`、`attention-grammar`、`conversion-action` 或 `trend-native`。
_Avoid_: content type, style bucket

**Creative Dimension**:
某个 Primary Replication Mechanism 内唯一允许改变的 closed component。机制与维度必须匹配；同一 Run 选定后不可替换，含糊或跨机制组合必须 blocked 或拆成另一个 Run/Variant。
_Avoid_: Goal Track, free-form variable, hidden second variable

**Conversion Component**:
`conversion-action` 内唯一可改变的互斥维度：`objection_resolution`、`promotion_contract`、`cta_invitation` 或 `action_path`。其余 conversion elements 必须冻结；Promotion 独立于普通 Facts；当前 `action_path` 只可记录受控 binding 或 `not_applicable`，不自动代表外部跳转或交易能力。
_Avoid_: free-form sales copy, checkout capability

**Trend Component**:
`trend-native` 内唯一可改变的互斥维度：`trend_signal_binding`、`trend_semantic_frame`、`template_grammar` 或 `audio_function`。它们分别回答有界外部信号、共享语境、可观察模板关系和声音的时间功能；其余 trend components 必须冻结。
_Avoid_: trend bundle, platform template capability

**TrendAdmissionRecord**:
随 `TrendNativePlan` 冻结的文档级准入记录，保存 reference analysis/adaptation/source-audio/template evidence states、平台/市场/locale 的 observed constraints、target substitutions、source identity exclusions 和进入 `MediaIntegrityRecord.originality_delta` 的 handoff。它不是音频/模板许可、平台兼容、平台调用、上传、发布或原创批准；当前 `execution_capability=not_implemented`。
_Avoid_: platform-compatible, auto-licensed, publishing-ready

**Media Integrity Gate**:
在冻结 ReplicationContract 并依次形成 fact-bound ScriptVersion、StoryboardVersion 后运行的跨机制、fail-closed 审计门。它不参与 Primary Replication Mechanism 路由、不创建新的 Creative Dimension，也不渲染或发布媒体。
_Avoid_: new content type, media approval

**MediaIntegrityRecord**:
`media-integrity-v1` 的文档级记录，分别保存 artifact traceability、technical profile、communicative surface、target identity continuity、source-use scope、originality delta，以及 tool/human fallback、blockers、unknowns、evidence limits 和 disposition。`preflight` 必须将未来 artifact 依赖项写成 `not_applicable_pending_artifact`；`artifact_review` 也只代表有范围的本地审计。
_Avoid_: copyright clearance, commercial approval, platform-compatible, publishing-ready

**Secondary Mechanism**:
参考内容中存在但本次不作为主变量的辅助机制；它必须保持冻结或单独拆成另一个 Variant。
_Avoid_: hidden second variable

**Attention Observation**:
对 Hook、信息揭示/镜头节奏、字幕节拍、视觉反差或声音时序的时间化、来源可回指观察。它描述参考内容怎样组织信息，不证明注意力、留存、播放或转化效果。
_Avoid_: retention driver, proven hook

**Attention Component**:
`attention-grammar` 合同中唯一可改变的表达组件：`hook_trigger`、`reveal_cadence`、`caption_cadence`、`visual_contrast` 或 `sonic_timing`。其他 attention component 保持冻结。
_Avoid_: attention style bundle

**Surface Feature**:
台词、字幕、人物、道具、镜头表层、品牌元素和音频等可替换或受权利约束的表达表面。
_Avoid_: creative mechanism

**Decomposition Map**:
对参考内容的时间线、Hook、Pain、Proof、Experience、Visual、Audio、Text、CTA、声明候选和未知项的结构化观察。
_Avoid_: prompt summary

**Pattern Hypothesis**:
由 Decomposition Map 提取的待验证创意机制，明确 invariant、replaceable、prohibited 和 evidence scope。
_Avoid_: winning formula

**Replication Plan**:
在机制路由后形成的可修订 workflow planning state，记录唯一主机制、唯一 Creative Dimension、Control/Variant 意图和冻结约束。它不是不可变合同，不能授权 provider、媒体生成或外部行动。
_Avoid_: approved execution contract

**Fact Map**:
把目标表达中的可见/可听 claim 映射到同一 Product Snapshot 的 `confirmed`/`locked` Facts，并保留 excluded、unsupported、Promotion 和 unknown 状态的审计结果。
_Avoid_: model-inferred product truth

**No-product Claim Scope**:
Brand Voice / Social Resonance 只有在 FactMap 与 ReplicationContract 明确 `claim_scope=no_product_claims` 且完全不包含商品声明时，才允许使用 `subject_binding.state=not_applicable`。此时 Product Snapshot identity、claim mappings、selected/excluded Fact sets 和 unsupported claims 必须为空，并在 limitations 中说明范围。`claim_scope=product_claims` 时必须绑定 exact/reviewed Product Snapshot，至少一个 eligible Fact 支持商品声明；同一 FactMap 中的非商品表达才可单独使用 `non_product_claim` disposition。Executable validator 已将 discriminator 闭合为 `product_claims | no_product_claims`，并验证 FactMap 到 ReplicationContract 的 scope、subject 与 Fact-set 一致性。
_Avoid_: unbound product claim, implicit brand-only mode

**Replication Contract**:
在 Fact Map 闭合后，冻结 Reference、Control、Variant、唯一 Creative Dimension、Product Snapshot、Facts、平台、市场、预算、停止条件和验收门的不可变实验合同。
_Avoid_: free-form remake request

**Adaptation Package**:
在不可变 Replication Contract 下编译的机制专属 handoff；承载 narrative adaptation、proof protocol、POV adaptation、attention plan、ConversionActionPlan 或 TrendNativePlan。它已有本地 machine-readable schema 和 validator，但不代表已经新增 PostgreSQL 表、runtime persistence、provider、render 或 publish capability。
_Avoid_: mutable prompt bundle

**Adaptation Delta**:
从参考表面迁移到目标商品、市场、语言和授权素材的明确变化集合；它不是隐藏变量容器。
_Avoid_: prompt variation

**Replication Finding**:
由 Contract 和可核查 Artifact 支持的观察、范围内推断、未知项、异常和下一步；不能直接升级为 Product Fact 或生产证明。
_Avoid_: growth proof

## Primary mechanism partition

一个 Reference 只能选择一个 `Primary Replication Mechanism`。如果两个机制无法分离，必须拆成两个 Variant 或标为 blocked；不能创建含糊的 hybrid 类型。

- `narrative-transformation`: 主要复制问题、转折、解决和结果的叙事关系。
- `proof-demonstration`: 主要复制可观察实验、对比、倒计时、测量或物理演示。
- `experience-pov`: 主要复制 POV、ASMR、感官触点、动作连续性或情绪体验。
- `attention-grammar`: 主要复制 Hook、信息揭示/镜头节奏、字幕节拍、视觉反差或声音时序；合同内只改变一个 Attention Component。
- `conversion-action`: 主要复制异议处理、促销合同、CTA 和行动路径。
- `trend-native`: 主要复制受外部趋势、平台梗、音频或挑战模板支配的表达语法；合同内只改变一个 Trend Component，并冻结 TrendAdmissionRecord。

## Evidence boundary

- Performance Observation 只能说明指定 subject 和 window 内发生了什么。
- Reference Video 的口播、字幕和画面不能自动成为 Product Fact。
- Content Direction 和 Creative Signal 是假设输入，不是 approved Creative Pattern。
- Attention Observation 只能支持一个待验证的表达假设；它不证明 retention、播放、转化、causal lift 或 winner status。
- Trend Observation 只能支持在指定平台、市场、语言和时间窗内观察到的表达假设；它不证明当前热度、推荐、音频/模板权利、平台兼容、模板激活、上传、发布或表现。
- source audio/template 的可播放或可见性不等于 reuse permission；target 文本、视觉和声音必须能与 source identity surface 区分。`TrendAdmissionRecord` 的 `originality_delta` 只能进入 `MediaIntegrityRecord.originality_delta`，不得写成已通过；`source_use_scope` 与 `originality_delta` 分别回答使用范围和表达差异，不能互相替代。
- Asset Bundle 结构有效、Aggregate Index disposition、Private Gate receipt、技术 probe、模型相似度或单一人审都只能说明其自身证据层；它们不能被升级为权利、商业、平台、发布或 production 结论。
- 只有同一 Product Snapshot 的 `confirmed` 或 `locked` Product Fact 才能支持商品声明。
- `unknown`、`not_reported`、`not_collected`、`source_ambiguous` 和 observed zero 保持不同含义。
- 技术执行成功、skill 验证通过或本地媒体存在，都不代表商业批准、部署、live 或 production acceptance。

## Required artifact chain

```text
ReferenceBundle
  → DecompositionMap
  → PatternHypothesis
  → ReplicationPlan
  → FactMap
  → immutable ReplicationContract
  → AdaptationPackage
  → ScriptVersion
  → StoryboardVersion
  → MediaIntegrityRecord
  → ReplicationFinding
```

`ReplicationPlan` 是可修订的 workflow planning state；只有 Fact Map 闭合后的 `ReplicationContract` 可以冻结并进入 AdaptationPackage、ScriptVersion 和 StoryboardVersion 编译。九类新增 artifact 的 executable machine-schema authority 是 `tools/viral_replication/artifact_contracts.py`；SV-102 只新增不可变 `sv_artifacts` envelope 表，尚未实现会调用该 validator 的 Artifact writer，因此不能声称 canonical artifact 已持久化。标准完整执行链必须同时包含 ScriptVersion 与 StoryboardVersion，再进入 MediaIntegrityRecord；早期 bounded `preflight` 可只绑定二者中至少一个 typed ref，但这不等于完整链闭合，也不能进入 ReplicationFinding 或下一阶段。没有受控媒体 Artifact 时只能保留 preflight pending state；`artifact_review` 必须另有受控媒体 Artifact，且仍只代表同一 gate 内的 bounded review。

每个箭头都必须保留 source refs、digest、scope 和失败边界。任何阶段缺少可复核证据时，输出 `blocked` 或 `unavailable`，不得用模型推断补齐；任何阶段均不得暗示 render、publish、rights、commercial 或 production approval。
