# Media Integrity Gate SOP

## Trigger

在任一 primary replication workflow 已冻结 `ReplicationContract`、完成 fact-bound Script/Storyboard preflight 后使用；若存在受控或有证据授权的本地 Artifact，可进入 `artifact_review`。它是跨机制质量/权利/原创门，不是新的 `Primary Replication Mechanism`、Creative Dimension、RenderJob 或发布 workflow。

## Preconditions

- ReferenceBundle、DecompositionMap、PatternHypothesis、ReplicationContract、target Snapshot、ordered selected/excluded Facts、Pattern、duration、language、market、platform、model、target assets、source-use plan、rights 与预算可复核且没有未经批准的 Control/Variant drift。
- `mode=preflight`：有 frozen acceptance criteria、target substitutions、source identity exclusions、source-use evidence 与 explicit pending Artifact state。
- `mode=artifact_review`：有 artifact identity/hash/config or contract digest、safe bounded provenance、terminal state、受控/授权的 review path 和所需技术/ASR/OCR/frame/identity evidence 或 human fallback plan。
- 任何 target Product Claim 都有同 Snapshot 的 `confirmed`/`locked` Fact；Promotion 仍独立、时间有效且只在既有 server-owned CTA rule 内处理。
- 资产证据若来自 Momcozy Bundle/Index/Private Gate，只按其真实层级使用：Bundle 结构、Aggregate Index projection、Private Gate receipt 与 Commercial Approval 分开；不暴露私有资产内容、路径、ID、hash、receipt 或凭据。

## Steps

1. 用 `viral-replication-contract` 复核冻结合同与 isolation report。
   - 完成标准：single changed Creative Dimension、contract digest 和所有冻结字段可重建；否则先 `blocked`。
2. 选择 `preflight` 或 `artifact_review`，建立 `MediaIntegrityRecord`。
   - 完成标准：每个 gate 已获得证据或 explicit pending/unavailable state；没有伪造 Artifact 或工具输出。
3. 用 `viral-media-integrity` 逐一审计六个互斥 gate：artifact traceability、technical profile、communicative surface、target identity continuity、source use scope、originality delta。
   - 完成标准：每个 gate 都有 source/tool/human fallback、状态、unknowns 与 stable blocker；相邻 gate 不相互借用通过结论。
4. 用 `viral-fact-mapping` 审计可见与可听的所有 claim。
   - 完成标准：voiceover、caption、OCR、包装、价格、title、tag、action、acceptance copy 与 promotion 全部有明确 Fact disposition；unsupported/excluded occurrence=0。
5. 对技术、文字/声音与 identity gate 使用受控工具或有范围的独立 human fallback。
   - 完成标准：technical profile 与 frozen contract 匹配；ASR/OCR/人工核对的范围已写明；商品身份与跨镜头连续性不含 unresolved drift。
6. 对 source-use 和 originality gate 执行独立证据审计。
   - 完成标准：每项 planned use 的 evidence state 与用途匹配；target substitutions、source identity exclusions、comparison method、independent review state 完整。它们不等于法律意见、商业批准或平台许可。
7. 用 `viral-experiment-evaluation` 汇总 Artifact、Ledger、Scorecard 和 Finding。
   - 完成标准：finding 分开写 observations、bounded inferences、unknowns、limitations、stable blockers 与 `revise`/`collect_evidence`/`test`/`hold`/`stop` next action。
8. 用 `factframe-readiness` 标示 proof level。
   - 完成标准：preflight、local artifact review、Synthetic CI、Private Gate、commercial approval、deployment、live、platform verification 与 production acceptance 分别报告。

## Stop conditions

- 没有可重建的 frozen contract、artifact/provenance state、Fact mapping 或 target identity requirements。
- 将 pending Artifact、工具 unavailable、人工未复核、Asset Bundle 成功、Aggregate Index 状态、Private Gate receipt、QA disposition 或 model similarity 当作另一 gate 的通过。
- 出现 unsupported/excluded claim、cross-Snapshot Fact、失效 Promotion、可见/可听 source surface 复活、身份不连续、hash/digest 不一致或 terminal state 未闭合。
- planned use 超出 reference/target 的 analysis、adaptation、reuse、embedding、redistribution、commercial 或 publishing evidence state。
- 以模型单独审阅、单一相似度分数、可播放、可访问或看起来不同作为原创/合法/商业/平台/发布批准。
- 请求实际渲染、账号、billing、趋势 API、平台验证、上传、发布或 production acceptance；这些需单独批准的 runtime/外部 gate。

## Outputs

`MediaIntegrityRecord`、Artifact traceability/technical/ASR/OCR/identity observations 或 human fallback、full-surface claim map、source-use evidence matrix、originality-delta review、scorecard、bounded `ReplicationFinding` 与 proof-level report。`preflight` 输出只证明本地验收计划可继续；`artifact_review` 输出只证明有范围的本地审计状态；二者均不自动证明授权、原创批准、商业批准、平台兼容、发布或 production acceptance。
