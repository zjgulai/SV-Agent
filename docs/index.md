# Project Documentation

本页是项目文档入口。读取顺序按任务选择，不要求每次重读全部历史设计。

## Current system

- [Project layout](architecture/project-layout.md)：Agent 项目目录、CRAFT 语义映射、入口和不可破坏的边界。
- [SV-Agent project layout proposal](architecture/sv-agent-project-layout-proposal.md)：结合当前 vertical slice 与参考仓库方法形成的目录整理顺序、迁移 tickets、冲突边界和回滚方案。
- [System architecture](architecture/system-overview.md)：当前运行组件、事实边界、数据流和未来门禁。
- [Capability model](product/capability-model.md)：从商品事实到实验、素材和决策的综合能力图谱。
- [Momcozy insight storyline](product/momcozy-insight-storyline.md)：主品牌洞察如何由数据和证据逐层形成。
- [Capability comparison](product/capability-comparison.md)：FactFrame、Oumomo、Momcozy 和已取证 Leap 报告的能力对比。
- [Creative Comparison Lab design](product/creative-comparison-lab-design.md)：Variant C 的 production Interface、只读 Projection、门禁、测试与分阶段实施方案。
- [Insight & Performance Decision Brief design](product/insight-performance-projection-design.md)：选定的 compare-bound 洞察形态、主体绑定、缺失值、离线审核包、权限与回滚方案。
- [Project skill system](product/project-skill-system.md)：从能力图谱蒸馏出的项目级 workflow、SOP、skills 路由、目标与 TODO。
- [Viral replication execution](product/viral-replication-execution.md)：方案 A 的 workflow packs、skill 责任矩阵、ticket 和当前执行台账。
- [Viral replication graph consistency](product/viral-replication-graph-consistency.md)：VR-GRAPH-001 的旧 graph、文件集、ignore 和执行入口一致性审计。
- [SV-Agent Native Agent specification](product/sv-agent-native-agent-spec.md)：爆款复刻 Native Agent 的产品边界、模块、artifact chain、状态机、工具与审批契约。
- [SV-Agent implementation tickets](product/sv-agent-implementation-tickets.md)：SV-Agent 分阶段依赖、验收标准、批准门与当前 SV-104A/B、SV-105、SV-201 至 SV-204 本地实现状态。
- [SV-Agent UI/UX Taste audit](product/sv-agent-ui-ux-taste-audit.md)：基于真实浏览器三档视口与 Taste App Screen 规则的现状审计、Framed Sheet 方向、优先级和分批验收标准。
- [Roadmap](product/roadmap.md)：已实现能力、当前 gap、批准门和推荐顺序。
- [Development and testing](development/testing.md)：本地、CI、证据链和图谱验证方式。

## Domain language and decisions

- [Context map](../CONTEXT-MAP.md)：四个领域上下文及其关系。
- [ADRs](adr/)：难以逆转且存在真实取舍的系统决策。
- [Public synthetic CI / private asset validation boundary](adr/0006-separate-public-synthetic-ci-from-private-asset-validation.md)：真实素材不进入公开 runner 的长期安全决策。
- [SV-Agent Task runtime and authorization decision](adr/0007-sv-agent-task-runtime-and-authorization.md)：已接受的 Task/Run、Human Approval、actor、迁移、回滚与恢复边界；SV-101 领域内核、SV-102 本地持久化/事实回放、SV-103 内部只读工具审计、SV-104A/B 纯规划/评估契约、SV-105 纯独立审查、SV-201 只读 Task Inbox、SV-202 浏览器本地 New Task brief、SV-203 只读 Mission Control 与 SV-204 只读 Evidence and Artifact workspace 已实现，持久化执行、公开写入与授权运行时仍关闭。
- [Implemented decisions](decisions/)：P0/P1/P2 已实施合同与回归边界，保留原日期。

## Research and evidence

- [Oumomo evidence index](research/oumomo/evidence-index.md)：研究设计、长期知识、机器台账和报告入口。
- [LeapAI public report evidence](research/leap/public-report-evidence.md)：2026-08-21 至 2026-08-27 Momcozy 德国跨平台表现、Top 10 内容方向、方法限制和 FactFrame 映射。
- [SV-Agent video model selection](research/sv-agent-video-model-selection.md)：Magpie 本地 TokenHub/VOD 安全清点、视频模型场景路由、成本与合规边界、Provider 适配方案和付费 smoke gate。
- `outputs/oumomo-reverse-engineering/`：原始 ledger、hash、scorecard、SOP、报告和媒体证据。
- `outputs/momcozy-content-assets/`：本地 ignored 商业素材库；gitignored 不等于可删除。
- `outputs/kleanpal-pro-replication/2026-10-04-us-white/`：首个端到端病毒机制复刻案例（本地 ignored 研究产物，入口为其 `CASE-INDEX.md`）；本地筛查研究，不构成权利、商业、平台或发布结论，热度未获证实，不得声称爆款。

## Reports and presentations

- [Momcozy × FactFrame 综合能力融合方案](reports/momcozy-capability-fusion.html)：能力融合方案的单页展示。
- [Viral replication plan](reports/viral-replication-plan.html)：爆款复刻方法与执行界面的历史展示页；执行权威仍以 living docs、tickets、Skills 和测试为准。
- KleanPal Pro 复刻案例简报（本地 ignored）：`outputs/kleanpal-pro-replication/2026-10-04-us-white/report/kleanpal-case-brief.html`。

## Historical material

- [Implementation plans](archive/implementation-plans/)：已执行或被门禁停止的历史计划，不代表当前 TODO。
- [2026-09-23 Scheme A methodology bundle](archive/methodology-bundles/2026-09-23-scheme-a/)：保留原内部相对链接的历史方法包，不代表当前运行能力。

## Authority order

发生冲突时按以下顺序判断：

1. 源码、PostgreSQL schema/migration 与自动化测试；
2. current architecture/product docs 与 ADR；
3. 已实施 decision contracts；
4. 带日期和证据等级的 research findings；
5. archived implementation plans。

`.ua/knowledge-graph.json` 只提供导航。它不能覆盖以上事实源，也不能把旧文档中的声明升级为当前能力。
`reports/viral-replication-plan.html` 是方案展示文档；执行权威仍以本页、living docs、skills 和测试为准。
