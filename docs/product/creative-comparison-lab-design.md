# Creative Comparison Lab Design

## Status

`implemented locally — Phase 1` — Variant C 已落到现有 compare route、只读 application Module 与 GET Projection。没有 migration、业务写入、在线外部连接、RenderJob、部署或 production acceptance。

外部 evidence 的下一阶段产品形态已在 [Insight & Performance Decision Brief Projection Design](insight-performance-projection-design.md) 中收敛为同一 compare-bound Interface 的 v2 设计。当前 v1 implementation 仍不读取 package、filesystem 或 network。

## Product decision

Creative Comparison Lab 用来回答一个问题：两个不可变 Creative Candidate 是否在同一事实合同下形成了可审核的单变量比较，以及当前为什么 `blocked`、`needs_evidence` 或 `reviewable`。

首期不是 A/B testing、winner ranking 或发布系统。它不推断因果，不自动选择胜者，也不把 Leap、Oumomo 或素材证据升级为 Product Fact。

## Design It Twice result

本设计比较了三个 Interface：

1. **Minimal inspection** — `inspect(comparison_id)`，Interface 最小，但要求先新增持久化 comparison identity 和 migration。
2. **Flexible projection query** — `project(query)` 支持多 candidate 和可选 section，扩展性高，但容易演化为 mini-GraphQL 并扩大未批准范围。
3. **Page capsule** — `open(lab_id)` 最适合 Web caller，但同样提前引入 lab persistence、offline compiler 和新 identity。

推荐 hybrid：采用 Minimal inspection 的 depth 和 Page capsule 的单请求 View，但 Phase 1 直接使用现有 Script identity，不创建 `comparison_id` 或 `lab_id`。

## Phase 1 Interface

`CreativeComparisonLab` 是 application-layer deep Module。External Seam 只有一个 operation：

```python
@dataclass(frozen=True, slots=True)
class CreativeComparisonRequest:
    script_id: UUID
    control_version_id: UUID
    variant_version_id: UUID


class CreativeComparisonLab:
    async def inspect(
        self,
        request: CreativeComparisonRequest,
    ) -> CreativeComparisonProjection: ...
```

HTTP transport：

```text
GET /api/v1/scripts/{script_id}/creative-comparison
  ?control={control_version_id}
  &variant={variant_version_id}
```

Web 继续使用现有页面：

```text
/scripts/{script_id}/compare?left={control}&right={variant}
```

不新增顶层 production route。当前 `/prototype/momcozy-decision-workbench` 继续保持 DEV-only primary source，不能直接提升为 production code。

## Projection contract

```python
ReadinessState = Literal["blocked", "needs_evidence", "reviewable"]
EvidenceAvailability = Literal["available", "unavailable", "quarantined"]
DifferenceKind = Literal[
    "declared_dimension",
    "unexpected_change",
    "fact_binding_change",
    "unverified",
]


@dataclass(frozen=True, slots=True)
class CreativeComparisonProjection:
    schema_version: Literal["creative-comparison-view-v1"]
    script_id: UUID
    observed_at: datetime
    readiness: ReadinessProjection
    control: CandidateProjection
    variant: CandidateProjection
    differences: tuple[SemanticDifference, ...]
    product_truth_gate: ProductTruthGateProjection
    performance_evidence: PerformanceEvidenceProjection
    experiment_evidence: ExperimentEvidenceProjection
    asset_evidence: AssetEvidenceProjection
    limitations: tuple[LimitationProjection, ...]
    projection_digest: str
```

四种 evidence projection 必须保持独立字段，不建立模糊的万能 `Evidence` 对象：

- `product_truth_gate` 只来自 PostgreSQL Product Snapshot、Product Fact、Generation、Version、Storyboard 和现有 validator；
- `performance_evidence` 只包含 Performance Window、Observation、Creative Signal、Reported Product Claim 和方法缺口；
- `experiment_evidence` 只包含 Experiment Manifest、Observation、Finding、Artifact hash 和 Evidence Level；
- `asset_evidence` 只包含 Asset Bundle、Recipe、Provenance、hash、QA Status 和 Commercial Approval。

Phase 1 没有获批的机器化外部证据 schema，因此后三个 section 默认返回 `unavailable` 加安全文档引用，而不是解析 Markdown、扫描 ignored 素材目录或调用外部网络。

## Invariants

1. Control 与 Variant 必须是两个不同的 Script Version，且属于 URL 中的同一 Script Generation。
2. 两者必须绑定同一个 Product Snapshot、ordered Selected Fact、Excluded Fact deny-set、Promotion Fact 和 Creative Pattern Definition。
3. 读取时必须重新检查当前 Product Fact；只有 `confirmed` 或 `locked` 可以支持 visible Product Claim。
4. Stored Validation Report 与 live validation/preflight 必须同时保留，不能用旧的可接受结果覆盖当前阻断。
5. Phase 1 不接受 caller 声称的 `Creative Dimension`；没有 append-only Creative Comparison Contract 时，single-variable status 必须是 `unverified`。
6. 所有真实差异都必须返回。不能因为 UI 选择“Highlight differences”而隐藏未声明变化。
7. Leap 排名只形成 Creative Signal；Oumomo Finding 只形成 capability evidence；Asset Bundle 只形成 execution evidence；三者都不能支持 Product Claim。
8. `Hold` 或缺少 Commercial Approval 只能产生 `needs_evidence`，不能升级为可发布。
9. `reviewable` 只表示可以进行 Creative Comparison Review，不表示 render、legal、commercial 或 publishing approval。
10. 不计算 winner、score、priority 或 causal lift；Control 固定在前，Variant 固定在后。
11. missing、zero、unknown、unavailable 和 quarantined 必须保持不同。
12. 输出不能包含原始网页、媒体 bytes、绝对路径、signed URL、Cookie、外部任务 ID或模型私有推理。

## Readiness and disposition

固定 Gate 顺序：

```text
identity
  → comparability
  → product truth
  → script validation
  → storyboard readiness
  → performance evidence availability
  → experiment evidence availability
  → asset QA
```

- 任一事实、身份、validation、fact-binding change 或已知 unexpected change blocker 存在：`blocked`。
- 没有 blocker，但 single-variable 因缺少 Creative Comparison Contract 而未验证，或缺已批准的外部 evidence package、私有素材访问或 Commercial Approval：`needs_evidence`。本地 Aggregate Index 的存在本身不会改变 runtime readiness。
- 两者皆无：`reviewable`。

Phase 1 不返回 `ship` 或 `publishable`。页面只展示只读 `Review Disposition`：`revise`、`collect_evidence` 或 `stop`；它不写 Decision Event。

## Ordering and consistency

Module 分别读取 append-only Generation 与两个 append-only Version，再用一条 PostgreSQL statement 同时取得当前 Snapshot 的全部 Facts 与统一 `statement_timestamp()`。两个候选随后在内存中共享同一份 Fact observation，并分别计算 stored validation、live validation 与 Storyboard preflight；成功路径查询次数固定，不按 shot 或 finding 形成 N+1。

Phase 1 没有读取持久化 Storyboard/approval，也没有声明跨多个可变资源的 repeatable-read snapshot。`observed_at` 精确标记 Fact statement 的观察时间，不是整个数据库事务的一致性证明。若后续 Projection 引入 approval、asset 或 external evidence 等额外可变资源，必须先增加并验证 read-only repeatable-read 或等价的单 statement batch snapshot。

- facts 保留 Generation 中的 provider-priority 顺序；
- phases/shots 保留持久化顺序；
- findings 保留 `(path, rule_id)` 顺序；
- differences 按 `script → storyboard → asset → path → rule_id`；
- limitations 按 evidence context 和 source reference 稳定排序。

同一数据库观察和输入 digest 应产生同一 `projection_digest`；`observed_at` 不进入 digest。

## Error contract

使用现有 RFC 9457 Problem Details：

| Condition | HTTP/code | Meaning |
|---|---|---|
| Script 或任一 Version 不存在 | `404 COMPARISON_SUBJECT_NOT_FOUND` | identity 不存在 |
| Version 不属于同一 Script | `409 COMPARISON_REFERENCE_INVALID` | caller reference 冲突 |
| Unsupported projection schema | `409 COMPARISON_CONTRACT_UNSUPPORTED` | client/server contract 不兼容 |
| PostgreSQL unavailable | `503 PRODUCT_TRUTH_UNAVAILABLE` | 权威事实不可读，整体失败 |
| Product Truth invariant 损坏 | `500 PRODUCT_TRUTH_INTEGRITY_ERROR` | fail closed |

事实失效、validation finding、外部证据缺失、Asset `Hold` 和 unexpected difference 都是 HTTP 200 的业务投影，不是系统异常。

## Module depth and seam placement

External Interface 只让 caller 学习一个 request 和一个 projection。Implementation 隐藏：

- Version/Generation/Snapshot/Fact/Storyboard 的一致读取；
- current Fact eligibility 重验；
- raw JSON path diff 到 Semantic Difference 的编译；
- comparability 与 single-variable 检查；
- evidence role 降权、availability 和 digest 语义；
- readiness 聚合、稳定排序、redaction 和 canonical digest。

删除该 Module 后，上述规则会散回 FastAPI route、React tabs、repository caller 和 tests，因此它具有真实 Depth 和 Locality。

PostgreSQL 是 local-substitutable dependency；继续使用现有 `AsyncSession` 和真实 PostgreSQL integration fixture，不新增只有一个 adapter 的 `ProductTruthPort`。

Phase 1 不建立 Leap/Oumomo/Momcozy runtime adapter。后续若批准机器化离线 evidence package，才引入 implementation-private `ComparisonEvidenceReader` Seam，并至少提供 `Unavailable`、descriptor-bound reviewed-package 和 in-memory test Adapters。独立 reviewed binding registry 必须按 frozen Product Snapshot id + 重算 canonical digest + evidence context 把 verified public package 显式选择给 comparison；portable package 本身不保存 FactFrame identity，这项人工选择也不证明 target Market/Model/Variant 一致。相同品牌、title 或 category 不构成 binding。Oumomo 与真实 Momcozy private evidence 在 tenant/auth/RBAC 与安全 materialized projection 获批前继续 `unavailable`。

## UX contract

Production page 复用 C 的信息层级，但不复用 prototype implementation：

1. 顶部首先显示 `blocked` 与 `needs_evidence`，不先展示漂亮的 Control/Variant 画面。
2. 冻结合同区域在 Phase 1 明确显示 `single variable: unverified`。
3. Script、Storyboard、Asset tabs 只切换同一 Projection 的本地 lens，不各自发请求。
4. Difference Ledger 显示全部真实差异，并区分 expected、unexpected 和 fact-binding change。
5. Evidence Drawer 以四个 evidence context 分区；不可用来源显示限制，不显示零。
6. 页面不存在 Freeze、Generate、Approve、Ship、Render 或 Publish mutation。
7. loading、404、503、blocked、needs-evidence、partial/unavailable 和 narrow-screen 都必须有独立状态。

## Phase 1 test surface

Interface tests 穿过 `CreativeComparisonLab.inspect()`，API/Web tests 只验证 transport 和 rendering：

1. 同 Generation 的两个 Version 产生确定性 Projection。
2. 相同 Version、重复 ID 或跨 Generation reference 被拒绝。
3. current Fact 从 confirmed 变 proposed/rejected 后变为 blocked。
4. locked Fact 保持可用；excluded Fact visible copy 继续阻断。
5. Stored acceptable + live blocking finding 仍为 blocked。
6. Storyboard lineage 错误或 stale 显示 blocker。
7. 当前没有 Creative Comparison Contract 时 single-variable 为 unverified。
8. single-variable unverified 且无其他 blocker 时 readiness 为 needs_evidence，不误报 blocked 或 reviewable。
9. 外部 evidence section 为 unavailable，不触发 filesystem 或 network I/O。
10. shuffled repository rows 不改变稳定排序和 digest。
11. GET 不产生 INSERT/UPDATE/DELETE 或 commit。
12. response 不泄露私有路径、raw page、signed URL 或任务 ID。
13. Web 只发一个 Comparison GET；tabs 不再请求 API。
14. blocked 与 needs-evidence 可以同时显示。
15. production route 不包含 prototype fixture 或 switcher。

## Phase 2 approval gate

只有以下内容单独获批后，才能进入持久化实验：

- append-only `Creative Comparison Contract` schema 和 migration/rollback；
- `Creative Dimension` closed vocabulary，首个候选为 `hook_framing`；
- single platform、market、language、duration、audience、Pattern 和 stop conditions；
- immutable Control/Variant lineage 与生成/替代规则；
- reviewed offline evidence package schema、registry、digest 和 retention；
- tenant/ownership/RBAC；
- Decision Event 的 actor、authority、idempotency 和 replay；
- reviewed Asset Aggregate Index package、Commercial Approval 和私有素材访问；
- compiler/provider 生成合法 Hook Variant 的能力；
- migration、backfill、rollback、安全、a11y、integration/E2E 与 production acceptance。

Phase 2 的首选持久化 Interface 可以收敛为 `open(comparison_id)`，但不能在以上门禁完成前创建 identity 或表。

## Rollout and rollback

1. 先实现 Phase 1 application Module 与 integration tests。
2. 增加只读 API 和 Web compare page；`VITE_CREATIVE_COMPARISON_LAB=false` 可切回旧 compare view。
3. 本地与 CI 验证后，在无外部 evidence 的状态下确认 honest degradation。
4. 切换默认 compare rendering；旧 route 和旧 response 在观察期保留。
5. 回滚只需关闭 feature flag，数据库无 migration、无 backfill、无新写入。

## Acceptance boundary

Phase 1 已在本地实现并通过 application/API/Web 自动化验证。此状态不包含 migration、部署、真实用户权限、live external evidence、CI 或 production acceptance；不得把它表述为已上线、已接入 Leap/Oumomo/Momcozy 私有素材，或可 Render/Publish。
