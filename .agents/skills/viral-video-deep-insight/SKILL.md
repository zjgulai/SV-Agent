---
name: viral-video-deep-insight
description: "对有界高表现视频候选进行跨证据、反直觉的深度洞察：把表现观察、时间化内容分解、创意机制、商品事实、实验可迁移性和证据边界编译成咨询式 Insight Brief；适用于回答为什么可能有效、哪些部分可复用以及下一步如何验证，不替代素材准入、单一机制复刻合同、媒体生成或发布验收。"
---

# 爆款视频深度洞察

这个 skill 的产品化名称是“爆款视频深度洞察”，canonical slug 是
`viral-video-deep-insight`。它把项目已有的 Performance、Viral Replication、Product
Truth、Experiment、Asset 和 Readiness 边界组织成一条可复核的洞察故事线。

## 何时使用

当用户要回答以下问题时使用：

- 某个视频或候选集合在指定平台、市场和时间窗内表现突出，为什么“可能”有效？
- 哪些是可观察的创意机制，哪些只是账号、分发、趋势、样本或测量口径造成的表象？
- 如何把洞察转成一个事实受约束、单变量、可复盘的下一轮测试？
- 如何用专业咨询报告的方式同时呈现结论、反证、未知项、行动和护栏？

不要用它替代以下窄 skill：

- 参考来源和权限准入：`viral-reference-intake`；
- 时间线/声画拆解：`viral-content-decomposition`；
- 机制抽象或主机制路由：`viral-pattern-abstraction` 与 Viral Replication routing tree；
- 商品事实、脚本、分镜、媒体完整性、实验执行或 readiness gate：对应 `factframe-*`、
  `viral-fact-mapping`、`viral-media-integrity`、`viral-experiment-evaluation`。

## 先读的项目权威

按需读取，避免用旧报告或图谱替代真实事实：

1. `docs/index.md`；
2. `docs/contexts/content-performance-intelligence/CONTEXT.md` 与
   `docs/contexts/viral-replication/CONTEXT.md`；
3. `docs/product/momcozy-insight-storyline.md`、
   `docs/product/capability-model.md` 与
   `docs/product/insight-performance-projection-design.md`；
4. `docs/product/viral-replication-execution.md`、
   `.agents/workflows/viral-replication/routing-decision-tree.md`、
   `shared-artifact-contracts.md`、`shared-scorecard.md`；
5. 本 skill 的 [深度洞察框架](references/deep-insight-framework.md)；需要交付报告时再读
   [输出模板](references/output-template.md)。

若任务涉及具体参考片，先完成 `ReferenceBundle`、`DecompositionMap` 和
`PatternHypothesis`；本 skill 编排这些 artifact，不用模型摘要或排名替代它们。

## 输入与输出

输入至少包括：

- 明确的 `decision_question`；
- `subject`（brand、market、product family、model、variant）与 `Performance Window`；
- 有 source locator、digest、capture time、availability、rights scope 的
  `ReferenceBundle` 或等价证据；
- 性能观察的原始口径（指标层使用 `state=observed` 加数值 0 表示 observed zero，另行区分
  `not reported`、`not collected`、`source ambiguous` 等状态；`unavailable` 仅用于 section/gate）；
- 时间化 `DecompositionMap`，以及一个或明确阻断的 `primary_mechanism`；
- 若要讨论商品表达，提供同一 Product Snapshot 的 Fact 状态、selected/excluded deny-set；
- 若要提出复刻动作，提供 Control、Variant、唯一 `changed_creative_dimension` 的合同草案。

输出为一份 evidence-scoped `Insight Brief`，至少包含（`evidence_level=Fact|Inference|Unknown`
与 `proof_level=local|CI|private|deployment|live|production` 分开）：

`Question → Scope/Subject/Window → Observed → Tension/Counter-intuition →
Mechanism hypothesis → Transferability → Product/rights/integrity guardrails →
Smallest test → Action → Proof level/limitations`。

洞察状态只使用 `blocked`、`proceed_with_limits` 或 `ready_for_next_gate`；行动只使用
`revise`、`collect_evidence`、`test`、`hold` 或 `stop`。Decision Brief 的 `ship` 不得
被偷偷加入为本 skill 的结论。

## 执行规则

1. 先写清楚要支持的决定和不支持的决定。将“爆款”解释为有界 `Viral Candidate` 或
   `Performance Observation`，除非有独立门禁，否则不写 winner、causal lift、保证或通用公式。
2. 先审计分母和主体：平台、市场、语言、账号规模、paid/organic、发布时间、时长、样本、
   收集/去重/排序方法和快照时间。缺失数据保持缺失；零不是缺失。
3. 按时间顺序重建 Hook、Pain/Tension、Intervention、Proof、Experience、Result、CTA
   和 visual/audio/text grammar。每个结论都要有 source ref 和 availability state。
4. 用框架中的维度矩阵写出“观察 → 解释 → 替代解释 → 可证伪测试”，而不是把播放量直接归因
   给 Hook、ASMR、趋势或卖点。
5. 从六类 primary mechanism 中只选一个；无法把两个机制拆成一个可观察的 Creative
   Dimension 时输出 `blocked: primary_mechanism_ambiguous`，要求拆 Variant。
6. 将参考表达与目标商品分开。每个 voiceover、caption、OCR、画面、title、tag、CTA 和
   promotion claim 都要回到同一 Snapshot 的 `confirmed`/`locked` Fact；Reported Product
   Claim、模型建议和物理类比不能直接升级为 Product Fact。
7. 只把可迁移的功能写进 `invariant_elements`；把人物、台词、音乐、品牌表层、模板身份、
   未授权素材写入 `replaceable`、`prohibited` 或 `unknown`。技术 QA、模型相似度、Private
   Gate 或可播放性不能替代权利、原创、商业、平台或发布批准。
8. 若提出实验，冻结所有非目标字段，只允许一个 `changed_creative_dimension`，保存
   contract/config digest、停止条件、结果口径和重复计划。n=1 只报告一次观察。
9. 最后用模板编译固定顺序的 Insight Brief；私有模型推理不写入交付，只保留输入、typed
   outputs、findings、source refs、digest 和事实执行状态。

## 停止条件

- subject、window、source identity、digest 或可复现性无法闭合；
- 高播放/排名/集中度没有分母、快照或方法，用户却要求宣称“爆款原因”；
- 品牌、类别或标题相似被当作 Product Family/Model/Variant binding；
- 0、not reported、not collected、source ambiguous 或 unavailable 被混写；
- 时间线/主机制无法观察，或同时改变多个机制、时长、平台、事实或素材；
- unsupported、excluded、expired Promotion 或 AI 生成卖点进入目标表达；
- 权利、来源使用范围、目标身份连续性或原创差异未闭合，却要求媒体/发布结论；
- 请求要求 winner、causal、universal、commercial、deployment、live 或 production 结论，
  但没有对应独立 gate。

## 完成标准

第二位审阅者应能从 brief 重建：我们观察了谁和哪段窗口、直接证据是什么、哪一个主机制只是
假设、至少一个替代解释是什么、什么不可迁移、最小测试只改变什么、哪些事实/权利/媒体门仍
未通过，以及当前行动和 proof level。只有主体关系已审核、未处置的 unsupported/excluded claim
为零、媒体 gate 没有 `blocked/unavailable` 且满足下一道明确门时才可返回 `ready_for_next_gate`；否则
保留 `proceed_with_limits` 或稳定 blocker。

## 验证

运行本目录的确定性校验与 fixture 测试：

```bash
rtk run python3 .agents/skills/viral-video-deep-insight/scripts/validate_insight_brief.py .agents/skills/viral-video-deep-insight/tests/fixtures/valid-brief.json
rtk run python3 .agents/skills/viral-video-deep-insight/scripts/validate_insight_brief.py .agents/skills/viral-video-deep-insight/tests/fixtures/blocked-ranking-trap.json
rtk run python3 -m unittest discover -s .agents/skills/viral-video-deep-insight/tests -v
```

若当前 Agent runtime 安装了 `skill-creator`，再使用该 runtime 提供的 `quick_validate.py`
对本 skill 目录做结构校验；不要在项目文档中写死个人安装路径。

校验通过只证明 skill 的结构、字段契约和合成边界测试通过，不证明真实平台热度、媒体生成、
权利、部署或 production acceptance。
