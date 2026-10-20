# Context Map

本项目以 FactFrame 为平台身份，以 Momcozy 为首要品牌案例。五个领域上下文共享一条洞察故事线，但不共享事实语义或持久化权威。

## Contexts

- [Product Truth & Script](./docs/contexts/product-truth-script/CONTEXT.md)：把有证据的商品事实转化为可验证、可版本化的脚本与分镜决策。
- [Experiment Evidence](./docs/contexts/experiment-evidence/CONTEXT.md)：记录 clean-room 实验的输入、观察、成本、产物和证据强度。
- [Momcozy Asset Intelligence](./docs/contexts/momcozy-asset-intelligence/CONTEXT.md)：管理 Momcozy 本地商业素材的可追溯归档、质量状态和复用决策。
- [Content Performance Intelligence](./docs/contexts/content-performance-intelligence/CONTEXT.md)：把外部平台表现、排名和内容方向转化为带范围的 Creative Signal。
- [Viral Replication Intelligence](./docs/contexts/viral-replication/CONTEXT.md)：把有界参考内容拆成可验证创意机制，并编译成事实受约束、单变量可比较的复刻合同。

## Relationships

- **Experiment Evidence → Product Truth & Script**：实验结论可以支持能力 gap 和 roadmap，但不能直接升级为 Product Fact。
- **Content Performance Intelligence → Product Truth & Script**：Reported Product Claim 必须先通过 confirmed/locked fact 门禁；排名和 AI 摘要不能直接成为脚本声明。
- **Content Performance Intelligence → Experiment Evidence**：Creative Signal 通过 Hypothesis Reference 进入 Creative Comparison Contract；必须冻结平台、时间窗、唯一 Creative Dimension 和对照条件后再判断效果。
- **Viral Replication Intelligence → Product Truth & Script**：复刻机制只能通过当前 Product Snapshot 的 confirmed/locked Facts 重新编译为脚本声明；参考内容的台词、字幕和画面不得直接成为 Product Fact。
- **Viral Replication Intelligence → Experiment Evidence**：每次复刻必须冻结唯一 Primary Replication Mechanism、Control、Variant、配置 digest、预算和停止条件；一次高表现样本不能升级为因果结论。
- **Content Performance Intelligence → Viral Replication Intelligence**：Performance Observation 和 Creative Signal 可以形成复刻候选与 Hypothesis Reference，但排名、集中度和 AI 摘要不能直接成为 winning formula。
- **Product Truth & Script → Momcozy Asset Intelligence**：已验证脚本与 Storyboard 可以约束素材需求；它们不自动授予生成、发布或商业使用许可。
- **Momcozy Asset Intelligence → Product Truth & Script**：素材 Provenance 和 QA 可作为视觉执行证据；生成画面和模型文字不能反向成为商品事实。
- **Momcozy Asset Intelligence → Content Performance Intelligence**：只有带 Bundle ID、渠道和发布时间窗的已审核素材，才具备后续表现归因条件。
- **四者 → Decision Brief**：只读 Decision Brief 分区投影四个上下文，并要求显式 Subject Binding；它不建立万能 Evidence 对象、新事实源或跨平面原子快照。
- **四者 → Capability Graph**：图谱提供导航和关系索引，不成为新的事实源。
