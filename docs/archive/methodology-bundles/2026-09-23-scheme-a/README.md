# 方案 A：爆款复刻方法论交付包

生成日期：2026-09-23
交付性质：当前项目工作区的可阅读、可复用方法论快照；包含 SOP、Skill、工作流、公开夹具与前向测试案例。

## 先从这里开始

1. 打开 `viral-replication-plan.html`，了解方案 A 的 MECE 类型、端到端框架和交付结构。
2. 阅读 `docs/product/viral-replication-execution.md`，确认七类机制、共享原子 Skill、类型专属 Skill、ticket 和证明边界。
3. 进入 `.agents/workflows/viral-replication/routing-decision-tree.md`，为一个 Reference 选择唯一的 Primary Replication Mechanism。
4. 仅执行被选中机制目录中的 `SOP.md` 与 `skill-map.md`。跨工作流只能通过明确的 artifact handoff，不能复用未审计的模型输出。
5. 以 `fixtures/` 的 fail-closed 对抗样本和 `forward-tests/` 的独立案例检查输入、输出、停止条件与结论边界。

## 目录说明

| 目录 | 内容 | 用途 |
| --- | --- | --- |
| `viral-replication-plan.html` | 方案 A HTML 总览 | 以可视化方式浏览整体框架与执行 TODO。 |
| `docs/product/` 与 `docs/contexts/viral-replication/` | 方案 A 执行台账、项目级 Skill 系统、Viral Replication 领域上下文 | 理解 MECE 划分、机制原理、权威来源、输入输出与证明边界。 |
| `.agents/skills/viral-*/` | 13 个 `viral-*` Skill 的完整包 | Reference intake、分解、模式抽象、合同冻结、事实映射、机制迁移、媒体门和实验评估。 |
| `.agents/skills/factframe-*/` | workflow 实际复用的 `factframe-*` Skill 完整包 | 商品事实、脚本分镜、可靠执行、比较/证据、资产、readiness 与跨上下文路由。 |
| `.agents/workflows/viral-replication/` | 七个 workflow pack、路由树、共享契约、公开 fixtures 和 forward tests | 根据内容机制执行具体 SOP，并用案例验证边界。 |

## 七类 MECE 复刻机制

1. `01-narrative-transformation`：问题—转折—解决—结果的叙事结构迁移。
2. `02-proof-demonstration`：实验、对比、量化或物理演示的证明结构迁移。
3. `03-experience-pov`：POV、ASMR、感官与动作连续性的体验结构迁移。
4. `04-attention-grammar`：Hook、镜头节奏、信息揭示、字幕节拍、反差和声音时序迁移。
5. `05-conversion-action`：决策异议、Promotion Fact、CTA invitation 和受限 action-path 的转化结构迁移。
6. `06-trend-native`：有界趋势信号、共享语境、挑战/模板结构或音频功能的单组件迁移。
7. `07-media-integrity`：在主机制合同冻结后，独立审计 artifact、技术、声画表达、目标身份、来源使用范围与原创差异。

主机制必须唯一；`07-media-integrity` 是跨机制质量门，不是第八个可替代主机制。任何单项门通过都不替代事实、权利、原创、商业批准、平台能力、账号、上传、发布、live 或 production acceptance。

## 包含的案例与验证材料

- `fixtures/`：无私有数据的 adversarial fixtures。用于检验来源不稳、测量语义、事实声明、单变量漂移、权利未知，以及注意力、转化、趋势、媒体完整性等相邻边界时是否 fail closed。
- `forward-tests/`：五组独立前向测试，覆盖 proof demonstration、attention grammar、conversion action、trend native 与 media integrity 的输入、预期处置、首次 blocker、修正与复测结果。
- `shared-artifact-contracts.md` 和 `shared-scorecard.md`：跨 workflow 的最小 artifact handoff 与评分口径。

## 使用与安全边界

- 本包只包含文档、Skill、SOP、公开 synthetic fixture 与测试案例；不包含真实参考媒体、商业素材、账号、cookie、凭据、产品私有数据或运行输出。
- 公开 fixture / forward test 证明的是路由、artifact contract、claim boundary 和 stop condition；它们不证明真实视频生成、平台热度、播放表现、权利许可、商业批准、发布或生产验收。
- 方案展示 HTML 是总览入口；当前执行权威以本包内方法论文档、Skill 和 workflow SOP 为准。
- 每次用于新项目或新 Reference 时，应重新建立 `ReferenceBundle`、`DecompositionMap`、`PatternHypothesis` 与 `ReplicationContract`，不得将旧案例的结论直接升级为新事实。

## 打包完整性

交付前已逐项核对目录文件清单、每个复制文件的 SHA-256、压缩包完整性和敏感内容边界。ZIP 的 SHA-256 与最终文件数会在交付说明中给出。
