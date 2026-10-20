# Momcozy Asset Intelligence

定义 Momcozy 商业素材如何归档、验证、比较和进入复用决策。该上下文管理本地资产证据，不把生成素材升级为商品事实。

## Language

**Brand Workspace**:
围绕一个品牌组织事实、实验洞察和素材决策的分析视角；当前首要 Brand Workspace 是 Momcozy。
_Avoid_: Tenant, product rename

**Asset Bundle**:
一个媒体文件及其 Prompt、Recipe、Provenance、QA 和 hash 的完整可追溯单元。
_Avoid_: Image folder, generated file

**Concept Group**:
围绕同一传播目的和构图意图组织的一组 Asset Bundle 候选。
_Avoid_: Batch, campaign

**Recipe**:
描述素材生成配置、比例、模型和可核算成本的结构化记录。
_Avoid_: Prompt

**Provenance**:
把素材与公开来源、参考 hash 和本地 receipt 连接起来的证据记录。
_Avoid_: Task ID, signed URL

**QA Status**:
素材在事实、产品身份、文字、技术和商业审核中的当前判定。
_Avoid_: Quality score

**Hold**:
素材通过结构验证但尚未获得逐文件品牌商业审核的状态。
_Avoid_: Approved, failed

**Commercial Approval**:
品牌负责人对特定素材的产品几何、wordmark、裁切、安全区和意外文字完成的逐文件确认。
_Avoid_: Technical validation

**Library Index**:
一个明确范围内 Asset Bundle 的可浏览索引，必须声明覆盖的批次或全库范围。
_Avoid_: Latest assets

**Aggregate Index**:
覆盖整个 Brand Workspace、能够与各批次索引和 validator 数量对账的 Library Index。
_Avoid_: Batch index

**Private Gate**:
在受信任本机对真实 Brand Workspace 的新鲜投影、固定基线和 current release 做只读一致性判断的验收边界。
_Avoid_: Publisher, repair job

**Synthetic Fixture**:
可提交、无真实媒体或私有标识，用于公开 CI 验证素材工具契约的最小资产样本。
_Avoid_: Private library snapshot

**Gate Receipt**:
Private Gate 单次运行产生的有界通过状态或稳定失败 code，只证明该时点的技术一致性。
_Avoid_: Commercial Approval, publication permission
