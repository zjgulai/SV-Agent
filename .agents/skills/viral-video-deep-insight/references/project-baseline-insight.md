# 项目级反直觉洞察基线

状态：`proceed_with_limits`

证据范围：项目 living docs、Leap 有界公开报告、KleanPal Pro 本地复刻索引、Oumomo
clean-room 报告和现有 workflow/skill contracts。本文不是平台全量研究、winner 排名、因果
实验、商业批准或 production acceptance。

## 一句话结论

这个项目真正可积累的“爆款能力”不是更快生成一条看起来像热门视频的成片，而是把一个高表现
信号拆成可追溯的主体/窗口、时间化表达、唯一创意机制、事实受约束的目标表达和可证伪的单变量
实验。换句话说，项目的护城河是**把不确定的热度翻译成可比较的决策**，而不是制造一个“爆款
按钮”。

## 故事线：三份证据如何互相纠偏

### 第一幕：Leap 让“爆款”看起来已经存在

德国瓶具清洁/暖奶器报告在 2026-08-21 至 2026-08-27 的有界窗口内显示 22 个视频、10,312
views、37 likes；Top 10 占 8,878 views（86.09%）。Top 10 反复出现三组 Creative Signals：

1. 手工繁琐到自动化的 `relief transformation`；
2. 倒计时、温度、分屏和物理类比的 `visible proof`；
3. POV、ASMR 和日常动作的 `embodied experience`。

这足以让团队提出问题，却不足以让团队宣布答案。报告没有披露采集、去重、排序、paid/organic、
账号规模、发布时间、时长、快照、模型复核和置信校准；评论/分享和 followers 还存在 0 与短横线
的口径冲突。86.09% 首先是一个**集中度观察**，不是某个机制贡献了 86.09% 的因果证明。

### 第二幕：KleanPal 让“可拆解机制”看起来像“已验证爆款”

本地 KleanPal Pro 案例完整保留了 Reference → DecompositionMap → PatternHypothesis →
Product Facts → Storyboard → Media QA → 有界 TikTok 核验链。参考片约 28 秒，被拆为
`experience-pov`：生活任务进入 → 产品作为一段动作 → 继续生活并收尾。Proof、明确 CTA 和
帖级 TikTok 热度没有被观察到。

它证明的是：项目能够在有界范围内描述机制，并把人物、音乐、构图和未证实功效列为需要替换或
禁止的表层。它没有证明：原帖身份、热度、源素材权利、目标成片可发布，或体验表达会带来转化。
因此案例仍然是“本地筛查、热度未获证、不得声称爆款”。

### 第三幕：Oumomo 让“技术成功”与“内容成功”分家

Oumomo clean-room 实验多次显示，Job/媒体技术链路可以成功，但模型仍会扩写无依据功效、包装、
比较、价格、单位和 ASR 文案；R-B01 的媒体导出和 hash 技术链路闭环，内容事实却失败。这个
反例把项目的关键工程选择解释清楚：server-side Fact allow-list、excluded deny-set、append-only
版本、终态/ledger 对账、Media Integrity 六门和 proof-level 分层，比“再调一个 prompt”更有价值。

### 故事的反转

三份材料合起来的反直觉结论是：**越急着给出“为什么爆”，越可能跳过最有价值的验证工作。**
先修复主体、窗口、口径、事实和合同，再解释创意；否则得到的只是漂亮的事后叙事。

## 当前项目的关键判断

### 1. 不是缺少更多“爆款样本”，而是缺少可比的分母与 subject binding

当前最容易浪费成本的动作，是把账号级总量、播放列表卡片、品牌报告排名和不同 Product
Snapshot 放在一张排行榜里。项目已有 `Performance Subject Binding` 和 Decision Brief 设计，
但 reviewed package reader、canonical identity 和 runtime Insight Hub 尚未完成。因此当前安全
动作是输出 source-scoped hypothesis，不能自动生成“Momcozy winner”。

### 2. 内容的传播假设更像“价值翻译链”，不是“功能卖点链”

Leap 的三组信号可以组成一个待测的翻译链：

```text
先让日常摩擦可识别
  → 再让结果或现象可见
  → 最后让轻松/代入感可体验
```

这可能降低观众把产品功能翻译成个人价值的认知成本；但它仍是 `Inference`，必须排除账号、
分发、时间、音乐、人物和平台语境等替代解释。它不等于“自动化导致播放”“POV 提升留存”或
“ASMR 带来转化”。

### 3. “没有 Proof/CTA”本身是有价值的发现

KleanPal 的参考分解中 Proof 和 CTA `not_present`。这不是拆解失败，而是提示：不是每条高表现
候选都要被强行改造成证明型广告或转化型广告。当前 routing tree 允许 `experience-pov`，并把
CTA/趋势等次级元素冻结。强行补卖点可能扩大 unsupported claim surface，反而破坏待测机制。

### 4. 项目交付的成功指标应从“播放量”移到“学习闭环”

在没有稳定外部表现包与因果设计前，建议优先观察：

- `reference_stability`：来源、digest、窗口和帖级身份闭合率；
- `subject_binding_quality`：`exact_snapshot`、`reviewed_snapshot_selection`、
  `reviewed_family_context`、`unresolved`、`conflict` 的分布；
- `claim_closure`：可见/可听表面中绑定到同一 Snapshot 的 confirmed/locked Fact 比例；
- `single_variable_integrity`：Control/Variant 未批准差异数；
- `evidence_recovery`：unknown 转为可复核观察所需的最小动作；
- `test_learning`：每轮实验产生的 bounded finding、稳定 blocker 与下一步，而非单次播放峰值。

这些是系统能力指标，不是对外的增长 KPI，也不替代业务目标。

## 反直觉审计清单（本项目优先级）

| 优先级 | 容易写错的句子 | 应改成 |
|---|---|---|
| P0 | “Top 10 占 86%，所以 relief 是爆点。” | “Top 10 在该报告窗口内集中；relief 是待测 Creative Signal，分发/排序解释未排除。” |
| P0 | “KleanPal 复刻成功，说明原片是爆款。” | “机制和本地工件链可被描述；帖级热度、权利和发布未闭合。” |
| P0 | “视频生成成功，产品能力被证明。” | “技术/任务终态与事实、身份、权利、商业和发布门分别记录。” |
| P1 | “有 CTA，所以是 conversion。” | “CTA 是否决定主要表达需按 routing tree 判断；否则只作为冻结表层。” |
| P1 | “有热门音频，所以是 trend-native。” | “只有趋势决定主要表达且 TrendAdmissionRecord 完整时才路由 trend-native。” |
| P1 | “温度画面证明精准控温/杀菌。” | “记录可见现象与允许结论；功效必须回到 Product Fact。” |
| P1 | “短横线等于 0 互动。” | “保留 source_ambiguous/not_reported/observed value 的原始语义。” |
| P2 | “技术 QA 和 Private Gate 都过了，可以发布。” | “它们只证明各自的技术层；rights、commercial、platform、publish 和 production 是独立门。” |

## 最小可执行路线

1. **准入**：建立有 digest 的 `ReferenceBundle`、Performance Window 和 Subject Binding；若原帖
   身份不可立，输出 `blocked` 或 source-scoped `proceed_with_limits`。
2. **拆解**：建立时间化 `DecompositionMap`，逐项记录 Hook/Pain/Intervention/Proof/Experience/
   Result/CTA、visual/audio/text、claim candidates 与 availability。
3. **抽象**：选择一个 primary mechanism，写 invariant/replaceable/prohibited/unknown；不把
   排名或 AI summary 当机制证据。
4. **事实编译**：对目标所有可见/可听表面运行 `viral-fact-mapping`；同 Snapshot 的
   `confirmed/locked` 才能支撑声明，excluded deny-set 必须不复活。
5. **实验合同**：只改一个 `changed_creative_dimension`，冻结平台、市场、时长、事实、素材、
   声音、预算和权利范围；保存 digest 和停止条件。
6. **完整性与复盘**：按六道 Media Integrity gate、终态/ledger/artifact、四证据平面输出
   `Finding`；将结果写成 `revise/collect_evidence/test/hold/stop`。
7. **准备度**：用 `factframe-readiness` 分开 local、CI、private、deployment、live、production；
   不把任何低层级证据升级成发布承诺。

## 对产品/方法论的含义

- 新 skill 应作为 cross-cutting analysis layer，编排现有窄 skill，而不是新增第七类 primary
  mechanism 或一个万能 Insight endpoint。
- 首个可靠输出应是 compare-bound、read-only 的 Insight Brief；外部 Performance package 必须
  经过 reviewed digest、scope 和 lifecycle gate。
- 当前不应顺手增加账号、billing、ranking、video generation、social publishing 或自动 Product
  Fact promotion；这些都需要新的设计批准和独立 gate。
- 洞察工作的价值不是把未知抹掉，而是把未知变成一个有成本、有顺序、有停止条件的下一步。

## 当前基线结论

`proceed_with_limits`：项目已经拥有足以构建“爆款视频深度洞察”的方法论、证据边界和复刻
workflow；现有材料支持有界 Creative Signal 和机制假设，不支持普遍爆款、因果提升、权利、
商业、平台或 production 结论。下一步应使用本 skill 生成 brief，并按单变量合同进入受控验证。
