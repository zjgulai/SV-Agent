# Viral Replication Adversarial Fixtures

这些夹具是方案 A 的 P3 证据边界测试。它们是合成输入，不包含真实账号、私有链接、原始视频、Cookie、产品数据库或平台数据。每个 JSON 都同时写明输入状态和 expected disposition，方便人工复核或由独立 agent 消费。

## 三层验证边界

1. **Fixture-shape validation**：`tools/viral_replication_oracle` 检查 JSON 可读性、fixture/case 必需字段、closed expected disposition 和 failure-code 形状。CLI 的 `fixture_schema=<count>` 只代表这一层，不是 SV-001 canonical artifact schema acceptance。
2. **Canonical artifact contract validation**：`tools/viral_replication/artifact_contracts.py` 是九类新增 artifact 的 executable machine-schema authority。只有将 fixture 映射为对应 artifact 并调用该 validator，才可声称 artifact contract validation；当前 fixture oracle 的 `schema` 计数不能替代它。
3. **Workflow expectation oracle**：oracle 从 fixture input 独立推导 disposition/blockers，再与 `expected` 对照。该层验证 workflow stop condition，不证明 canonical artifact、真实媒体、CI、平台或 production acceptance。

本地 deterministic runner：

```bash
rtk uv run --project apps/api python -m tools.viral_replication_oracle .agents/workflows/viral-replication/fixtures
```

## 消费顺序

1. 先读取 `routing-decision-tree.md` 和目标 workflow 的 `SOP.md`。
2. 将夹具中的输入映射为对应 artifact；不得把 `expected` 字段当作模型生成的事实。若报告 canonical artifact acceptance，必须另行调用 `tools/viral_replication/artifact_contracts.py` 的 validator。
3. 按 canonical skills 的 stop conditions 逐条检查，再由 workflow oracle 独立推导 disposition 与 blockers。
4. 只输出 `blocked`、`proceed_with_limits` 或 `ready_for_next_gate` 之一，并保留 blocker、evidence level、unknowns 和 next action。
5. 只有在预期 blocker 被准确指出时，fixture expectation 才算通过；不能用“看起来合理”替代字段级判断，也不能把 fixture-shape pass 写成 artifact-schema pass。

## 覆盖矩阵

| Fixture | 风险 | 必须阻断或保留的边界 |
| --- | --- | --- |
| `SV-004-six-mechanism-oracle-matrix.json` | 六机制 positive/ambiguous/blocked coverage | 只证明 synthetic route/stop-condition expectation；其 fixture shape 和抽象字段不自动满足 canonical artifact schema |
| `VR-P3-001-reference-source-unstable.json` | 参考来源不可稳定复现 | source identity、digest、playability 未闭合时不得抽取定论 |
| `VR-P3-002-measurement-semantics.json` | 0、未报告、未采集、来源歧义混淆 | 观察状态必须保持原语义，不得把 0 改写为缺失或成功 |
| `VR-P3-003-claim-deny-set.json` | unsupported claim 与 excluded Fact 复活 | claim mapping 必须 fail closed；excluded 事实永远不能支持文案 |
| `VR-P3-004-multi-variable-drift.json` | 控制组与变体多维漂移 | ReplicationContract 必须阻断 causal/winner 结论 |
| `VR-P3-005-rights-unknown.json` | 权利/授权状态未知 | 进入媒体使用或发布前必须停止 |
| `VR-P4-001-F1-attention-evidence-scope.json` | 可观察 attention grammar 被写成留存因果 | 可保留机制假设，但 retention/causal/default Pattern 结论必须停止 |
| `VR-P4-001-F2-attention-surface-copy.json` | 字幕、音频、品牌视觉等表层复制 | adaptation scope 与表层替换未闭合时必须停止 |
| `VR-P4-001-F3-attention-component-drift.json` | 多个 attention component 与时长/声音同时漂移 | 单变量合同必须停止 |
| `VR-P4-001-F4-attention-routing.json` | 热门音频/挑战模板被误路由为 attention | 必须路由至 `trend-native`，并保留权利 blocker |
| `VR-P4-001-F5-attention-availability-subject.json` | 零值、未报告、未采集与主体绑定缺失被误写成 Hook 失败 | 原始 Availability 与 subject binding 未闭合时必须停止 |
| `VR-P4-002-F1-promotion-fact-separation.json` | Promotion 被作为普通 selected/excluded Fact 或 provider context | Promotion 必须保持独立字段，provider 不得接收 |
| `VR-P4-002-F2-promotion-validity-scope.json` | 已失效限时优惠仍被渲染 | 必须以数据库时间检查有效期 |
| `VR-P4-002-F3-cta-slot-ownership.json` | generic CTA Pattern 或 provider 使用 Promotion | 只允许 `server_promotion_final_cta` 的最终 `cta` role，且 server-owned policy 不得泄漏 |
| `VR-P4-002-F4-action-path-binding.json` | 未绑定的外部 checkout/URL 被当作既有能力 | 必须标记 `not_applicable` 或进入独立能力设计 |
| `VR-P4-002-F5-incidental-cta-misrouting.json` | 仅因结尾有 CTA 而把 proof 样本误路由为 conversion | CTA 存在不等于它是主机制 |
| `VR-P4-003-F1-incidental-trend-misrouting.json` | 仅有 trend tag/背景音频却把 proof 样本误路由为趋势 | 趋势表层存在不等于 trend-native 是主机制 |
| `VR-P4-003-F2-trend-signal-scope-freshness.json` | 稳定参考被写成未验证的“当前热门” | signal identity、来源、市场/语言和观察窗必须有界 |
| `VR-P4-003-F3-audio-function-substitution.json` | 来源音频复用或近似替代被隐藏在 template 变体内 | audio function、source reuse 与 target sound policy 必须可追溯且单变量 |
| `VR-P4-003-F4-template-provenance-originality.json` | 可见模板被当作可调用资源，且无原创差异记录 | template use scope、source identity separation 和 originality handoff 必须 fail closed |
| `VR-P4-003-F5-platform-compatibility-overclaim.json` | 本地格式观察被写成平台兼容/上传/发布能力 | 只允许记录 constraints；外部兼容和发布必须独立 gate |
| `VR-P4-004-F1-artifact-traceability-profile.json` | artifact/config/contract digest 不一致，却借另一文件的 probe profile 通过 | artifact 溯源与技术规格必须分别 fail closed |
| `VR-P4-004-F2-communicative-surface-claim-audit.json` | OCR 发现 excluded claim，且关键 ASR unavailable 被忽略 | 声画表达面必须完整 fact-map 或记录有范围人工复核 |
| `VR-P4-004-F3-target-identity-continuity.json` | Fact mapping 正确却出现颜色/组件/跨镜头 identity 漂移 | target identity/continuity 不得由 claim 或模型相似度代通过 |
| `VR-P4-004-F4-source-use-scope-vs-asset-qa.json` | Bundle/Index/Private Gate 状态被升级成 reference reuse 或 commercial entitlement | source-use scope、asset QA 和商业批准必须各自保留证据层 |
| `VR-P4-004-F5-originality-independent-review.json` | 仅模型审阅“不同”，但 source identity 表层和固定镜头关系未排除 | originality delta 要有独立 comparison 和替换/排除记录 |

## 通过标准

- 每个 fixture 的 `expected.disposition` 与实际处置一致。
- 每个 blocker 都能回指一个 artifact 字段、skill stop condition 或 SOP gate。
- Oracle 的 `fixture_schema=<count>` 只统计 fixture-shape validation；除非同一运行明确调用 canonical validator 并单独报告结果，不得称为 SV-001 schema acceptance。
- 不把 `observed`、`reference_claim`、`model_suggestion` 直接升级成 Product Fact。
- 不把一次合成样本的通过写成 CI、Private Gate、deployment、live 或 production acceptance。
- `VR-P4-003` 不重造 `VR-P3-004` 的通用多变量漂移、`VR-P3-005` 的泛化 rights unknown、`VR-P4-001-F2` 的一般表层复制或 `VR-P4-001-F4` 的趋势误路由 attention；消费 trend fixture 时仍须复用这些基础防线。
- `VR-P4-004` 不重造 `VR-P3-003` 的普通 claim deny-set、`VR-P3-004` 的通用多变量漂移、`VR-P3-005` 的泛化 rights unknown、`VR-P4-001-F2` 的一般 surface copy 或 `VR-P4-003-F4/F5` 的趋势模板/平台越权；它只覆盖媒体门内六个相邻但不可替代的交界错误。
