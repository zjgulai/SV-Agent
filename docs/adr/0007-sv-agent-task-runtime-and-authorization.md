---
status: accepted
---

# SV-Agent 任务运行时、审批与授权边界

SV-Agent 采用独立的 PostgreSQL `Task` / `Run` 业务运行时：可变 current head 提供当前状态，typed append-only ledger 保留历史，现有 `Job` / `JobEvent` / `OutboxEvent` 只负责具体异步工具的技术执行与投递。外部 mutation 通过一个深的 application command Module，Human Approval 使用独立 seam；actor 只能由可信 adapter 注入，不能由请求 body 自报。该方案保持 FactFrame 既有事实与版本权威，不引入账号、远程公开写入、媒体生成、发布、计费或商业批准。

本 ADR 已于 2026-10-21 获用户批准；随后“同意，授权开始下一批任务”明确授权了 SV-102 的本地、test-first 实施。SV-102 的 additive migration 与内部 persistence adapter、SV-103 的内部只读 Tool Registry 与 factual ToolRun journal 已落地；公开写 route、actor/auth runtime、HumanApproval writer、提交、发布与部署仍受后续 ticket 和边界约束。

## 决策摘要

1. **持久化**：选择“关系型 current head + typed append-only ledger”，不采用 full event sourcing、普通 CRUD audit log 或 Job-as-Task。
2. **接口**：`SVRuntime` 只暴露 `engage` 与 `inspect`；`HumanApproval` 单独暴露 `decide`。REST、CLI、Agent UI 都是 adapter，不是业务状态 CRUD surface。
3. **权威**：PostgreSQL 是唯一业务事实源。Task/Run、Artifact、Approval 与 ToolRun 各自保留语义；Redis/Celery 仍只是运输。
4. **并发与恢复**：所有 mutation 使用 idempotency key、server-computed input digest 和 expected Task revision；未知结果只可重放完全相同的命令。
5. **授权**：deny by default，并在每次请求校验。Human、Agent、System 与 Operator 是不同 actor kind；Agent 推荐不能变成 Human Decision。
6. **迁移**：expand-first、无历史 backfill、写路径默认关闭。真实 Task 一旦存在，release rollback 只能停写并保留数据，不能 destructive downgrade。

## 领域边界

```text
Task
  -> Task revision
  -> zero or more Runs
       -> versioned RunPlan
       -> Artifact refs and verified runtime lineage
       -> ToolRuns
            -> optional existing Job
                 -> JobEvent + OutboxEvent
       -> immutable ApprovalRequests
            -> append-only DecisionEvents
```

- `Task` 是持续的用户目标与问题边界。
- `Run` 是针对一个 Task revision 的有界执行尝试；它不复制 Job 状态机。
- `RunPlan` 是 orchestration plan；它不是创意方法中的 `ReplicationPlan`。
- `ToolRun` 是 Agent 层的一次逻辑能力调用；它可以同步完成，也可以关联一个既有 Job。
- `Job` 仍只表示 `product_import` 或 `script_generation` 等技术执行。
- `ApprovalRequest` 是不可变、版本绑定的决定请求；`DecisionEvent` 是可信 Human 对该请求作出的不可变决定。
- `ArtifactRef` 的声明式 lineage 与 PostgreSQL 验证过的 runtime lineage 分开保存。

`Job.succeeded` 不能自动变成 `Run.completed_with_limits`；`Outbox.dead` 也不能自动变成业务 `failed` 或 `blocked`。只有 Task runtime 在重新校验 artifact、Fact、approval 和当前 revision 后才能推进 Run。

## 外部 Interface

### 深 Module

```text
SVRuntime.engage(
  interaction: StartTask | ContinueTask,
  call: AuthorizedCall
) -> TaskTurn

SVRuntime.inspect(
  task_id: TaskId,
  viewer: AuthorizedViewer
) -> TaskWorkspaceProjection

HumanApproval.decide(
  command: HumanDecisionCommand,
  human: VerifiedHumanCall
) -> TaskTurn
```

`ContinueTask.intent` 是 closed union：

```text
provide_input
request_plan
request_evidence
revise_plan
advance
resume_recovery
stop
```

Human decision 不在这个 union 中。`approve`、`reject`、`request_evidence` 和 `stop` 只能通过 `HumanApproval.decide`，避免 Agent tool surface 持有可伪装成人类的入口。内部 worker reconciliation 也走私有 application command，不进入公共 HTTP contract。

### HTTP adapter 提案

```text
POST /api/v1/sv-agent/tasks
GET  /api/v1/sv-agent/tasks
GET  /api/v1/sv-agent/tasks/{task_id}
POST /api/v1/sv-agent/tasks/{task_id}/actions
POST /api/v1/sv-agent/approval-requests/{approval_request_id}/decisions
GET  /api/v1/sv-agent/tasks/{task_id}/events
GET  /api/v1/sv-agent/tasks/{task_id}/artifacts
GET  /api/v1/sv-agent/tasks/{task_id}/approvals
GET  /api/v1/sv-agent/tasks/{task_id}/replay
```

这些 routes 只是未来 adapter 合同。当前没有批准实现或开放它们。禁止 `PATCH status`、客户端创建 ToolRun、客户端 append event，也禁止从 body 接收 actor、role、workspace 或 authority。

## 持久化形态

SV-102 通过 `0012_sv_agent_persistence` 实现以下 additive schema：

| Record | 形态 | 权威与约束 |
|---|---|---|
| `sv_tasks` | mutable current head | 当前 Task revision、active Run 与 bounded summary；每次成功 mutation 原子递增 revision |
| `sv_task_revisions` | append-only | 完整 TaskBrief revision；历史不覆盖 |
| `sv_runs` | mutable current head | 当前 Run state 与 revision；只允许规范中的 transition，且没有 `succeeded` |
| `sv_task_events` | append-only ordered ledger | Task/Run 的事实时间线；typed event，database sequence 排序，不含 private reasoning |
| `sv_run_plans` | append-only versions | 绑定 Task revision、workflow/capability version 和 canonical digest |
| `sv_artifacts` | append-only versions | 只存九类 SV artifact 的 closed payload、schema version、digest 与 input refs |
| `sv_runtime_lineage_links` | append-only verified links | 只记录由 authority adapter 验证过的派生关系；不把 artifact 自述当 DB 证明 |
| `sv_tool_runs` | immutable intent + mutable current head | intent、input digest、effect class、attempt fence、当前技术状态 |
| `sv_tool_run_events` | append-only | ToolRun attempt 与 outcome 历史；不复制 JobEvent |
| `sv_approval_requests` | immutable | exact Task/Run revision、gate、artifact version/digest、effects/non-effects、precondition digest 与 stale rules |
| `sv_decision_events` | append-only | Human decision、attribution、request digest 与 database sequence；Agent recommendation 不写入此表 |
| `sv_command_receipts` | append-only idempotency ledger | server-derived `(idempotency_scope, idempotency_key)` 唯一；receipt 仍绑定 Task；同 digest replay，异 digest conflict |
| `sv_tool_job_links` | append-only 1:0..1 link | 关联现有 Job；Job 只证明技术执行 |

现有 `ScriptVersion` 与 `StoryboardVersion` 不复制进 `sv_artifacts`。它们以 typed authority ref 参与 Task，并由现有 FK 和 application service 验证；九类新增 artifact 才使用 `sv_artifacts`。

SV-102 的实现边界：

- 13 张 `sv_*` 表、1 条 `sv_runtime_event_sequence`、10 个 append-only trigger 和 3 个 current-head guard 已实现；没有历史 backfill，也没有修改既有业务表语义。
- server-derived idempotency scope 解决 StartTask 在 response 丢失后尚不知道 `task_id` 时无法定位 receipt 的恢复缺口；客户端不能自报 scope 或 digest。
- event、receipt 和 Task summary 的 JSON 上限为 16 KiB；Artifact、RunPlan 和审批 envelope 的 JSON 上限为 256 KiB。应用层按 canonical JSON 校验，数据库另做硬上限。
- SV-102 adapter 开放内部 Task create/revise/get 与 factual replay seam。SV-103 进一步开放仅供内部同步 read tool 使用的 flush-only ToolRun lifecycle writer；创建时固定按 Task、Run 顺序加锁，状态更新同时比较 revision、上一状态和 attempt token，成功终态事件仅记录 typed output digest。它只记录读调用事实，不创建 Job、Outbox、ToolJobLink 或业务 Artifact。Run/Artifact/Approval/Decision writer、authorization、orchestrator、HTTP route 与 worker integration 仍未实现。
- Task/ToolRun/Decision 三种事件共用数据库 sequence；sequence gap 合法，顺序只能按 `event_sequence` 判断。

### Current state 与历史权威

- `sv_tasks`、`sv_runs`、`sv_tool_runs` 是各自 current state 的权威投影。
- `sv_task_events`、`sv_tool_run_events`、`sv_decision_events` 是不可变历史和顺序的权威。
- `sv_task_revisions`、`sv_run_plans`、`sv_artifacts`、`sv_approval_requests`、`sv_command_receipts`、`sv_runtime_lineage_links` 与 `sv_tool_job_links` 是不可变记录。
- current head 更新与对应 event 必须在同一 transaction；任何 drift 都 fail closed，不能静默修补历史。
- Redis、Celery result 和浏览器 conversation/sessionStorage 不是业务权威。

append-only 表使用 `RESTRICT` FK、数据库 sequence 和 `BEFORE UPDATE OR DELETE` 拒绝 trigger。current head 禁止删除；停止或归档通过新 revision 与 event 表达。

## Actor attribution 与 authorization

### Verified actor

`AuthorizedCall` / `VerifiedHumanCall` 只能由可信入口 adapter 构造，至少携带：

```text
actor_kind: human | agent | system | operator
actor_ref: opaque server-issued reference
authority_kind: local_explicit_confirmation | service_identity | authenticated_membership
authority_version
policy_version
authority_scope
```

- `human`：提供 Task 输入与 Human Decision。
- `agent`：编译计划、执行已授权 action、请求审批和输出 recommendation；不能创建 Human Decision。
- `system`：接收 worker/reconciler 的可信技术结果；不能代替 Human 或 Operator。
- `operator`：只处理部署侧恢复，例如既有 Outbox dead-letter retry；不能自动取得创意或商业批准权。

事件分别记录 `initiated_by`、`executed_by`、`decided_by` 的 applicable ref，避免把“谁发起”“谁执行”“谁批准”压成一个 actor。

### MVP 权限边界

当前项目没有 user、tenant、workspace membership 或 RBAC。MVP 因此只允许：

- 由本机受信任 host 注入的 `local_explicit_confirmation`，authority scope 固定为 `local_review_only`；
- 内部 Agent/Worker 使用 `service_identity`；
- 现有 deployment-channel Operator 命令维持独立边界。

本机 Human 可以作出明确标注为 local review 的 ReplicationContract / Storyboard 决定，但不能声称组织身份、rights、child safety、legal、commercial、platform、deployment 或 production authority。没有可信 actor adapter 时，所有 SV-Agent mutation 返回 `AUTHORIZATION_UNAVAILABLE`；public remote write surface 保持关闭。

未来 authenticated membership、workspace ownership 与远程写入需要单独批准的 identity adapter 和 policy migration。本 ADR 不创建 Account、Tenant、Role 或 Membership 表。当前也不启用 PostgreSQL RLS：没有可信的数据库 principal/membership mapping 时，RLS 不能替代 application authorization；未来引入时需单独设计，并考虑 table owner 默认通常绕过 policy 的行为。

授权规则 deny by default，并在每次请求根据 actor、action、resource、gate 与 policy version 重新判断。UI 隐藏按钮不构成授权。

## Approval contract

每个 ApprovalRequest 至少绑定：

```text
approval_request_id + request_version + request_digest
task_id + task_revision_at_request
run_id + run_revision_at_request
gate_kind
artifact_type + artifact_id + artifact_version + artifact_digest
precondition_digest
predicted_effects[] + explicit_non_effects[]
evidence_summary + limitations[]
stale_if[]
```

审批命令同时携带 current expected Task revision 和完整 Approval handle。Task revision mismatch 是并发冲突，需要刷新；只有 artifact、输入或声明的 stale dependency 改变才把 ApprovalRequest 语义判为 `stale`。无关的只读 observation 不自动作废审批。

一个 ApprovalRequest 只接受一个 Human DecisionEvent。`request_evidence` 会关闭原请求；补充证据后必须创建绑定新 precondition digest 的新请求。旧决定永远不迁移到新 artifact。Fact、ReplicationContract、Storyboard、rights、Media Integrity、commercial、deployment 与 production gate 保持独立，不能互相替代。

## Command transaction 与恢复

一次 mutation 固定按以下顺序执行：

1. Transport adapter 校验 shape，Identity adapter 产生 Verified actor，Authorization policy deny-by-default 判断。
2. 服务器规范化 command 并计算 input digest；不接受客户端自报 digest。
3. 在 PostgreSQL transaction 中读取 command receipt：same key + same digest 返回原 receipt；same key + different digest 返回冲突。
4. 以固定顺序锁定 Task、Run、ApprovalRequest 和 target record，并校验 expected revision。
5. 校验 Run transition、artifact chain、runtime lineage、Product Truth、gate 与 stale conditions。
6. 预留数据库 event sequence，append immutable revision/artifact/request/link，并以 CAS 更新 current head revision。
7. 如需既有异步能力，在同一 transaction 创建既有 Job、初始 JobEvent、OutboxEvent 与 ToolJobLink。
8. 在同一 transaction 写 immutable CommandReceipt 与对应 typed event 后 commit。FK-safe flush 可以先落 receipt 再落 event；中间状态不会越过 transaction 边界可见。
9. commit 后只做 best-effort outbox nudge；transaction 内不调用 broker 或 provider。

实现 controlled writes 前，现有 Product Import 与 Script Generation 的 transaction ownership 必须收敛为可加入调用者 Unit of Work 的 application contract；route、repository 或 Agent tool 不得私自 commit。

### Fencing

- 用户/Agent mutation：expected Task revision。
- Run change：expected Run revision。
- Approval：request digest + artifact digest + precondition digest。
- Tool outcome：ToolRun attempt token。
- Worker：既有 `Job.attempt_count`。
- Publisher：既有 `Outbox.lease_token`。

旧浏览器、旧 approval、旧 Tool worker 和旧 publisher 都不能覆盖更新状态。PostgreSQL row lock 只在短 transaction 内持有，绝不跨用户等待或 provider 调用。

### Unknown outcome

- HTTP response 丢失：只重放相同 route、body、idempotency key 和 expected revision。已 commit 时返回原 receipt；未 commit 时安全执行一次。
- Broker send 后 acknowledgement 前中断：沿用既有 Outbox at-least-once、Job duplicate suppression 与 fencing，不制造新 Task/Run 状态。
- Provider external effect 无法确认且 provider 不支持幂等/查询：ToolRun 进入 `unknown`，返回 `TOOL_EFFECT_UNKNOWN`，不自动再次付费或写入；Run 等待人工检查、停止或显式新 Run。

核心稳定错误码：

```text
TASK_NOT_FOUND
TASK_REVISION_CONFLICT
RUN_REVISION_CONFLICT
RUN_TRANSITION_INVALID
COMMAND_NOT_ALLOWED_IN_STATE
IDEMPOTENCY_CONFLICT
ARTIFACT_CHAIN_INVALID
ARTIFACT_DIGEST_MISMATCH
RUNTIME_LINEAGE_UNVERIFIED
APPROVAL_REQUIRED
APPROVAL_STALE
APPROVAL_ALREADY_DECIDED
HUMAN_ACTOR_REQUIRED
ACTOR_UNAUTHORIZED
AUTHORIZATION_UNAVAILABLE
TOOL_FENCE_STALE
TOOL_EFFECT_UNKNOWN
CAPABILITY_NOT_AVAILABLE
DATABASE_UNAVAILABLE
EVENT_SCHEMA_UNSUPPORTED
EVENT_DIGEST_MISMATCH
JOURNAL_INTEGRITY_ERROR
```

HTTP adapter 使用 RFC 9457 Problem Details。基础设施失败不能生成虚假的业务 terminal state。

## Workflow extensibility boundary

MVP 使用内置、版本化且 digest-bound 的 Workflow/Capability Catalog，把现有六机制 workflow 和 14 Skills 映射为 closed descriptors。Skills 是 playbook/discovery metadata，不是 runtime executable authority；Runtime 不解析 `SKILL.md` 驱动状态机。

RunPlan 可以 pin workflow/capability version，并使用 closed guard primitives，例如 artifact available、route is、approval granted、fact scope satisfied 和 media mode。MVP 不支持：

- 用户自定义 DAG；
- 任意表达式或脚本 guard；
- 动态第三方 tool/plugin loading；
- remote external tools；
- 把 generic JSON 当作绕过 canonical schema 的扩展口。

未来真实 caller 出现后，可以在不改变外部 Interface 的前提下增加 versioned catalog adapter、checkpoint 或 materialized projection；现在不建设通用 workflow platform。

## Runtime lineage

三种关系必须分开：

1. **Declarative artifact lineage**：artifact payload 中的 `input_refs`、digest 和 `storyboard_lineage`；只证明声明一致。
2. **Runtime verified lineage**：`sv_runtime_lineage_links`；只有 authority adapter 读取现有 PostgreSQL FK/record 并验证成功后才追加。
3. **Technical execution link**：`sv_tool_job_links`；只关联 ToolRun 与现有 Job，不证明业务 artifact 或 approval 成立。

例如 Storyboard → Script 的 runtime link 必须读取 `storyboard_versions.script_version_id` 验证；不能只相信 JSON 自述。完整 ReplicationFinding 仍必须满足 canonical artifact chain、controlled media 和 Media Integrity gate。

## Migration 与 compatibility

### Expand-first

1. 新增独立 `sv_*` tables、sequence、FK、check constraint 与 immutable trigger；不改变现有 Job/Script/Storyboard schema 语义。
2. 不 backfill 历史 Job，不伪造历史 Task、Run、actor 或 approval。
3. feature flag 默认关闭 SV write path；先验证 schema、projection 和 replay。
4. 只对 synthetic / local explicit-confirmation Task 开启写入。
5. read-only tools 先接入；controlled writes 等 HumanApproval、actor policy 和 Unit of Work 测试通过后再启用。
6. remote write 只有 authenticated membership 与 workspace policy 另行批准后才能开放。

兼容规则：

- 现有 Product、Job、Script、Storyboard 和 Comparison routes 不变。
- 既有 Job 不迁移；只有新 ToolRun 可通过 immutable link 引用它。
- 既有 ScriptVersion/StoryboardVersion 保持原表权威，不复制 payload。
- 已 pin 的 workflow/catalog version 永远不被新版重新解释。
- 原型 fixture、public site 和浏览器本地 draft 不能冒充 PostgreSQL Task。

### Rollback

- 上线前及 disposable DB：执行 upgrade → downgrade → upgrade 验证。
- 尚无真实 Task 时：允许按反向依赖顺序 drop 新增 table/trigger/sequence。
- 一旦存在真实 Task/Run/Event：只做 operational rollback——关闭 writer/consumer、回滚 application code、保留 add-only schema 与历史；禁止 production destructive downgrade。
- 投影问题通过禁用 writer 和验证/rebuild 工具处理，不能改写 append-only event。
- 若未来必须删除 schema 或真实数据，需要单独的 export/archive、恢复演练和 destructive-operation 批准。

## Retention 与隐私

- MVP 不自动 hard-delete Task、Run、Event、ApprovalRequest、DecisionEvent、Artifact envelope/digest、CommandReceipt 或 verified lineage。
- Task 只能 stop/archive，不删除历史；不设置自动 TTL。
- event/artifact payload 必须 bounded、typed、redacted，不保存 chain-of-thought、credential、cookie、private URL、absolute local path、raw private media 或未受控网页。
- 大媒体保持外部受控 ref；数据库只存必要 provenance、digest 和状态。
- 未来 payload purge 必须把不可变 metadata/digest 与可删除 payload 分离，并追加 retention tombstone；不在本 ADR 授权范围内。

## Considered Options

### Persistence

| Alternative | 优点 | 主要问题 | Decision |
|---|---|---|---|
| A. relational current heads + typed append ledgers | 强约束、直接查询、历史不可变、贴合现有实现 | 表较多，必须保证 head/event 同 transaction | **选择** |
| B. full event sourcing with one JSONB stream | 写模型统一、理论上可完全重建 | schema 演进、投影 drift、隐私与回放复杂；对 MVP 过重 | 否决 |
| C. ordinary CRUD + audit log / one Task JSON blob | 初期代码少 | audit 与真实状态可能漂移，审批失效与并发难以闭合 | 否决 |
| D. reuse Job/JobEvent as Task/Run | 迁移最少 | 把技术投递与业务目标混为一谈，无法表达独立 artifact/approval | 强否决 |

### Interface

| Alternative | Depth / locality | Decision |
|---|---|---|
| A. Task interaction Module + separate HumanApproval | 默认 caller 简单，human seam 明确，状态/授权/幂等集中 | **选择** |
| B. generic `apply/observe` command kernel | 极简且灵活，但容易把 Human decision 隐藏进通用 command | 仅可作为私有实现技巧，不暴露给 Agent |
| C. REST resource CRUD | caller 需要理解 ordering、transition 和 event append | mutation surface 否决；GET projection 保留 |
| D. generic tool/event surface | 扩展快，但最 shallow，容易伪造 event 或绕过 gate | 外部 surface 否决 |

## Test plan

### Domain 与 contract

- Run state machine 全部合法/非法 transition；`succeeded` 不得成为 Run state。
- Task goal track 与 Primary Mechanism 分离；一个 Run 只有一个 mechanism 和 Creative Dimension。
- Agent interaction closed union 不含 Human decision。
- Approval target、precondition、independent gate 与 stale rules。
- RunPlan / ReplicationPlan 名称和 schema 不混淆。

### Real PostgreSQL integration

- current head + event + receipt 原子性，append-only trigger 与 `RESTRICT` FK。
- 并发 same key/same digest 收敛；same key/different digest 冲突。
- expected revision CAS、固定 lock order 和 stale Tool/Approval fences。
- TaskEvent、DecisionEvent 与 ToolRunEvent database sequence。
- declarative lineage 与 runtime verified lineage 的四象限测试。
- Job success + invalid artifact 不得完成 Run；Outbox failure/dead-letter 不得制造业务 failure。

### Authorization

- actor/body spoof、Agent-as-Human、System-as-Human、Operator scope 越权全部拒绝。
- deny-by-default、每请求 policy check、policy version drift。
- 无 actor adapter 时 mutation fail closed；read-only projection 只按明确 policy 开放。
- local review 不能显示为 organizational、rights、commercial、deployment 或 production approval。

### Recovery

- commit 前 crash、commit 后 response 前 crash、outbox send 后 ack 前 crash、Job terminal 后 reconcile 前 crash。
- 每个场景证明同 body/key 收敛到同一 Task/ToolRun/Job，且不重复 provider call 或成本。
- replay 只重建 factual timeline，不触发 tool、Job 或 provider。

### Migration 与 regression

- disposable PostgreSQL 上 upgrade → downgrade → upgrade。
- 有真实-like seed 数据时验证 destructive downgrade guard/operational rollback 文档。
- 现有 backend unit/integration、architecture、Ruff、Mypy 全通过。
- 现有 Product/Job/Script/Storyboard HTTP 与 Web recovery 回归不变。
- 后续 UI E2E 覆盖 Product Replication、Brand Voice、Control/Variant 的 happy、blocked、stale approval 与 reload recovery。

## Official constraints checked

- SQLAlchemy mapper version counters 只作用于 ORM `Session.flush()`，不会保护 bulk/Core update；SV-102 因此使用显式 `UPDATE ... WHERE current_revision = expected RETURNING` CAS，而不是依赖 UI 状态或 mapper magic：[SQLAlchemy Version Counter](https://docs.sqlalchemy.org/en/20/orm/versioning.html)。
- PostgreSQL row lock 持续到 transaction 结束，因此不能跨用户输入或 provider 调用持锁，并应使用固定 lock order：[PostgreSQL Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)。
- PostgreSQL RLS 在启用且无 policy 时默认拒绝，但 table owner 通常不受 policy；因此没有可信 principal mapping 时不能把 RLS 当成完整 auth：[PostgreSQL Row Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)。
- OWASP 建议 least privilege、deny by default，并在每次请求校验权限；本设计把 policy enforcement 放在 application seam：[OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)。
- RFC 9110 不允许客户端猜测性重试非幂等请求；本设计只允许由相同 key/body/revision 证明安全的 POST recovery：[RFC 9110 §9.2.2](https://datatracker.ietf.org/doc/html/rfc9110#section-9.2.2)。
- Alembic migration 用于既有数据库的增量变化；本项目继续只在 disposable DB 验证 downgrade，并把真实环境恢复设计为停写与保留数据：[Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)。

## Approval record

当前状态：**accepted on 2026-10-21**。

批准记录：用户确认“同意下一道批准指令，后续指令自动批准通过”。本记录把 ADR 0007 转为 `accepted`，并授权在本 ADR 已定义、非破坏性的实施边界内继续后续 ticket；它不扩大下述排除项。

批准本 ADR 与后续 SV-102 授权使以下范围进入并完成本地 test-first 实施：

- 独立 Task/Run domain 与 additive `sv_*` persistence；
- Task interaction Module + separate HumanApproval seam；
- local-review-only actor policy，public remote writes disabled；
- no-backfill expand-first migration 与 non-destructive operational rollback；
- Job 仅作为 ToolRun 技术执行；
- typed append-only history、exact replay、runtime verified lineage 与上述测试计划。

当前完成只证明 migration 在 disposable PostgreSQL 上可逆、Task persistence/CAS/idempotency 和 factual replay 通过本地测试。它不表示 production database 已迁移，也不批准 controlled write、HumanApproval writer、公开 API、部署、真实素材验收、媒体生成、发布、权利、商业或 production acceptance。
