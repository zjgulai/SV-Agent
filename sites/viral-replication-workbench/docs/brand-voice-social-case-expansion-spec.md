---
status: awaiting-user-gate
scope: site-only
proof_level: source-limited
owner: Momcozy Viral Replication Workbench
last_updated: 2026-10-11
---

# Momcozy Brand Voice Social Case Expansion Specification

状态：`BV-P1-002` 已完成本地验证；`BV-GATE-001` 的本地 preflight 已完成，当前等待案例级外部权利、儿童安全、连接器和行动批准证据。

本规格把网站中的“品牌声量 / Baby Social”案例与产品复刻案例分轨。它只定义案例档案、证据表达和本地静态 MVP 的用户路径，不把社媒数据、原始儿童媒体、商业授权或发布能力偷渡进来。

## 1. Problem Statement

当前网站的 Case Archive 只有 KleanPal Pro 和 Oumomo 两个入口，访客看到的主要是产品体验、工程链路和内容事实失败。已有的母婴 TikTok 深度洞察被放在独立报告页，用户无法从案例档案发现它，因此网站给人的印象是“只有产品视频，没有 baby 社媒声量案例”。

这不是简单缺少一张视频卡，而是案例目标、证据和风险没有分层：

- `product_performance` 关注产品理解、事实绑定、转化表达和复刻合同；
- `brand_voice_social` 关注父母身份认同、社会共鸣、品牌心理可得性和社区参与；
- `campaign_awareness_benchmark` 关注有明确媒体投放、UGC 或 Brand Lift 设计的活动；
- `counterexample_hold` 专门展示权利、儿童安全、来源和指标口径的阻断。

如果把这些内容按同一套“爆款/最终片/转化”排序，会把第三方播放量误写成品牌认知，把自然流量误写成付费效果，也会诱导用户复制儿童、创作者、音乐或危险照护表面。

## 2. Goal and Success Criteria

### 2.1 产品目标

在不增加产品 CTA、不引入产品功效 claim、不托管原始儿童视频、不接入真实社媒连接器的前提下，让用户可以：

1. 从 Case Archive 一键进入一个 baby social / brand voice 案例；
2. 一眼区分“品牌声量”与“产品复刻”；
3. 看到来源、Performance Window、Performance Observation、缺失值、Creative Signal、权利、儿童安全和媒体状态；
4. 从观察进入有限机制假设，再进入一个最小、非卖货的 Momcozy 品牌声量测试方向；
5. 知道当前案例是否只能分析、是否可以形成概念、是否仍需要外部授权或测量。

### 2.2 P0 完成定义

P0 只有在以下条件全部满足时才算完成：

- `BV-001` 已从 Case Archive 可达，不再只藏在 Deep Insight 页面；
- 页面明确显示 `track=brand_voice_social`、`intent=brand_awareness_only` 和 `status=proceed_with_limits`；
- 当前候选的播放量、来源和缺失值保持原始语义，不被写成 winner、因果、Brand Lift 或销售提升；
- 页面不上传、不重新托管原始儿童视频或原始配乐；
- 页面显示 `rights_scope=analysis_only`、儿童安全未知项和 `media_state=metadata_only`/`external_link`；
- 案例详情能跳转到既有深度洞察报告和脱敏 Insight Brief JSON；
- 静态 HTML、Insight Brief validator、浏览器路径和移动端布局验证通过；
- 改动只写入站点嵌套仓库，不自动 commit、部署或公开发布。

### 2.3 P1 目标

P1 在 P0 稳定后再增加第二类 baby social 机制、Social Resonance Map、评论/分享语义和活动 benchmark 卡片。P1 不改变既有六类 primary mechanism；品牌声量是目标包装层，不是第七种机制。本批 `BV-P1-002` 已加入一个 `attention-grammar` 候选与独立 `campaign_awareness_benchmark` lane；两条轨道保持 source-limited、metadata-only 和不可跨轨道排名。

## 3. Non-goals and Hard Boundaries

本规格明确不做：

- TikTok 全量抓取、自动发现、自动排名或自动判定“爆款”；
- 真实社媒账号连接、发布、广告投放、Creator marketplace 或商业合作；
- 原始 TikTok 视频、儿童肖像、原始音频或完整网页的下载、重新托管和再分发；
- 从播放、点赞、评论或第三方榜单推导 Brand Lift、causal lift、销售提升、市场份额或普适公式；
- 生成真实儿童 likeness、仿拍具体儿童、复用创作者台词或复制原始镜头；
- 把未经 `confirmed`/`locked` 事实绑定的 Momcozy 产品 claim 放进品牌声量案例；
- 改动 apps/web、API、数据库、迁移、私有资产库、Private Gate 或现有 `VR-P...` 能力台账；
- 通过 Sites 或其他渠道自动部署、发布或改变访问权限。

## 4. Product Decisions

### 4.1 Case tracks

| Track | 目标 | 允许的内容 | 证据口径 |
| --- | --- | --- | --- |
| `product_performance` | 产品理解、体验、转化和受控复刻 | KleanPal、Oumomo、事实绑定和 CTA | Product Snapshot、Script/Storyboard、Media Integrity、Finding |
| `brand_voice_social` | 品牌声量、父母身份认同、心理可得性、社区参与 | 非产品或产品偶然出现的 baby/parenting social candidate | Performance Window、Performance Observation、Creative Signal、Social Resonance |
| `campaign_awareness_benchmark` | 学习成熟活动的声量设计和测量 | 官方 campaign、UGC、Brand Lift、paid/organic mixed | 明确 paid/organic、活动窗口、分母和测量方法 |
| `counterexample_hold` | 展示阻断和反例 | 音乐权利未闭合、儿童安全风险、来源不明或指标自相矛盾 | 只保留观察与阻断原因，不生成复刻建议 |

轨道之间不得做无条件的跨轨道排名。尤其不能把 `brand_voice_social` 的第三方 views 与 `campaign_awareness_benchmark` 的 paid Brand Lift 放在同一张“爆款榜”。

### 4.2 Objective model

品牌声量案例默认使用：

```text
intent = brand_awareness_only
conversion = not_applicable
purchase_intent = not_collected
sales_lift = out_of_scope
cta = none
```

品牌声量不是“没有指标”，而是指标从销售结果切换为：

- 注意力代理：views、reach、focused view、completion；
- 社会共鸣：shares、saves、comments、UGC、profile visits；
- 品牌记忆：recall、familiarity、favorability、branded search；
- 风险信号：负向评论、儿童安全投诉、权利争议和错误产品联想。

每个指标必须绑定 `source_ref`、采集时间、分母、paid/organic 状态和 `Observation Availability`。缺失必须使用 `not_reported`、`not_collected`、`not_applicable`、`redacted` 或 `unresolved`，不能用 0 或空字符串伪造比较。

### 4.3 Evidence and proof-level model

站内沿用 Content Performance Intelligence 的术语：

- `Performance Window`：品牌、平台、市场、时间范围和采集时刻；
- `Performance Observation`：来源直接显示的计数或汇总；
- `Content Direction`：待验证的表达方向，不是已批准模式；
- `Creative Signal`：值得继续验证的关联，不证明因果；
- `Observation Availability`：明确缺失值语义；
- `Evidence Disposition`：`cite`、`recompute`、`test` 或 `reject`；
- `proof_level`：`local`、`reported`、`measured`，不允许把 `local` 升级为生产或商业证明。

默认状态机：

```text
candidate
  -> proceed_with_limits
  -> ready_for_next_gate
  -> awaiting_user_gate
  -> done

candidate
  -> hold_rights | blocked | counterexample
```

`done` 只表示该案例在当前范围的行为、证据和验证都完成，不表示爆款、商业批准、发布资格或生产验收。

### 4.4 Rights, music and child-safety model

每个案例必须独立呈现：

- `source_use_scope`：`analysis_only`、`external_link`、`internal_review`、`rights_cleared_embed`、`blocked`；
- `music_rights`：`unknown`、`cleared`、`not_applicable`、`blocked`；
- `child_safety`：监护人同意、肖像范围、身份暴露风险、危险模仿风险；
- `commercial_disclosure`：自然、付费、UGC boost 或未知；
- `media_state`：`metadata_only`、`external_link`、`internal_review`、`rights_cleared_embed`、`blocked`。

默认原则：没有授权就只展示脱敏元数据和外部来源链接，不展示原始儿童媒体；没有音乐授权就不下载、不嵌入、不复用音频；没有监护人/创作者授权就不生成或复用真实儿童 likeness。

## 5. BV-001 Existing Maternal TikTok Candidate

### 5.1 Case identity

```yaml
case_id: bv-001-messy-eater-cleanup
track: brand_voice_social
intent: brand_awareness_only
title: Baby Social Voice · Messy Eater Cleanup
primary_mechanism: proof-demonstration.task_bundle_visibility
secondary_mechanism: experience-pov
status: proceed_with_limits
next_action: collect_evidence
proof_level: local
media_state: metadata_only
source_use_scope: analysis_only
```

### 5.2 What is observed

既有报告描述一条非产品的育儿内容：宝宝、餐椅和餐盘被同时移入淋浴区，并在一个连续动作中完成清理。第三方公开记录页报告约 8.7M TikTok views，并给出创作者 credit、美国场景和 Parenting & Kids 分类。

### 5.3 What is not proven

以下内容保持未知：

- 原始 TikTok 帖子 URL 与帖子级身份；
- likes、comments、shares、completion、保存和账号规模；
- paid/organic 状态、采集/去重/排序方法和分母；
- 原始媒体、儿童肖像、创作者和配乐的复用权利；
- 观看量是否带来品牌认知、品牌搜索、销售或因果 lift；
- 这个机制是否能跨市场、跨年龄、跨产品迁移。

### 5.4 Brand-awareness storyline

```text
parent tension
  -> 三条育儿清洁任务被看见
  -> 一个可见动作压缩任务成本
  -> 轻微意外感 + “这就是我家”的身份识别
  -> 可能引发分享、评论或转发
  -> Momcozy 作为理解母亲日常的品牌语境
  -> 通过 recall/familiarity/positive association 测试，而不是销售 CTA
```

这是一条机制假设，不是因果结论。账号分发、编辑精选、异常场景、跨平台传播和样本选择都必须作为替代解释保留。

## 5.5 BV-002 Baby Reaction Candidate

`bv-002-baby-reaction-diaper-change` 使用 [ARK record/19758](https://ark.media/record/19758) 作为独立公开登记来源。来源页报告美国 Parenting & Kids 内容、2025-08-12 发布日期和约 11.1M TikTok views；这些是 `reported` attention proxy，不是原帖、品牌 lift 或授权证明。

该候选的主机制是 `attention-grammar`，维度为 `single_reaction_reveal`，辅助观察为 `experience-pov`。可研究的最小结构是“routine context → 一个可读表情 → 父母识别假设”，但不能复用换尿布、真实儿童 likeness、原始声音、创作者身份或具体剪辑。由于换尿布属于 intimate-care context，guardian consent、likeness、music 和 commercial disclosure 均保留为未知；案例停留在 `proceed_with_limits` / `analysis_only` / `metadata_only`。

站点只提供脱敏 `case-record.json` 与 `social-resonance-map.json`。互动指标、paid/organic、帖子分母、Brand Recall、Familiarity 和 Exposed-vs-Control lift 均保持 `not_reported` / `not_collected`。任何后续创意只能改用非私密、获授权的成人/道具情境，并必须重新通过 `BV-G2 rights-child` 与 `BV-G3 mechanism`。

## 5.6 CB-001 Campaign Awareness Benchmark

`bv-benchmark-nestle-generations-of-love-2024` 使用 [TikTok for Business 的 Nestlé Generations of Love case](https://ads.tiktok.com/business/en/inspiration/nestle-branded-mission-case-study?redirected=1) 与 [TikTok Brand Lift Studies guidance](https://ads.tiktok.com/resources/help/article/tiktok-brand-lift-studies?lang=en) 作为 benchmark-only 来源。官方案例页报告 2024-02-06 至 02-12 的 Philippines、Indonesia、Malaysia、Thailand、Vietnam 五市场活动，使用 Branded Mission、Branded Effect、Branded Hashtag Challenge 和 selected UGC boost，并报告各市场的 ad recall / familiarity / intent、1,554 条视频、1,135 位用户、65 条 boosted submissions 和 4.71% boosted engagement rate。

这些字段只用于学习活动窗口、市场拆分、organic/boosted UGC 分层和 Brand Lift preflight。官方 guidance 描述 randomized Exposed/Control、polling/statistical comparison 与 account-manager setup；站点不会把 reported lift 解释为 TikTok-only causal result，也不会把它迁移为 Momcozy lift、销售或产品 claim。该 lane 的 `primary_mechanism` 为 `not_applicable`，`mechanism_scope=benchmark_design_not_replication`；创意机制字段只记录活动设计不变量，不生成仿拍建议。

该 benchmark 另保留 growing-up milk category、mixed organic/boosted disclosure、market-level sample 和分母缺失等限制。站点只下载脱敏 `benchmark-record.json`，不托管广告、创作者视频、儿童媒体、音乐或 connector 结果；与 `brand_voice_social` 候选不放在同一 views 排名。

## 6. Information Architecture and User Journey

### 6.1 Archive entry

Case Archive 顶部增加四个筛选：

```text
全部 | 产品复刻 | 品牌声量 | 活动 Benchmark | 反例 / 门禁
```

P0 只新增第三个案例 tab；P1 再将 tab 改为 data-driven filter，不重写现有 KleanPal/Oumomo 案例。

### 6.2 Case card

案例卡必须在首屏显示：目标、主机制、产品出现状态、证据级别、付费状态、权利状态、儿童安全状态和下一道门。

推荐 BV-001 的可见标签：

```text
品牌声量 · 非卖货
source-limited
analysis-only
child-safety pending
proceed_with_limits
```

### 6.3 Detail sections

品牌声量案例详情采用以下顺序：

1. 这条内容研究什么品牌问题；
2. Performance Window 与来源登记；
3. 观察到的内容 beats；
4. Social Resonance Map；
5. 主要机制与替代解释；
6. Momcozy 非卖货迁移方向；
7. 未知项和证据限制；
8. 权利、音乐和儿童安全；
9. 脱敏产物下载；
10. 下一道 gate 和允许的 action。

页面必须同时提供既有 `deep-insight.html` 链接和脱敏 `Insight Brief JSON` 下载；不得复制或重新打包原始 TikTok 媒体。

### 6.4 Target concept boundary

后续允许形成两个本地概念版本，但不能在 P0 生成：

- `A0 social-only`：只保留父母社媒语境，不出现产品和 CTA；
- `A1 brand-cue`：只增加 Momcozy 品牌识别元素，不增加产品功效 claim。

A0/A1 只能有一个 changed creative dimension，且必须经过 Media Integrity、source-use、originality 和 child-safety 审查。

## 7. Case Data Contract

P0 不新增后端 schema；站点使用脱敏、只读的 `BrandAwarenessBrief` 投影。其最小字段为：

```yaml
case_id: string
track: product_performance | brand_voice_social | campaign_awareness_benchmark | counterexample_hold
intent: brand_awareness_only | community_participation | product_launch | cause_awareness
subject: creator_or_brand, market, language, audience_context
source_register: locator, source_kind, what_it_proves, precision, rights_scope, digest_or_unknown
observation_window: platform, posted_at, start, end, timezone, capture_at
metrics: name, value, state, denominator, paid_or_organic, capture_at, source_ref
content_beats: hook, tension, intervention, proof_or_experience, result, cta
primary_mechanism: one mechanism only
invariant_elements: list
replaceable_surfaces: list
prohibited_surfaces: list
social_resonance: parent_tension, recognition_signal, emotional_payoff, participation_cue
claim_register: claim, source_ref, disposition
rights_safety: source_use, music_rights, guardian_consent, likeness_scope, exposure_risk
commercial_disclosure: organic | paid | boosted_ugc | unknown
media_state: metadata_only | external_link | internal_review | rights_cleared_embed | blocked
status: proceed_with_limits | ready_for_next_gate | hold_rights | blocked | counterexample
next_action: revise | collect_evidence | test | hold | stop
proof_level: local | reported | measured
limitations: list
```

`campaign_awareness_benchmark` 是有意的 benchmark-specific contract：它保留 `campaign_design`、`metrics`、`benchmark_use`、`claim_register`、`commercial_disclosure`、`media_state` 和 `rights_safety_boundary`，并将 `primary_mechanism` 标为 `not_applicable`、`mechanism_scope=benchmark_design_not_replication`。`content_beats`、`social_resonance` 与产品创意字段在此轨道为 `not_applicable`，不能为了形式完整而填入仿拍机制或品牌 claim；`campaign_design` 的 category、window、market、UGC/boosted 分层和 Brand Lift 方法才是本轨道的必需观察。

### 7.1 SocialResonanceMap（P1-001）

`SocialResonanceMap` 是 `BrandAwarenessBrief` 的只读脱敏子产物，专门承载“为什么可能引发身份识别或参与”的有限假设。每一条字段都必须带 `state`、`source_ref`、观察窗口和 `disposition`，并把四类内容分开：

1. `observations`：来源直接可见的内容或数字；
2. `bounded_inferences`：有范围、可证伪的创意解释；
3. `alternative_explanations`：可能造成相同表现的非内容因素；
4. `unknowns`：未采集、未报告、未授权或无法重建的部分。

评论、分享、保存、UGC、profile visits 等只能作为 social-resonance proxy。没有帖子级分母、采集方法和 paid/organic 状态时，必须保留 `not_reported` / `not_collected`，不得换成 0、情绪比例、Brand Lift 或因果结论。P1-001 的脱敏 JSON 通过案例详情下载；它不触发评论抓取、平台 connector、原片托管或发布。

## 8. Measurement Semantics

### 8.1 Organic proxy layer

可以记录 views、reach、focused view、completion、shares、saves、comments、profile visits、follows、UGC 数量和评论主题，但它们只能作为 attention/social resonance proxy。

### 8.2 Awareness measurement layer

如果后续有授权和预算，才进入 reach、impressions、frequency、VTR、Brand Recall、Familiarity、Favorability 和 Exposed-vs-Control Brand Lift。平台的 Awareness、Consideration 和 Conversion 目标必须分开记录；views 不能替代 Brand Lift。

### 8.3 Collection boundary

TikTok Research Tools 不是默认可用的商业全量抓取接口。任何外部采集方案都要先通过 credential、scope、commercial_access、quota、来源身份、权利和儿童安全 preflight；无法闭合时保持 `unavailable`，不换成假数据。

## 9. Delivery Gates and Stop Conditions

| Gate | 通过条件 | 阻断条件 |
| --- | --- | --- |
| `BV-G0 source` | 主体、平台、市场、Performance Window、source ref 可重建 | 原始主体/窗口/来源不可复现 |
| `BV-G1 performance` | 指标有来源、时间、分母和 paid/organic 状态 | 只有单一高播放数字、分母和口径未知 |
| `BV-G2 rights-child` | source-use、音乐、儿童安全和商业披露都有状态 | 未授权媒体、儿童身份暴露或音乐权利不明 |
| `BV-G3 mechanism` | 只有一个 primary mechanism，替代解释已写出 | 多机制无法拆分或把相关性写成因果 |
| `BV-G4 brand translation` | Momcozy 只出现为非卖货品牌假设，产品 claim/CTA 为空 | 出现未绑定产品 claim、销售 CTA 或医疗/安全暗示 |
| `BV-G5 site presentation` | 卡片、详情、下载、边界文案和验证均通过 | 用户会误解为授权原片、已证实爆款或商业批准 |

任何一项失败都停在 `blocked` 或 `hold_rights`，不自动进入媒体生成、投放或发布。

### 9.1 BV-GATE-001 Preflight contract

用户对“下一道”的授权只允许启动本地证据摄取和 preflight 记录；它不能替代创作者/监护人授权、音乐许可、平台 connector 权限、品牌批准或 Brand Lift 实验批准。每条记录写入 `brand-voice-gate-preflight/v1`，只保留脱敏来源引用、证据状态、范围和停止动作，不保存合同原文、凭据、cookie、儿童姓名、精确位置、私有 URL/ID/hash 或原始媒体。

记录至少包含 `gate_id`、`case_id`、`subject_ref_redacted`、当前请求的 `requested_use[]`、本轮评估范围的 `planned_use[]`、按用法的 `decision`、`request_state`、`evidence_items[]`、`rights_scope`、`music_rights`、`creator_permission`、`guardian_consent`、`likeness_scope`、`child_safety`、`commercial_disclosure`、`connector_access`、`external_action_approval`、`blockers`、`unknowns`、`conflicts`、`reviewed_at`、`next_action` 和 `proof_level`。`evidence_kind` 独立于案例的 `proof_level`：`public_source`、`policy_baseline`、`first_party_console`、`signed_authorization`、`human_review` 和 `measured` 不得互相替代。`not_requested` 只表示本轮没有启动外部动作，不表示获得批准。

每个 planned use 必须独立判断：

| Planned use | 最低证据 | 允许状态 | 未满足时 |
| --- | --- | --- | --- |
| `analysis_only` | 公开来源登记 + 观察窗口 + unknown/limitations | `proceed_with_limits` | 保持 metadata-only |
| `benchmark_reference` | 官方 benchmark 页面、报告口径、观察范围与不可转移声明 | `proceed_with_limits` | 仅展示 benchmark metadata，不复制素材或 lift 结果 |
| `adaptation_candidate` | 已抽象的非身份化机制、原创差异、儿童安全审查 | `candidate_only` / `hold_rights` | 不生成仿拍或真实儿童 likeness |
| `embed_or_rehost` | 明确的 rights-cleared embed/rehost 范围、期限、平台和撤销条款 | `rights_cleared_embed` | 不嵌入、不下载 |
| `commercial_use` | 创作者/监护人/品牌签署的商业使用范围、市场披露和品牌批准 | `awaiting_user_gate` → `ready` | 不主张商业使用 |
| `paid_amplification` | 付费放大范围、音乐商业许可、平台/广告批准和预算审批 | `awaiting_user_gate` → `ready` | 不投放、不 boost |
| `publish` | 创作者/监护人/品牌签署授权、市场披露、平台批准和发布审批 | `awaiting_user_gate` → `ready` | 不发布 |
| `connector_read` | credential、scope、commercial_access、quota、terms acceptance 和 expiry 的控制台证据 | `approved` | 不连接、不抓取 |
| `brand_lift` | account-specific setup、Exposed/Control 设计、样本和业务批准 | `approved_experiment` | 不把 benchmark lift 写成 Momcozy 结果 |

公开 TikTok policy 页面只能证明规则基线。例如 Content Suite 的视频级授权有期限、账号级授权可撤回；market-specific Branded Content policy 对婴儿产品、尿布等类别有市场/年龄限制；Commercial Content Disclosure 要求品牌/产品推广打开 disclosure。这些页面不能证明某条 ARK 内容的创作者/监护人同意、曲目许可或 Momcozy connector/实验批准。

当前 BV-002 的 preflight 状态为 `awaiting_user_gate`：公开 ARK 登记可证明摘要和 reported views，但原始帖子、监护人/创作者、音乐、分母和 connector 证据未闭合；换尿布场景继续禁止重演。当前 CB-001 的 preflight 只在 benchmark reference 范围内 closed；Nestlé 素材复用、Momcozy 独立 Brand Lift 和发布仍未批准。对应脱敏记录位于两个案例的 `data/gate-preflight.json`。

## 10. Validation Plan

### 10.1 Static validation

- `viral-video-deep-insight` Insight Brief validator 必须保持 `VALID`；
- inline JavaScript 通过 `vm.Script` 或等价语法检查；
- `git diff --check` 无空白错误；
- 所有本地 JSON 下载链接返回 HTTP 200；
- 站点不包含原始 TikTok 视频、音频、凭据、私有 ID 或 hash。

### 10.2 Browser validation

- `?view=cases&case=maternal-tiktok` 可直接定位 BV-001；
- 第三个 tab 显示正确状态和非卖货标签；
- `deep-insight.html` 和 Insight Brief 下载入口可用；
- 空媒体状态显示“无授权原片，仅展示 metadata/report”，不出现错误的 Oumomo 文案；
- 桌面和移动视口无横向溢出、无 `pageerror`；
- 访问者不会将播放量读成 Brand Lift、销售提升或发布许可。
- `baby-reaction-diaper-change` 的来源登记、Social Resonance Map、四字段和四类缺失值均可下载；`nestle-generations-of-love` 的 benchmark panel、四张设计卡和观察/限制列表均可见。
- 两个新案例的本地 JSON 返回 HTTP 200，`raw_media_hosted=false`、`connector_access=false`，且新案例目录不含视频、音频或原始儿童媒体。

### 10.3 Deployment boundary

本批默认只做本地站点验证。没有新的明确授权，不执行 Sites source helper、部署、公开 URL 更新、权限变化或生产验收。

## 11. Ticket Map

详细 ticket 在 `brand-voice-social-case-expansion-tickets.md` 及其 `docs/tickets/brand-voice-social/` 子目录；`BV-P0-001` 至 `BV-P0-004`、`BV-P1-001` 和 `BV-P1-002` 已完成本地验证，下一道 frontier 为 `BV-GATE-001`。

## 12. Deferred Work

- 第二批 candidate 的来源闭合、监护人/创作者授权和安全审查（`BV-GATE-001`）；
- Social Resonance Map 的真实评论主题编码（需授权来源，不在当前站点包内）；
- Momcozy 自有 campaign benchmark 的 paid/organic 分层、Brand Lift 设计和独立样本；
- 已授权创作者/品牌素材的 `rights_cleared_embed`；
- A0/A1 本地概念片与单变量对照；
- Exposed-vs-Control Brand Lift、品牌搜索和长期心理可得性测量；
- 任何真实 TikTok connector、发布、广告、计费、订单或生产部署。

## 13. External References

- [ARK by KOMI · record/20842](https://ark.media/record/20842)：BV-001 的第三方来源记录；不等于原始 TikTok 帖子或复用授权。
- [TikTok Research Tools](https://developers.tiktok.com/docs/en/about-research-api)：公开研究数据访问的申请、范围和合规边界。
- [TikTok Terms of Service](https://www.tiktok.com/legal/page/us/terms-of-service/en?region=us)：内容、声音和再利用权利边界。
- [TikTok Music Legality guidance](https://ads.tiktok.com/business/library/TikTok_Music_Legality.pdf)：品牌声音和商业音乐授权边界。
- [TikTok Brand Lift Studies](https://ads.tiktok.com/resources/help/article/tiktok-brand-lift-studies?lang=en)：Brand Lift 的 Exposed/Control 测量语义。
- [ARK by KOMI · record/19758](https://ark.media/record/19758)：BV-002 的公开登记来源；不等于原始 TikTok 帖子、监护人同意或复用授权。
- [TikTok for Business · Nestlé Generations of Love](https://ads.tiktok.com/business/en/inspiration/nestle-branded-mission-case-study?redirected=1)：CB-001 的官方活动 benchmark；reported lift 不等于 Momcozy 结果。
