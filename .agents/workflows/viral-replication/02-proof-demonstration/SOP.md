# Proof Demonstration Replication SOP

## Trigger

当复刻价值主要来自可观察的实验、对比、倒计时、温度、物理类比或前后变化时使用。

## Preconditions

- 参考视频的 proof device 和实际观察现象可以分开记录。
- 目标商品的每个功效主张都有同一 Snapshot 的 confirmed/locked Fact 或被明确禁止。
- 演示不会把物理现象自动升级成杀菌、保温、精准控温、耐用等商品结论。

## Steps

1. 用 `viral-reference-intake` 建立 ReferenceBundle。
   - 完成标准：来源、digest、窗口、可播放性、权利和限制可复核。
2. 用 `viral-content-decomposition` 建立 proof-specific DecompositionMap。
   - 完成标准：记录装置、输入、操作、观察、展示方式和来源限制。
3. 用 `viral-pattern-abstraction` 形成 `PatternHypothesis`，区分 proof mechanism 与 surface demonstration。
   - 完成标准：每个 proof step 有 `observed_phenomenon` 和 `allowed_conclusion`。
4. 读取 `viral-proof-demonstration`，形成包含最小 proof protocol 的可修订 `ReplicationPlan`。
   - 完成标准：计划只选择一个 proof Creative Dimension，协议不需要参考视频中的未经证实卖点才能成立。
5. 读取 `viral-fact-mapping` 和现有 claim audit，形成 `FactMap`。
   - 完成标准：每条口播、字幕、标题和画面文字都有 Fact 状态，unsupported claim=0。
6. 用 `viral-replication-contract` 冻结不可变 ReplicationContract。
   - 完成标准：除 proof mechanism 外，商品、时长、模型、语言、素材和预算冻结；digest 与 isolation report 可重建。
7. 在不可变合同下将 proof protocol 编译为 `AdaptationPackage`。
   - 完成标准：每步的 input、operation、observed phenomenon、display surface 和 allowed conclusion 可复核；该 package 通过本地 machine schema 验证，但不产生 PostgreSQL/runtime persistence。
8. 通过 `factframe-script-storyboard` 依次编译带 proof shot role 的 ScriptVersion、StoryboardVersion。
   - 完成标准：proof shot 的 acceptance criteria 只描述可观察状态和允许结论。
9. 用 `viral-media-integrity` 运行跨机制媒体门。
   - 完成标准：`MediaIntegrityRecord` 分别记录 artifact 溯源、技术、声画 claim、目标身份、来源使用范围和原创差异；preflight 不伪造 Artifact，artifact review 不把 QA 写成许可。
10. 用 `viral-experiment-evaluation` 运行 experiment evidence reconciliation，形成 `ReplicationFinding`。
   - 完成标准：ledger 和 artifact hash 与 `MediaIntegrityRecord` 的有范围证据可复核，Finding 不把单次演示升级为效果结论。
11. 用 `factframe-readiness` 声明 proof level。
   - 完成标准：local、CI、private、deployment、live 和 production claim 分开写明。

## Stop conditions

- 观察现象与商品结论无法区分。
- proof protocol 依赖未确认的数字、单位、功效或安全性。
- 参考/目标产品 identity 不明确。
- 模型输出新增 comparison、medical、safety 或 performance claim。
- 只有 n=1 却要求 causal、universal 或 winner 结论。
- Media Integrity Gate 无法重建合同、target identity、source-use scope 或 full-surface claim review，或以模型/技术 probe 单独替代原创、权利、商业或发布判断。

## Outputs

ReferenceBundle、proof DecompositionMap、PatternHypothesis、ReplicationPlan、FactMap、不可变 ReplicationContract、proof AdaptationPackage、validated ScriptVersion、StoryboardVersion、`MediaIntegrityRecord` 和 bounded ReplicationFinding。它们不代表 render、publish、rights、commercial 或 production approval。
