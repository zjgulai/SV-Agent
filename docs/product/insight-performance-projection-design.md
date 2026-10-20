# Insight & Performance Decision Brief Projection Design

## Status

`design selected — Gate D1 contract-only implementation complete locally; Gate D2 runtime binding not started`

本方案关闭 Roadmap 中“只读 Insight Projection 是否有足够用户价值”的判断，并同时收敛 Read-only Performance Signal Projection 的产品形态。Gate D1 已在当前工作区实现 typed Evidence Package contracts、validator、Synthetic Fixture 与 unavailable/in-memory reader；它仍未创建 migration、route、database table、runtime connector、descriptor reader、reviewed binding registry 或私有素材访问，也不代表 CI、部署或 production acceptance。

## Product decision

结论是 **有条件值得产品化，但只应先进入现有 Creative Comparison Lab，不应现在建立独立 Insight Hub**。

首个产品形态是一个 compare-bound `Decision Brief`：审核者打开两个不可变 Script Version 时，在同一个只读 Projection 中看到：

1. 当前 Product Truth 与 validation 为什么通过或阻断；
2. 哪个有界 Performance Observation 只足以形成 Creative Signal；
3. 哪个 Reported Product Claim 必须继续经过 confirmed/locked Fact Gate；
4. Experiment 和 Asset evidence 是否存在、是否匹配、还缺什么；
5. 下一步是 `revise`、`collect_evidence`、`test` 还是 `stop`，以及该建议不能证明什么。

它不是 KPI dashboard、搜索产品、自动推荐器或事实仓库。当前 Leap 只有一个德国七日切片，方法披露有限；它不足以支撑 winner、benchmark、跨市场结论或独立洞察产品。

## Current facts that shape the design

- 当前可信 runtime identity 是 Script Generation、Script Version、Product Snapshot 和 Product Fact；没有 Brand Workspace、Market、Product Family、Model、Variant、tenant、membership 或 RBAC identity。
- `ProductSnapshot` 只有 title、description、category path、images、price 与 canonical digest，不能可靠推导 Market、Product Family、Model 或 Variant。
- Leap 的已取证 subject 是 `momcozy-德国-奶瓶清洗暖奶器`，窗口为 2026-08-21 至 2026-08-27。
- Momcozy Private Gate 的固定基线是 M5 wearable-pump asset workspace。相同品牌名不能把二者自动 join；对于 M5 comparison，它们是明确的产品身份冲突。
- 当前 `CreativeComparisonLab` 已提供一个只读 GET、共享 Fact observation、稳定 Difference Ledger 和三个诚实的 external evidence `unavailable` section。
- Oumomo 与真实 Momcozy 素材是独立文件证据平面；普通 application runtime 不能直接扫描、解析或暴露它们。

因此，无 migration 的首个可信 binding 只能由独立、deployment-local、人工审核的 binding registry 把 `{snapshot_id, snapshot_canonical_digest, evidence_context}` 映射到唯一 package digest。`canonical_digest` 只证明 Snapshot 内容相同，不能单独充当 Snapshot identity；Runtime 必须从 PostgreSQL 校验 comparison 两端所绑定 Generation 的 Snapshot id 与重算 digest，再验证 package registry 与 binding registry，并以该 composite key 精确 lookup。零条 binding 时直接 `unavailable`，多条或未知 digest 时 quarantine；不能遍历 package 后猜测匹配。外部 package 本身不携带 FactFrame runtime identity；title、关键词、同品牌、相似 category 或模型生成匹配都不够。

## User value and success criteria

### Primary job

主要用户是 Momcozy 的内容策略与 Creative Ops 审核者。其核心问题不是“哪条内容分数最高”，而是：

> 这两个候选是否在同一事实合同下可比较；现有证据支持什么、不支持什么；在媒体投入前最小的安全下一步是什么？

### Why the value is real

- 把散落在 Product Truth、外部报告、实验记录和素材 QA 中的限制放回具体 comparison，减少把信号误读成事实的风险。
- 把 `unknown` 和 identity mismatch 变成显式工作项，而不是隐藏在文档脚注里。
- 复用已实现的 comparison identity 和单次 GET；无需先发明新的 workspace、decision 或 experiment identity。
- 让 Leap 的 22 videos、10,312 views、37 likes 与 Top 10 86.09% 集中度保持在正确的七日德国 subject 范围内，而不是变成泛化 Momcozy benchmark。

### Product success measures

首个 pilot 只观察以下结果，不以点击率或内容播放量作为 projection 自身成败：

- 审核者能否在一个页面说明 Observation、Inference、Unknown、Action 和 Guardrail；
- Reported Product Claim 被误当成 Product Fact 的次数是否为零；
- source/window/precision/subject mismatch 是否在作出 test 决定前被发现；
- evidence 缺失时是否选择 `collect_evidence`，而不是把缺失解释成零或失败；
- 每个显示值是否可回溯到安全 locator、review disposition 与服务端验证过的 package integrity record；只有 public package 的 digest 可以进入普通 response。

## Design It Twice result

| Alternative | Interface | Strength | Current failure | Disposition |
|---|---|---|---|---|
| Compare-bound inspection | 扩展 `CreativeComparisonLab.inspect(request)` | 最小 caller surface；复用现有 Script identity、Fact Gate、页面与 rollback | Projection 会变宽，必须保持 typed sections | **Selected** |
| Standalone Brand Insight | `BrandInsightProjector.project(question)` | 可支持 portfolio、claim、experiment、asset 多类问题 | 当前没有 workspace/subject/RBAC；会硬编码 Momcozy 或信任 caller 字符串 | North-star only |
| Package-first browser | `ReviewedEvidenceCatalog.open(package_ref)` | provenance、digest、quarantine 最清晰 | 以存储对象而非用户决策为中心；容易暴露 path/ref | Internal seam only |

推荐 hybrid：external seam 保持 compare-bound；implementation-private seam 使用 reviewed package reader。独立 Brand Insight 只在出现真实的非 comparison caller、canonical subject identity、RBAC 和至少两个可用 evidence plane 后复评。

## External Interface

不新增顶层 endpoint，也不让 caller 选择 package、path 或 evidence section：

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
    ) -> CreativeComparisonProjectionV2: ...
```

HTTP path 保持：

```text
GET /api/v1/scripts/{script_id}/creative-comparison
  ?control={control_version_id}
  &variant={variant_version_id}
```

未提供协商 header，或请求 `application/json` / `*/*` 时，这个 GET 继续返回 `creative-comparison-view-v1`，响应 `Content-Type: application/json`。D2 Web 在 flag 开启时发送 `Accept: application/vnd.ai-video.creative-comparison-v2+json, application/json;q=0.9`；server flag 开启且 v2 可用时返回 v2 与 `Content-Type: application/vnd.ai-video.creative-comparison-v2+json`，否则合法协商到 v1。所有响应设置 `Vary: Accept`；没有任何支持类型的 `Accept` 返回 RFC 9457 HTTP 406。server flag 只控制 v2 是否可选，Web flag 只控制是否发送这组 v2+v1 preferences；不得原地改变 v1 字段语义或把未知 media type 当成 v2。

## Projection contract

```python
class CreativeComparisonProjectionV2(BaseModel):
    schema_version: Literal["creative-comparison-view-v2"]
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
    decision_brief: DecisionBriefProjection
    limitations: tuple[ComparisonFinding, ...]
    projection_digest: str
```

四种 evidence 必须继续使用不同 typed section，不能建立万能 `Evidence` list：

- `product_truth_gate`：只来自 PostgreSQL Product Snapshot、Product Fact、Generation、Version 和 validator；
- `performance_evidence`：只包含 Performance Window、Performance Observation、Creative Signal、Reported Product Claim 和方法限制；
- `experiment_evidence`：普通 summary 只包含 Experiment Manifest scope、Observation/Finding、Evidence Level、artifact count 与 `integrity=verified`；Artifact digest 只属于未来有 trace permission 的 privileged projection；
- `asset_evidence`：普通 summary 只包含 Aggregate Index scope、count、QA Status、Commercial Approval availability 与 `integrity=verified`；Bundle ref、path 和 hash 只属于未来有 private-trace permission 的 privileged projection。

`decision_brief` 只是上述 section 的确定性只读编译结果，不拥有新事实：

```python
class DecisionBriefProjection(BaseModel):
    question_key: Literal["creative_comparison_reviewability"]
    observed: tuple[DecisionStatement, ...]
    inferences: tuple[DecisionStatement, ...]
    unknowns: tuple[DecisionStatement, ...]
    candidate_action: Literal["revise", "collect_evidence", "test", "stop"]
    guardrails: tuple[DecisionStatement, ...]
    capability_path: tuple[Literal[
        "content_performance",
        "product_truth",
        "creative_comparison",
        "experiment_evidence",
        "asset_intelligence",
    ], ...]


class DecisionStatement(BaseModel):
    statement_ref: str
    evidence_context: Literal[
        "product_truth", "performance", "experiment", "asset"
    ]
    evidence_level: Literal["observation", "inference", "unknown"]
    source_refs: tuple[str, ...]
    text_key: str
    bounded_args: dict[str, str | int | Decimal]
    limitation_codes: tuple[str, ...]
```

`text_key` 必须来自 server-owned closed template registry，`bounded_args` 只接受 schema 允许的 typed values；package 不能提供显示 prose。不在 request-time 调用 LLM。Inference 只能引用 reviewed disposition，Action 只来自 deterministic rule table；private reasoning 不进入 Projection。

## Performance evidence schema

```python
EvidenceSectionState = Literal[
    "available",
    "partial",
    "unavailable",
    "out_of_scope",
    "quarantined",
    "restricted",
]

SubjectRelation = Literal[
    "exact_snapshot",
    "reviewed_snapshot_selection",
    "reviewed_family_context",
    "unresolved",
    "conflict",
]

MeasurementState = Literal[
    "observed",
    "missing",
    "unknown",
    "not_reported",
    "not_collected",
    "source_ambiguous",
    "not_applicable",
    "redacted",
]

class PerformanceObservationProjection(BaseModel):
    observation_ref: str
    platform: Literal["all", "instagram", "tiktok", "youtube"]
    metric: Literal[
        "published_videos", "views", "likes", "comments", "shares",
        "accounts", "followers", "engagement_rate",
    ]
    state: MeasurementState
    value: Decimal | None
    unit: Literal["count", "ratio"]
    source_display: str | None
    source_presentations: tuple[SourcePresentation, ...]
    precision: Literal["exact_payload", "rounded_ui", "unresolved"]
    disposition: Literal["cite", "recompute", "test", "reject"]


class SourcePresentation(BaseModel):
    surface: Literal["getter_payload", "page_ui"]
    display: str
```

Measurement rules：

1. `state=observed` 时 `value` 必须存在，`0` 是合法观察值；
2. 其他 state 的 `value` 必须为 `null`；
3. `missing` 只表示 source contract 规定应存在的 metric key 缺失；package schema 自身 required field 缺失直接 quarantine，不编码成 metric `missing`；
4. `unknown` 表示 reviewer 无法判定值或采集状态，且不存在两个已观察 surface 的冲突；`not_reported` 表示来源根本未提供该 metric/surface；`not_collected` 表示来源明确声明未采集；`source_ambiguous` 表示两个已观察 surface 冲突；这些状态互斥；
5. Leap comments 与 Instagram followers 的 payload `0` / UI `-` 冲突必须成为 `source_ambiguous`，不能显示为零；aggregate shares 可保留 observed zero，但当前 platform share breakdown 固定为 `not_reported`；
6. payload 的 `10,312` 与 UI 的 `10.3K` 分开保留 exact value、source display 和 precision；
7. `unavailable`、`quarantined`、`restricted` 是 section state，不得伪装成 metric value；
8. 七日 aggregate 不能按任意三日 filter 重新计算；window 不对齐时保持原窗口并显示 limitation。

## Subject and window binding

未来 canonical product identity 的粒度必须保持：

```text
Brand Workspace → Market → Product Family → Model → Variant
```

`Asset Bundle` 是关联到该 identity 的素材单元，不是 Product Variant 或销售 bundle。

首个无 migration pilot 不声称已存在这套 canonical identity。它只允许：

```text
verified public package digest
  + deployment-local reviewed binding registry
  + frozen Product Snapshot id and canonical digest
  + closed evidence context and reviewed expected scope digest
  → one Creative Comparison
```

Binding rules：

- `exact_snapshot`：只保留给未来 package subject 与 canonical Snapshot target identity 完整一致的情形。当前 pilot 的独立 binding registry 用 Snapshot id + 重算 digest + evidence context 做人工选择，并校验 reviewed expected scope；这仍不证明 target Market/Model/Variant 已匹配，因此 section 必须保持 `partial/source-scoped hypothesis`，不能声称 `exact_snapshot` 或 target-scope matched evidence。
- `reviewed_snapshot_selection`：D2 pilot 的唯一可用 relation；表示 composite Snapshot binding 和 expected source scope 已人工审核，只允许 `partial/source-scoped hypothesis`，不得提升为 target evidence。
- `reviewed_family_context`：只有未来建立 canonical Product Family binding 后才允许；它只能形成 hypothesis context，不能支持 claim 或 candidate-specific结论。
- `unresolved`：没有足够 identity；section 显示 unavailable/limitation，不做 title 或 category 猜测。
- `conflict`：任一已知 Market、Product Family、Model 或 Variant 冲突；不得进入 comparison evidence。

每个 evidence plane 保留自己的时间语义，不能伪造跨平面的原子快照：

- Product Truth：Snapshot identity 与 DB `observed_at`；
- Performance：window start/end、timezone state、platform、captured_at 与 source snapshot state；
- Experiment：frozen configuration 与 observation interval；
- Asset：Aggregate release digest 与 Bundle observed-at coverage。

## Reviewed package contract

首个允许考虑的 package 是公开、安全、人工审核的 Performance package；不是 Markdown、网页缓存或任意 JSON dump。

```json
{
  "schema_version": "reviewed-performance-package.v1",
  "package_ref": "leap-momcozy-de-bottle-care-2026-08-21-27-v1",
  "evidence_context": "content_performance",
  "visibility": "public_reviewed",
  "subject": {
    "brand_workspace": "momcozy",
    "market": "DE",
    "product_family": "bottle_washer_warmer",
    "model": {"state": "not_reported", "value": null},
    "variant": {"state": "not_reported", "value": null},
    "source_subject_label": "momcozy-德国-奶瓶清洗暖奶器"
  },
  "window": {
    "start": "2026-08-21",
    "end": "2026-08-27",
    "timezone": {"state": "not_reported", "value": null}
  },
  "source": {
    "locator": "https://leap-ai-delta.vercel.app/public-report/c89da8a0-681f-42ed-91b2-8a3062f19ac8",
    "captured_on": "2026-08-27",
    "captured_at": {"state": "not_reported", "value": null},
    "snapshot_state": "not_reported",
    "collection_method": {"state": "unknown", "value": null},
    "deduplication_method": {"state": "unknown", "value": null},
    "paid_organic_split": {"state": "unknown", "value": null},
    "ranking_formula": {"state": "unknown", "value": null}
  },
  "review": {
    "review_state": "reviewed_with_limitations",
    "review_scope": "technical_and_claim_safety",
    "review_policy_version": "performance-review.v1",
    "reviewed_at": "<iso8601>"
  },
  "observations": [
    {
      "observation_ref": "overall.views",
      "platform": "all",
      "metric": "views",
      "state": "observed",
      "value": 10312,
      "unit": "count",
      "source_display": "10.3K",
      "source_presentations": [],
      "precision": "exact_payload",
      "disposition": "cite"
    },
    {
      "observation_ref": "overall.comments",
      "platform": "all",
      "metric": "comments",
      "state": "source_ambiguous",
      "value": null,
      "unit": "count",
      "source_display": null,
      "source_presentations": [
        {"surface": "getter_payload", "display": "0"},
        {"surface": "page_ui", "display": "-"}
      ],
      "precision": "unresolved",
      "disposition": "recompute"
    }
  ],
  "creative_signals": [
    {
      "signal_ref": "manual_to_automation_relief",
      "role": "hypothesis_only",
      "disposition": "test"
    }
  ],
  "reported_product_claims": [
    {
      "claim_ref": "high_temperature_disinfection",
      "role": "fact_gate_required",
      "fact_gate": "required",
      "disposition": "reject"
    }
  ],
  "limitations": [
    "COLLECTION_METHOD_UNDISCLOSED",
    "DEDUPLICATION_UNDISCLOSED",
    "PAID_ORGANIC_SPLIT_UNDISCLOSED",
    "RANKING_FORMULA_UNDISCLOSED",
    "SOURCE_TIMEZONE_UNDISCLOSED"
  ],
  "package_digest": "<sha256 over canonical package body without package_digest>"
}
```

Package invariants：

- canonical digest 不包含自身 `package_digest` 字段；
- schema、package size、closed enums、source/window、review、digest 和 safe-value scan 必须全部通过；binding 由独立 registry 验证；
- manifest 只指向一个 digest-named immutable package，不递归发现“最新”文件；
- caller 不能传 path、package ref、source URL 或 binding；
- 不保存 raw full page、Cookie、signed URL、absolute path、person identity、external task ID 或 media bytes；
- binding registry 对同一 Snapshot/context 指向多个 active package，或相同 ref 对应不同 digest，是 quarantine，不做 winner selection；
- package 不能包含 Product Fact mutation、Creative Pattern install 或 Decision Event 指令。

Registry 使用 immutable revision，不使用 `latest`、mtime 或 caller path：

```json
{
  "schema_version": "reviewed-performance-registry.v1",
  "registry_revision": 1,
  "exposure": "public",
  "classification": "public_reviewed",
  "review_policy_version": "performance-review.v1",
  "retention_class": "public_reproducible",
  "entries": [
    {
      "package_ref": "leap-momcozy-de-bottle-care-2026-08-21-27-v1",
      "state": "active",
      "package_digest": "<semantic sha256>",
      "package_bytes_sha256": "<byte sha256>",
      "scope_digest": "<subject and window sha256>",
      "eligible_from": "<iso8601>",
      "eligible_until": "<iso8601>",
      "purge_not_before": "<iso8601>"
    }
  ],
  "registry_digest": "<sha256 over canonical registry body without registry_digest>"
}
```

独立 local binding registry 不修改可移植 public package：

```json
{
  "schema_version": "comparison-evidence-binding-registry.v1",
  "policy_version": "manual-snapshot-binding.v1",
  "entries": [
    {
      "snapshot_id": "<Product Snapshot UUID>",
      "snapshot_canonical_digest": "<recomputed frozen Product Snapshot sha256>",
      "evidence_context": "performance",
      "package_digest": "<verified public package sha256>",
      "expected_scope_digest": "<reviewed subject and window sha256>",
      "relation": "manual_snapshot_selection",
      "target_identity_state": "unresolved",
      "binding_review_ref": "review:comparison-evidence-binding-v1"
    }
  ],
  "registry_digest": "<sha256 over canonical registry body without registry_digest>"
}
```

`target_identity_state=unresolved` 强制 v2 把 Performance section 显示为 `partial/source-scoped hypothesis`；只有未来 canonical Market/Product Family/Model/Variant binding 完整且一致，才可升级为 target-scope matched。D3 获批后，这个 binding 才能迁入 PostgreSQL append-only identity/ownership model。

Registry exposure、package visibility 和 deployment policy 必须严格求交。Performance package 的 `eligible_until` 必须存在，且 `purge_not_before >= eligible_until`。Filesystem reader 必须逐级使用 owned directory descriptor 与 `O_DIRECTORY | O_NOFOLLOW`；leaf 必须是 regular file、当前 owner、`nlink=1` 且不可 group/world write。解析前执行 bounded bytes、object/array/string count、string length 和 duplicate-key 检查；canonical bytes 必须相等，读取前后 `fstat` 必须一致。

离线生命周期为 `candidate → schema_validated → digest_validated → safety_validated → reviewed → active`；任一步失败进入 `quarantined`，active 只能追加新 revision 变为 `superseded`、`revoked` 或 `expired`。Runtime 只读这些状态，不执行 activate、revoke、supersede、purge 或自动修复。被 Finding/decision 引用的 package 在 retention policy 到期前不得物理删除；任何 purge 都需要独立的精确范围与可恢复审计，不属于本设计的 runtime。

## Internal seam and adapters

```python
@dataclass(frozen=True, slots=True)
class ComparisonEvidenceSubject:
    product_snapshot_id: UUID
    product_snapshot_canonical_digest: str
    evidence_context: Literal["performance", "experiment", "asset"]


class ComparisonEvidenceReader(Protocol):
    async def read(
        self,
        subject: ComparisonEvidenceSubject,
    ) -> ComparisonEvidenceSet: ...
```

`ComparisonEvidenceSet` 保留独立 `performance`、`experiment` 和 `asset` typed fields。这个 seam 位于 `CreativeComparisonLab` implementation 内，不出现在 route、React 或 Product domain。

至少三个 Adapter 使它成为真实 seam：

- `UnavailableComparisonEvidenceReader`：当前默认；不做 I/O，全部诚实降级；
- `ReviewedPackageComparisonEvidenceReader`：未来只读取固定 manifest 与一个大小有界的 immutable package；禁止 network、recursive discovery、symlink escape 和 caller path；
- `InMemoryComparisonEvidenceReader`：Interface tests 构造 available、partial、unavailable、quarantined、zero、ambiguous 和 conflict 情形。

PostgreSQL 继续直接通过现有 `AsyncSession` 与 integration fixture 测试；不新增只有一个 Adapter 的 `ProductTruthPort`。真实 Leap 网站是 true external dependency，永远不成为 request-time Adapter。

## Gate order and deterministic behavior

```text
comparison identity
  → comparability
  → PostgreSQL Product Truth
  → stored/live validation
  → Storyboard readiness
  → reload Snapshot and verify id + recomputed digest against both bound Generations
  → validate pinned package registry and binding registry
  → lookup {Snapshot id, digest, evidence context} in the verified binding registry
  → zero matches: generic unavailable
  → multiple matches or unknown package digest: binding-integrity quarantine
  → exactly one digest: resolve its single package-registry entry
  → candidate / validated / reviewed / superseded / revoked / expired / not-yet-eligible: generic unavailable with one internal-only reason
  → quarantined or illegal lifecycle: binding-integrity quarantine
  → active and eligible: continue
  → open the digest-derived immutable regular file
  → validate canonical bytes/package schema/digest/safety
  → compare verified package scope digest with binding expected_scope_digest
  → context-specific evidence projection
  → deterministic Decision Brief
  → stable redaction/sort/digest
```

- 判定顺序固定：binding count → package digest presence → registry lifecycle → eligibility → filesystem/package integrity → scope equality；每个输入只落入一个分支。Registry validation 只能读取 closed registry fields；任何 package field 在完整 package 验证前都不得参与 subject binding、日志或 response。Runtime 不遍历 package 来猜 binding。
- Product Truth 或 identity 的系统失败保持现有 404/409/500/503，并在失败前不读 external package。
- External evidence 不能改变 Product Truth、Candidate、Difference、Validation 或 Storyboard state。
- 缺 evidence 产生 `needs_evidence`，不是 system error。
- package mtime、读取 path、DB statement time 和 UI lens 不进入 `projection_digest`。用户可见 digest 只对授权后、已 redacted 的 response body 计算；隐藏的 private package/registry digest 只留在服务端 integrity record，不形成跨权限关联信号。
- 排序固定为 evidence context、platform、metric、signal ref、claim ref 和 limitation code。

## Error and quarantine contract

| Condition | Projection/HTTP | Public stable code | Internal audit reason | Disclosure rule |
|---|---|---|---|---|
| feature off、catalog 未配置、零条 binding | HTTP 200 / `unavailable` | `PERFORMANCE_EVIDENCE_UNAVAILABLE` | `FEATURE_OFF` / `CATALOG_UNCONFIGURED` / `BINDING_NOT_FOUND` | public response 不区分原因 |
| package 尚在 candidate/validated/reviewed、已 superseded/revoked/expired，或尚未到 eligible window | HTTP 200 / `unavailable` | `PERFORMANCE_EVIDENCE_UNAVAILABLE` | `EVIDENCE_PACKAGE_NOT_ACTIVE` / `EVIDENCE_PACKAGE_SUPERSEDED` / `EVIDENCE_PACKAGE_REVOKED` / `EVIDENCE_PACKAGE_EXPIRED` / `EVIDENCE_PACKAGE_NOT_YET_ELIGIBLE`，按固定 lifecycle/time 顺序只取一个 | internal reason 仅进入受控 audit，不进 response/log message |
| package filesystem 暂时不可读 | HTTP 200 / `unavailable` | `PERFORMANCE_EVIDENCE_UNAVAILABLE` | `EVIDENCE_SOURCE_UNAVAILABLE` | Product Truth 仍可读，不确认 package existence |
| 单个 metric 缺失或方法未披露 | HTTP 200 / `partial` | 对应公开 limitation code | 同 public code | 显示 state，不补值 |
| subject 未解析 | HTTP 200 / `unavailable` | `PERFORMANCE_EVIDENCE_UNAVAILABLE` | `EVIDENCE_SUBJECT_UNRESOLVED` | 不做 fuzzy match |
| subject/scope 明确冲突 | HTTP 200 / `out_of_scope` | `PERFORMANCE_EVIDENCE_OUT_OF_SCOPE` | `EVIDENCE_SUBJECT_CONFLICT` | 不显示不匹配 package 内容 |
| 多条 binding、unknown package digest 或 binding registry integrity invalid | HTTP 200 / `quarantined` | `PERFORMANCE_EVIDENCE_QUARANTINED` | `EVIDENCE_BINDING_INTEGRITY_INVALID` | 不返回 registry/package 是否存在、ref/path/digest |
| registry entry 已 quarantined 或 lifecycle state 非法 | HTTP 200 / `quarantined` | `PERFORMANCE_EVIDENCE_QUARANTINED` | `EVIDENCE_PACKAGE_QUARANTINED` / `EVIDENCE_LIFECYCLE_INVALID` | 不返回 lifecycle、ref/path/digest |
| schema unsupported 或 digest mismatch | HTTP 200 / `quarantined` | `PERFORMANCE_EVIDENCE_QUARANTINED` | `EVIDENCE_SCHEMA_UNSUPPORTED` / `EVIDENCE_INTEGRITY_INVALID` | 不返回 raw field/ref/path/digest |
| package visibility、registry classification 与 deployment exposure 不一致 | HTTP 200 / `quarantined` | `PERFORMANCE_EVIDENCE_QUARANTINED` | `EVIDENCE_EXPOSURE_INVALID` | 不返回 exposure 细节、ref/path/digest |
| review policy version 不匹配或 retention 非法 | HTTP 200 / `quarantined` | `PERFORMANCE_EVIDENCE_QUARANTINED` | `EVIDENCE_POLICY_INVALID` | 不返回 policy、ref/path/digest |
| unsafe value / path escape / symlink escape | HTTP 200 / `quarantined` | `PERFORMANCE_EVIDENCE_QUARANTINED` | `EVIDENCE_SAFETY_INVALID` | 只返回 public generic code |
| Projection sanitizer 自身失效 | HTTP 500 | `COMPARISON_PROJECTION_INTEGRITY_ERROR` | 同 public code | fail closed |
| PostgreSQL unavailable | HTTP 503 | `PRODUCT_TRUTH_UNAVAILABLE` | 同 public code | 整体失败 |

Internal audit reason 是 server-only closed enum，只能进入访问受控、retention 有界的 audit sink；普通 application log、metric label、cache key、response 和 `projection_digest` 都不能携带它。这样 public state/code 不构成 package existence、lifecycle 或 deployment configuration oracle。

## Ownership and permission boundary

`Brand Workspace` 是品牌分析视角，不是 tenant。当前没有 auth/RBAC，因此：

- 第一阶段只能考虑 `public_reviewed` 且已通过 safe projection 的 Performance package；
- Oumomo 和 Momcozy private package 继续 `unavailable`；
- 不显示 `restricted` 卡片来暗示某个私有 package 存在；
- package owner、reviewer person identity、private Bundle ref/path/hash 不进入 response；
- deployment 到共享环境前必须另行批准 Workspace membership、subject ownership 与 permission matrix。

未来最小权限应分开：

- `comparison:read`
- `performance-evidence:summary`
- `experiment-evidence:summary`
- `asset-evidence:summary`
- `asset-evidence:private-trace`
- `commercial-approval:read`

授权必须发生在 private Adapter 读取前。非成员统一返回 404，避免 workspace 枚举；已确认成员缺少字段权限时才使用 `restricted/redacted`。D2 只允许缓存 `ComparisonEvidenceSet`，不缓存含 Candidate/Product Truth/Decision Brief 的完整 Projection。evidence cache key 必须包含 workspace（未来）、Snapshot id、Snapshot canonical digest、evidence context、redaction scope、evidence schema、policy version、package registry digest、binding registry digest 与 resolved package digest；每次请求必须先读取并验证当前两个 registry revision，之后才允许 cache hit。缓存 TTL 不得超过所有适用 policy 和 package 中最早的 `eligible_until`；新 revision、revoke、supersede 通过 revision/digest 切换原子失效。若未来缓存完整 Projection，key 还必须加入 `script_id`、有序 control/variant version ids 与当前 Product Truth observation identity/version/digest，并另行评审。

## UX contract — selected Variant C evolution

Production UI 延续 Variant C 的信息层级，但不复制 prototype fixture：

1. 顶部先显示 `blocked` 与 `needs_evidence`，并固定展示 Control、Variant、Snapshot 和 Projection schema；
2. 冻结合同条显示 single variable、Product Truth、subject relation 和 disposition；
3. `Decision Brief` 固定分为 Observation、Inference、Unknown、Action、Guardrail；
4. Script、Storyboard、Asset lens 仍只切换同一个 GET Projection，不再发请求；
5. Evidence Drawer 按 Product Truth、Performance、Experiment、Asset 四区展示，先显示 subject/window/binding，再显示 metric；
6. `0` 显示为 `0`；`source_ambiguous`、`not_reported`、`unavailable` 和 `quarantined` 使用不同文案与视觉，不统一成 `-`；
7. `conflict` 只显示稳定阻断和期望 scope，不显示不匹配 package 细节；
8. 页面没有 Freeze、Generate、Approve、Ship、Render、Publish 或 package selector；
9. `reviewable` 只表示可以继续 Creative Comparison Review，不表示商业批准或生产可用；
10. narrow-screen 顺序为 blocker → Decision Brief → candidates → Difference Ledger → evidence details。

当前 prototype 中的 Leap hypothesis 是 fixture。它不能进入 production comparison，除非独立 registry 存在对 frozen Product Snapshot id + recomputed canonical digest + evidence context 的人工 binding；该 binding 在 canonical target identity 缺失时仍只能产生 source-scoped hypothesis，尤其不能拿德国奶瓶清洗暖奶器信号支持 M5 Model/Variant。

## Rollout and rollback

### Gate D0 — this document

- 产品价值与 selected interface 已闭合；
- 没有 runtime、schema files、package、migration 或 external access。

### Gate D1 — contract-only implementation, separately approve

- 已定义 context-specific package models、closed enums、validator 和 committed Synthetic Fixture；
- 已建立 `Unavailable` 与 `InMemory` adapters；Synthetic Fixture 保留 Leap 已审核的公开 window、观察值与缺失语义，但不是 runtime package 或生产验收；
- 不连接 Web、filesystem runtime、私有 evidence、PostgreSQL、route 或现有 `CreativeComparisonLab`；
- 后续 D2 才能在独立批准后引入 descriptor-bound reader、binding registry 和 v2 projection。

### Gate D2 — local public-performance pilot, separately approve

- 增加 descriptor-bound `ReviewedPackage` Adapter 与独立、人工审核的 Snapshot id + digest + evidence-context binding registry；
- 扩展 `CreativeComparisonProjectionV2` 和 Variant C production UI；
- 默认 GET 继续返回 v1；Web flag 发送 v2 优先、`application/json` v1 fallback 的 closed `Accept`，server flag 只让 v2 成为可选 representation，响应设置正确 `Content-Type` 与 `Vary: Accept`；
- server flag 默认关闭；零条 matching binding 时 v2 honest degradation 为 `unavailable`，多条 matching binding 必须 `quarantined`；
- 不接入 Oumomo 或真实 Momcozy private library。

### Gate D3 — shared/private evidence, new architecture approval

- 建立 tenant、Brand Workspace membership、canonical Product Family/Model/Variant、append-only Subject Binding 与 Reviewed Package Registry；
- migration、backfill、RBAC、cache isolation、retention、audit 和 rollback 必须独立验证；
- private evidence 通过安全 materialized projection 进入，普通 server 永不扫描真实库根目录。

### Gate D4 — standalone Brand Insight, reassess only

只有存在至少两个真实非 comparison decision caller、至少两个可用 evidence plane，并已完成 identity/RBAC 时，才复评问题驱动的 standalone projection。不要提前创建通用查询、分页或 dashboard。

Rollback：

- server evidence flag 关闭后不选择 v2 representation，并使用 `UnavailableComparisonEvidenceReader`；带 v1 fallback 的 Web 请求合法协商到 v1；
- Web flag 关闭后停止发送 v2 preference，同一路径确定性返回当前 Creative Comparison v1；现有 `VITE_CREATIVE_COMPARISON_LAB=false` 仍可回到 legacy diff；
- immutable manifest 只能切回仍满足当前 exposure、revocation、expiry 与 retention policy 的已验证旧 pinned registry revision；rollback 不能绕过 revoke 或 expiry，也不重写 package；
- D1/D2 没有 migration、backfill、data deletion 或 business writes；
- quarantine、read failure 或 flag-off 不能改变 Product Fact、Script Version、Storyboard 或现有 current asset release。

## Test and acceptance surface

下一 implementation gate 至少覆盖：

1. binding registry 的 `{Snapshot id, recomputed digest, evidence context}` composite key 命中、两端 Generation 绑定一致，以及 title/brand/category fuzzy match 拒绝；
2. `reviewed_snapshot_selection` 只能得到 `partial/source-scoped hypothesis`；德国 bottle washer package 对 M5 Snapshot 的 canonical identity conflict 必须 `out_of_scope`；
3. exact value `10,312` 与 display `10.3K` 同时保留；
4. comments 与 Instagram followers 的 payload `0` / UI `-` 变成 `source_ambiguous`，aggregate shares zero 与 platform shares `not_reported` 分开；
5. `missing`、`unknown`、`not_reported`、`not_collected`、`source_ambiguous`、observed zero 与 unavailable 的互斥 validator；
6. unsupported schema、digest mismatch、duplicate active match、unsafe value、symlink/path escape 全部 quarantine；
7. package read failure 不影响 Product Truth comparison；
8. Product Truth failure 时不读取 package；
9. external evidence 不改变 blockers、differences、validation 或 Storyboard state；
10. deterministic ordering 和 digest；
11. GET 无 INSERT/UPDATE/DELETE、network、recursive scan 或 commit；
12. response 无 raw page、absolute path、signed URL、Cookie、external task ID、private Bundle ref/hash 或 model reasoning；
13. Web 仍只发一个 GET，lens 本地切换；
14. unavailable、partial、out-of-scope、quarantined、restricted、404、503 和 narrow-screen 独立呈现；
15. v2+v1 fallback `Accept`、两种 response `Content-Type`、HTTP 406、`Vary: Accept`、server/Web flags 分别回退且 v1/legacy view 仍可用；
16. 只缓存 `ComparisonEvidenceSet`，cache key 覆盖 Snapshot composite key 与 registry/binding/package revisions；必须先读当前 registry 才能命中，TTL 不越过最早 expiry，revoke 后不返回旧证据；
17. not-active、superseded、expired、revoked、quarantined/illegal lifecycle、exposure mismatch、binding integrity 与 policy/retention invalid 只产生 public generic code；internal audit reason 不进入 response、普通日志、cache key 或 digest。

## No-go conditions

以下任一条件成立时不得开始 D2：

- 只能在 request time 解析 Markdown、网页或任意 ignored directory；
- package 没有 source、subject、window、precision、review、limitations 和 digest；
- 只能靠 title、关键词、相同品牌或 AI 相似度连接 Product Snapshot；
- 无法区分 observed zero、source ambiguous、not reported 与 unavailable；
- 要把 ranking 变成 score、winner、causal lift 或默认 Creative Pattern；
- 要把 Reported Product Claim、Experiment Finding 或 Asset copy 写成 Product Fact；
- invalid package 仍做部分容错显示；
- 在无 auth/RBAC 时读取或暗示私有 Oumomo/Momcozy package；
- 要创建 Decision Event、Comparison identity、Experiment identity、migration 或 runtime network connector；
- 要把本设计、Synthetic Fixture、Capability Graph 或 local test 作为部署/production proof。

D3 的 prerequisite 不是“避免 migration”，而是先单独批准并验证 migration、append-only identity/binding/registry、ownership、RBAC、retention、audit、cache isolation 与 rollback。任何一项没有独立 gate 时，D3 不得开始。

## Final capability fusion

```text
bounded Performance Observation
  → verified package + independent reviewed Snapshot selection
  → Creative Signal / Reported Product Claim
  → PostgreSQL Product Truth allow/deny gate
  → immutable Control / Variant comparison
  → Experiment Evidence and Asset Evidence availability
  → deterministic Decision Brief
  → revise / collect evidence / test / stop
```

融合发生在一个只读决策 Projection 中；事实、性能、实验和素材继续保持各自权威、窗口、缺失语义和权限边界。Momcozy 是首要 Brand Workspace，FactFrame 仍是产品与控制平面。
