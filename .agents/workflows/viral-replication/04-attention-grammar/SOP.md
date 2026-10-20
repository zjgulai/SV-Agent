# Attention Grammar Replication SOP

## Trigger

当复刻价值主要来自 Hook、信息揭示/镜头节奏、字幕节拍、视觉反差或声音时序，且这些要素可从商品卖点、实验装置、体验、促销和趋势模板中分离时使用。

## Preconditions

- ReferenceBundle 的来源、digest、时间窗、可复核状态和分析/适配权限明确。
- DecompositionMap 已用时间范围记录 Hook、视觉、字幕、声音、切点、信息揭示和未知项。
- PatternHypothesis 的唯一 `primary_mechanism` 是 `attention-grammar`。
- Control/Variant 只选择一个 attention component：`hook_trigger`、`reveal_cadence`、`caption_cadence`、`visual_contrast` 或 `sonic_timing`。
- 目标 Product Snapshot、confirmed/locked Facts、目标素材来源和声音使用范围已确定。
- 已选择一个 frozen `CompiledPatternDefinition`，其 `pattern_key/version`、duration、language、phase sequence、shot role 和 budget 可被复核。

## Steps

1. 用 `viral-reference-intake` 固定 ReferenceBundle。
   - 完成标准：来源、digest、平台、观察窗口、可播放性、权限和限制可复核。
2. 用 `viral-content-decomposition` 建立 timed attention `DecompositionMap`。
   - 完成标准：每个 attention observation 有时间范围、载体、可观察功能、surface 分类、source ref、availability state，以及现有 Pattern 的 shot/phase anchor。
3. 用 `viral-pattern-abstraction` 提取 PatternHypothesis。
   - 完成标准：机制只描述可迁移的注意力功能，不包含播放、留存、转化或 winner 因果结论。
4. 用 `viral-attention-grammar` 选择唯一 attention component 并形成可修订 `ReplicationPlan`。
   - 完成标准：selected component、可替换表层、禁止复制表层、冻结组件、target substitutions 和 Pattern anchors 完整；两位审阅者能得出同一 component。
5. 用 `viral-fact-mapping` 审计所有 target caption、voiceover、包装文字、标题和 CTA，形成 `FactMap`。
   - 完成标准：商品主张全部绑定同一 Snapshot 的 Fact，unsupported claim=0，excluded fact occurrence=0。
6. 用 `viral-replication-contract` 固定 Control/Variant，形成不可变 ReplicationContract。
   - 完成标准：canonical config diff 只包含选定 attention component；其余注意力组件、商品、时长、语言、平台、模型、素材、声音政策和预算一致，digest 可重算。
7. 在不可变合同下将 attention plan 编译为 `AdaptationPackage`。
   - 完成标准：timed observations、Pattern phase/shot anchor、surface substitutions 与 frozen components 可复核；该 package 通过本地 machine schema 验证，但不产生 PostgreSQL/runtime persistence。
8. 用 `factframe-script-storyboard` 依次编译既有 fact-bound Pattern 为 ScriptVersion、StoryboardVersion。
   - 完成标准：时长、shot budget、server-owned copy 和 Pattern Definition 受不可变合同约束；AdaptationPackage 只引用现有 phase/role。
9. 用 `viral-media-integrity` 建立 `MediaIntegrityRecord`。
   - 完成标准：surface substitution 不替代六个独立 gate；preflight 明确 pending artifact，artifact review 分开审计 claim、identity、source-use 和 originality delta。
10. 用 `viral-experiment-evaluation` 记录 Artifact、Ledger 和 `ReplicationFinding`。
   - 完成标准：Finding 分开写 observations、bounded inferences、unknowns、limitations 和 next action，且不把单次结果写为注意力因果证明。
11. 用 `factframe-readiness` 标明 proof level。
   - 完成标准：local fixture、local validation、CI、Private Gate、deployment、live 和 production 结论分别表述。

## Stop conditions

- 关键 Hook、节奏、字幕、视觉或声音 observation 不可复核，或来源只剩模型摘要。
- 主机制必须依赖热门音频、平台梗或挑战模板；此时路由到 `trend-native`。
- 主机制实际是促销/CTA、实验演示、POV/ASMR 或叙事关系。
- 复刻直接使用参考台词、音频、人物、品牌视觉、特征性镜头或未授权模板。
- Contract 同时改变两个 attention component，或同时改变时长、语言、素材、商品事实或其他 Creative Dimension。
- 任何输出将 attention grammar 解释为 retention、播放、转化、causal lift、winner 或 production proof。
- 任一 Media Integrity Gate 不能由有范围证据重建，或把表层差异、技术 QA、模型审阅或 preflight 写成版权、商业、平台或发布批准。

## Outputs

ReferenceBundle、timed attention DecompositionMap、PatternHypothesis、ReplicationPlan、FactMap、不可变 ReplicationContract、attention AdaptationPackage、fact-bound ScriptVersion、StoryboardVersion、`MediaIntegrityRecord`、Artifact/Ledger 和 bounded ReplicationFinding。它们不代表 render、publish、rights、commercial 或 production approval。
