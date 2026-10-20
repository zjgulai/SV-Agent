# Narrative Transformation Replication SOP

## Trigger

当复刻价值主要来自问题、摩擦、转折、解决和结果的叙事关系，而不是某个实验装置、感官体验或促销机制时使用。

## Preconditions

- ReferenceBundle 的来源、窗口、digest 和可复核状态明确。
- DecompositionMap 已覆盖 Hook、Pain/Tension、Intervention、Result、CTA 和 unsupported claims。
- 目标 Product Snapshot 与可用 `confirmed/locked` Facts 已确定。
- 只有一个 narrative Creative Dimension 被允许变化。

## Steps

1. 读取 `viral-reference-intake`，确认参考身份、权限和可播放性。
   - 完成标准：ReferenceBundle 的 required fields 齐全，未知项显式列出。
2. 读取 `viral-content-decomposition`，建立包含时间化叙事弧的 `DecompositionMap`。
   - 完成标准：每个 beat 有时间范围、作用、表层表达和 evidence refs。
3. 读取 `viral-pattern-abstraction`，形成 `PatternHypothesis`，分离 invariant、replaceable 和 prohibited surface。
   - 完成标准：可以用一句话说明“要迁移的机制”，且不包含原始台词复制。
4. 读取 `viral-narrative-transformation`，形成可修订的 `ReplicationPlan`。
   - 完成标准：计划只选择一个 narrative Creative Dimension，列出 Control/Variant 意图、冻结字段和候选 target substitutions；它还不是执行合同。
5. 读取 `viral-fact-mapping`，将所有可见/可听商品声明映射到同一 Snapshot 的 Fact。
   - 完成标准：形成 `FactMap`；unsupported claim=0，excluded fact occurrence=0。
6. 用 `viral-replication-contract` 将计划、FactMap 和执行配置冻结为不可变 `ReplicationContract`。
   - 完成标准：canonical config diff 只有一个主变量，合同 digest 可重算；冻结后不得由 provider 或 UI 改写。
7. 在不可变合同下把 narrative plan 编译为 `AdaptationPackage`。
   - 完成标准：目标商品场景、节奏、CTA、surface substitutions 和 prohibited copy 可复核，商品主张不从参考视频继承；该 package 通过本地 machine schema 验证，但不产生 PostgreSQL/runtime persistence。
8. 用 `factframe-script-storyboard` 依次编译 ScriptVersion、StoryboardVersion。
   - 完成标准：Pattern、时长、shot role 和 server-owned copy 全部受不可变合同约束。
9. 用 `viral-media-integrity` 建立 `MediaIntegrityRecord`。
   - 完成标准：在 preflight 明确 artifact-dependent pending state；在 artifact review 分别闭合溯源、技术、声画 claim、目标身份、来源使用范围和原创差异，不把任何单项升级为授权或发布许可。
10. 用 `viral-experiment-evaluation` 记录执行、Artifact、Ledger 和 `ReplicationFinding`。
   - 完成标准：终态、hash、账务、评分和限制可以逐项回溯。
11. 用 `factframe-readiness` 声明 proof level。
   - 完成标准：local、CI、deployment、live 和 production claim 分开写明。

## Stop conditions

- 参考内容不可复核或权限未知。
- 主机制与 proof/experience/conversion 无法分离。
- 目标 Facts 不足以支持结果或功效声明。
- Control/Variant 存在第二个未声明变量。
- 生成结果把参考台词、品牌元素或未授权表层直接复制。
- `MediaIntegrityRecord` 的任一必需 gate 不可复核、source-use evidence 超过 planned use，或把 preflight/QA/模型判断写成权利、商业、平台或发布结论。

## Outputs

ReferenceBundle、DecompositionMap、PatternHypothesis、ReplicationPlan、FactMap、不可变 ReplicationContract、narrative AdaptationPackage、ScriptVersion、StoryboardVersion、`MediaIntegrityRecord`、QA/validation findings 和 bounded ReplicationFinding。它们不代表 render、publish、rights、commercial 或 production approval。
