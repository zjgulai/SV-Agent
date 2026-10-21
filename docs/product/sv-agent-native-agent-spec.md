# SV-Agent Native Agent Specification

Status: active implementation contract; SV-101 through SV-103, bounded SV-104A/B, SV-105 and SV-201 through SV-204 complete locally
UX decision: A - Task Mission Control is selected
Batch 1 kernel status: implemented and validated in the repository baseline
Runtime status: domain kernel, Task persistence/CAS, factual replay, closed read tools,
digest-bound RunPlan compilation, pure prerequisite evaluation and pure independent next-gate
review, a public read-only Task Inbox, a browser-local New Task brief, a read-only Mission
Control and a read-only Evidence and Artifact workspace are implemented; durable RunPlan/reviewer writes,
execution orchestration and authorization runtime are not implemented
SV-005 design gate: accepted on 2026-10-21 in `docs/adr/0007-sv-agent-task-runtime-and-authorization.md`; SV-101 through SV-105 and SV-201 through SV-204 are implemented locally
Primary brand workspace: Momcozy
Companion backlog: `docs/product/sv-agent-implementation-tickets.md`

## 1. Executive decision

SV-Agent is a stateful viral-replication orchestrator built on the existing FactFrame runtime. It is not a chat wrapper, a video generator, or a social-publishing agent.

The selected product shape combines three surfaces:

- A Task Mission Control is the primary shell and authoritative navigation.
- An Evidence Graph is a secondary view for artifacts, dependencies, and evidence boundaries.
- A conversational director is a control surface for proposing typed commands. Conversation is never authoritative business state.

FactFrame remains responsible for Product Truth, immutable Script and Storyboard versions, reliable Job execution, and read-only creative comparison. SV-Agent adds durable Task and Run identity, artifact orchestration, deterministic mechanism routing, approval interrupts, and replay.

## 2. Existing capability boundary

### Reuse without reimplementation

- Product Source, Product Snapshot, Product Fact, Promotion Fact, and Fact lifecycle.
- The `confirmed` or `locked` eligibility rule for product claims.
- Script generation contracts, provider boundaries, deterministic validation, and append-only ScriptVersion.
- Storyboard preflight, immutable StoryboardVersion, preview, and human approval events.
- PostgreSQL Job, JobEvent, Outbox, Celery transport, reconciliation, leasing, and attempt fencing.
- Creative Comparison Lab read-only projection and Difference Ledger.
- Six viral-replication mechanism workflows and the cross-cutting Media Integrity gates.

### Add in SV-Agent

- Durable Task, Run, RunPlan, ToolRun, ArtifactRef, ApprovalRequest, and DecisionEvent concepts.
- Runtime forms of ReferenceBundle, DecompositionMap, PatternHypothesis, ReplicationPlan, FactMap, ReplicationContract, AdaptationPackage, MediaIntegrityRecord, and ReplicationFinding.
- Deterministic routing to exactly one Primary Replication Mechanism.
- Typed tools that wrap application services rather than repositories or Celery.
- A version-bound HumanApproval interface.
- A replay projection that exposes inputs, typed outputs, factual state, errors, and decisions without private model reasoning.

### Explicitly out of scope

- RenderJob, video generation, keyframe generation as a production capability, or final-media creation.
- Account connection, social upload, publishing, ranking, billing, or checkout.
- Automatic Fact confirmation or locking.
- Automatic rights, originality, commercial, legal, platform, deployment, or production approval.
- Winner scoring, causal lift, or automatic promotion of Performance or Experiment evidence into Product Truth.

## 3. Goals and success conditions

SV-Agent must let a user start from a bounded reference and reach a review-ready replication package without losing evidence provenance or bypassing human decisions.

The MVP succeeds when:

1. A Task can be resumed after browser or worker interruption.
2. Every Task has a goal track, decision question, subject, platform, market, language, window, and stop condition.
3. Every replication Run selects exactly one Primary Mechanism and one Creative Dimension, or stops with a stable blocker.
4. Every product claim resolves to an eligible Fact from one Product Snapshot.
5. Every write tool declares impact and requires the applicable approval.
6. Every artifact is versioned, digest-bound, and traceable to its inputs.
7. Every unknown or unavailable value preserves its closed meaning and is never displayed as zero.
8. Replay reconstructs actions and decisions but never stores or exposes chain-of-thought.
9. The UI never presents Render, Publish, Ship, or Commercial Approval as available capabilities.

## 4. Product information architecture

```text
SV-Agent
|-- Task / Decision Inbox
|   |-- Needs my decision
|   |-- Agent running
|   |-- Blocked
|   `-- Completed with limits / Stopped
|-- New Task
|   |-- Product Replication
|   `-- Brand Voice / Social Resonance
|-- Task Workspace
|   |-- Overview and Decision Brief
|   |-- Plan
|   |-- Activity and Tool Runs
|   |-- Artifacts
|   |-- Evidence
|   |-- Approvals
|   `-- Replay
|-- Product Truth
|-- Playbooks
|   |-- Skills
|   |-- Workflows
|   `-- Cases
`-- Connections and Policies
```

Brand Voice / Social Resonance is a goal track. It does not become a seventh Primary Mechanism.

## 5. Deep modules and seams

| Module | Narrow interface | Hidden complexity | Initial source |
|---|---|---|---|
| `SVRuntime` | `engage`, `inspect` | task identity, planning, state transitions, idempotency, recovery, replay | new |
| `HumanApproval` | `decide` | verified human actor, version-bound decision, stale detection, independent gates | new |
| `ReferenceIntelligence` | `intake_reference`, `decompose_reference` | source identity, digest, window, rights state, timed observations | workflow to runtime |
| `ReplicationPlanner` | `route_mechanism`, `compile_plan`, `freeze_contract` | six-way routing, single-variable isolation, stop conditions | workflow to runtime |
| `ProductTruthWorkspace` | `read_truth`, `propose_fact_review` | Snapshot and Fact lifecycle, evidence kind, immutability | existing services |
| `ScriptWorkshop` | `queue_generation`, `derive_fact_rebind`, `read_version` | provider boundary, Fact selection, deny-set, deterministic validation | existing services |
| `StoryboardReview` | `preflight`, `create_review_object`, `request_decision` | live Fact recheck, digest, stale approval, immutable versions | existing services |
| `ExecutionJournal` | `get_status`, `get_timeline` | Job, Outbox, broker transport, retry leases, fencing | existing services |
| `EvidenceAndMediaIntegrity` | `read_evidence`, `audit_artifact` | four evidence planes, missing semantics, six independent media gates | partial contract |
| `CreativeComparisonLab` | `inspect` | shared Fact observation, deterministic difference classification | existing read-only service |

Repositories, database sessions, Redis, and Celery are implementation details and must not become Agent tools.

## 6. Canonical artifact chain

```text
ReferenceBundle
  -> DecompositionMap
  -> PatternHypothesis
  -> ReplicationPlan
  -> FactMap
  -> immutable ReplicationContract
  -> AdaptationPackage
  -> ScriptVersion
  -> StoryboardVersion
  -> MediaIntegrityRecord
  -> ReplicationFinding
```

`ReplicationPlan` is editable and can be revised before approval. `ReplicationContract` is the normalized, digest-bound, immutable result of the mechanism, Product Truth, rights, configuration, and single-variable gates.

Every artifact carries at least:

```text
artifact_id
artifact_type
task_ref
run_ref
version
status
input_refs[]
subject_binding
source_refs[]
content_digest
evidence_level: fact | inference | unknown
proof_level: local | ci | private | deployment | live | production
limitations[]
created_at
supersedes_artifact_id?
```

Artifact statuses are `draft`, `validated`, `awaiting_approval`, `blocked`, `approved`, `stale`, `superseded`, and `final_with_limits`. Artifact status does not replace Run, ToolRun, Approval, or evidence status.

The executable machine-schema authority for the nine new artifacts is
`apps/api/app/domain/sv_agent/artifact_contracts.py`. The historical
`tools/viral_replication/artifact_contracts.py` import is a compatibility export to that same
implementation, so offline fixtures and the deployable API cannot drift into two schema copies.
SV-102 added the immutable `sv_artifacts` envelope table without an Artifact writer. SV-204 moves
the pure validator into the deployable domain only so the read-only workspace can reject malformed
persisted rows; it still adds no writer. A future writer must call the same closed validator before
persistence. Every canonical artifact still requires non-empty `task_ref` and `run_ref`; local
fixtures may use bounded synthetic refs, but those refs do not prove that a persisted artifact or
runnable orchestration exists.

DecompositionMap carries a closed, mechanism-discriminated `mechanism_observations` union for narrative beats, proof steps, experience cues, timed attention observations, conversion components, and trend components. A concrete `primary_mechanism` requires the matching branch; an ambiguous `primary_mechanism=null` requires `mechanism_observations=null` and must stop or split into Variants. Conversion and trend branches close their full component partitions and preserve explicit source-surface or source-reuse boundaries. This schema records bounded observations; it does not authorize source reuse, platform execution, or media generation.

The standard completed chain contains both ScriptVersion and StoryboardVersion before MediaIntegrityRecord. An early bounded `preflight` may bind one or both typed version references; with only one ref, `storyboard_lineage=null`, while two refs require the exact lineage described below. That partial record does not close the completed chain, authorize ReplicationFinding, or imply render, publish, rights, commercial, or production approval. Whenever both refs are present, `storyboard_lineage` is required and must contain the exact `storyboard_version_ref`, its declared `source_script_version_ref`, and `evidence_scope=declared_artifact_lineage`. `artifact_review` additionally requires a controlled media artifact and therefore requires both refs plus this lineage. A completed ReplicationFinding rechecks the same lineage. This is a declarative artifact-lineage contract, not proof of runtime database derivation.

FactMap and ReplicationContract use the executable closed discriminator `claim_scope = product_claims | no_product_claims`; it is not a common-envelope field. `product_claims` requires an exact or reviewed Product Snapshot binding and eligible selected Facts. `no_product_claims` is limited to Brand Voice / Social Resonance artifacts with no product claim: `subject_binding.state=not_applicable`, snapshot identity absent, and claim mappings plus selected, excluded, and unsupported Fact/claim sets empty. A product claim always restores Product Snapshot and Fact binding. The local validator enforces scope, subject binding, Fact-set rules, and FactMap-to-ReplicationContract consistency; this still does not create runtime persistence or a business approval.

## 7. Run state machine

```text
draft
  -> planning
planning
  -> awaiting_input | runnable | blocked | stopped
runnable
  -> running
running
  -> awaiting_input | awaiting_approval | blocked
  -> completed_with_limits | failed | stopped
awaiting_input
  -> planning | stopped
awaiting_approval
  -> running | planning | blocked | stopped
blocked
  -> planning | stopped
failed
  -> planning | stopped
```

State meanings:

- `draft`: the user has not completed the minimum Task brief.
- `planning`: SV-Agent is validating scope and compiling a typed RunPlan.
- `awaiting_input`: required user input is missing; no guessing is allowed.
- `runnable`: the plan and required pre-execution approvals are complete.
- `running`: one or more typed read or approved write tools are active.
- `awaiting_approval`: an immutable version-bound ApprovalRequest is open.
- `blocked`: a stable business or evidence blocker prevents legal progress.
- `completed_with_limits`: the requested review-ready deliverable exists with explicit limitations.
- `failed`: execution ended because of a technical terminal failure; this is not a business rejection.
- `stopped`: the user or an applicable stop condition ended the Run.

`succeeded` is deliberately not a Run state because technical completion must not be confused with commercial, publishing, deployment, or production acceptance.

SV-101 implements this graph in `app.domain.sv_agent` as immutable Task/Run values. `RunStateSemantics` classifies orchestration, business disposition, approval pause, and technical terminal meanings without treating Job, Artifact, or Approval state as Run authority. A Run cannot become `runnable` before one closed Primary Mechanism / Creative Dimension pair is selected. This is a domain contract only: it creates no database row, API route, worker action, approval authority, or external side effect.

## 8. External Agent interface

SV-005 selects a Task interaction Module plus an independent Human Approval seam:

```text
SVRuntime.engage(StartTask | ContinueTask, AuthorizedCall) -> TaskTurn
SVRuntime.inspect(task_id, AuthorizedViewer) -> TaskWorkspaceProjection
HumanApproval.decide(HumanDecisionCommand, VerifiedHumanCall) -> TaskTurn
```

`ContinueTask.intent` is a closed union:

```text
provide_input
request_plan
request_evidence
revise_plan
advance
resume_recovery
stop
```

Human `approve`, `reject`, `request_evidence`, and `stop` decisions do not appear in the Agent interaction union. An Agent may request a decision or return a reviewer recommendation, but it cannot obtain the `VerifiedHumanCall` required by `HumanApproval.decide`.

Free-form conversation must compile into one of the allowed interactions. Before execution, the UI shows the compiled intent, affected Task or artifact version, expected side effects, and required approval. Actor, role, workspace, authority, and input digest are server-derived; they are never trusted from the request body.

## 9. HTTP contract proposal

These routes are a proposed application boundary, not an authorization to add migrations or expose public write endpoints.

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

Mutating commands require an idempotency key, verified actor attribution, expected Task revision, and typed payload. Unknown write outcomes may only resume the original command with the same route, body, key, and revision. REST is a transport adapter; it cannot expose generic status patches or client-authored events.

## 10. Tool catalog policy

### Read tools

- Product and Product Truth inspection.
- Pattern contract inspection.
- Job status, events, and import attempts.
- Script, ScriptVersion, diff, and export inspection.
- Storyboard preflight, preview, and approval-state inspection.
- Creative Comparison inspection.

The implemented SV-103 registry freezes these groups as six internal `1.0.0` tool names:

| Tool | Closed read actions |
|---|---|
| `product_truth.inspect` | one Product Snapshot and its Product Facts |
| `pattern_contract.inspect` | one exact key/version/duration/language/audience contract |
| `job.inspect` | status, optional events, optional Product Import attempts |
| `script.inspect` | `inspect`, `version`, `diff`, `export` |
| `storyboard.inspect` | `preflight`, `preview`, `approval_state` |
| `creative_comparison.inspect` | one Control/Variant projection |

Each input and output rejects extra fields. A missing referenced subject is a typed
`not_found` result that carries the queried subject reference on a technically completed
read; a disabled or absent registered adapter is `ToolRun.unavailable`. Neither state may be
inferred from an empty collection or from missing Performance, Experiment, or Asset evidence.
Job event/import-attempt and Script-version collections default to 100 and are capped at 200
items. Job projections expose stable error codes but do not expose provider `error_detail`.
Export is an in-memory projection and does not write a file or create an Artifact. The
registry is internal: SV-103 does not expose an HTTP route or authorize writes.

### Write tools requiring explicit approval

- Public Schema.org Product import.
- Manual Fact proposal as `user_assertion/manual-form`.
- Script generation queueing.
- Fact-rebind derived ScriptVersion.
- Storyboard review-object creation.

### Human-only or independently governed gates

- Fact confirmation or locking.
- ReplicationContract acceptance.
- Storyboard approve or reject.
- Reference rights and child-safety decision.
- Source-use, originality, legal, commercial, platform, deployment, or production approval.
- Outbox dead-letter retry.
- Any future render, paid generation, upload, or publish action.

ToolRun records include:

```text
tool_run_id
tool_name
tool_version
task_id
run_id
intent_summary
input_digest
read_or_write
approval_request_id?
idempotency_key?
status
artifact_refs[]
stable_error_code?
recovery_action?
started_at
finished_at?
```

For the SV-103 synchronous read seam, the caller owns the database transaction. Each
accepted invocation records CREATED, STARTED, and exactly one terminal ToolRun event in the
same transaction. Successful terminal events retain a server-derived digest of the typed
output; the full output is not copied into the event ledger. Current-head transitions compare
the expected revision, prior status, and attempt token. The seam does not yet provide
command-receipt replay: retrying is a new logical read invocation. SV-104A/B proves only
computationally repeatable plan compilation and evaluation; durable resume still requires a
Run/RunPlan writer plus command-receipt integration.

## 11. Human approval contract

An ApprovalRequest is immutable and binds:

- the exact Task and Run revision;
- the artifact type, ID, version, and digest;
- the requested decision;
- the predicted effects and non-effects;
- the evidence summary and limitations;
- the conditions that make approval stale.

Allowed decisions are `approve`, `reject`, `request_evidence`, and `stop`. An Agent reviewer can recommend a decision but cannot create a human ApprovalEvent.

One ApprovalRequest accepts at most one Human DecisionEvent. `request_evidence` closes that request; changed evidence requires a new request bound to a new precondition digest. Task revision conflict requires a refresh, while semantic staleness is derived only from the target artifact and the request's declared stale dependencies.

Fact, Contract, Storyboard, rights, Media Integrity, commercial, deployment, and production approvals remain separate gates.

## 12. Selected five-screen UX

1. **Task / Decision Inbox**: orders waiting decisions, running Tasks, blockers, and completed-with-limits Tasks by impact.
2. **New Task**: captures goal track, decision question, reference, subject, platform, market, language, window, stop condition, and initial rights state.
3. **Mission Control**: shows the seven-stage path, current Plan, current artifact, next safe action, Agent activity, and conversational command surface.
4. **Evidence and Artifacts**: combines the artifact dependency graph with Product Truth, Performance, Experiment, and Asset evidence planes.
5. **Approval and Replay**: shows version-bound decisions, predicted effects, evidence, stale conditions, and the factual Run timeline.

Control and Variant comparison opens from Screens 4 and 5. Playbooks and cases are contextual resources, not the execution system of record.

## 13. Failure and recovery rules

- A missing input returns `awaiting_input` with a field-level requirement.
- Multiple inseparable mechanisms return `primary_mechanism_ambiguous` and propose splitting into two Variants.
- Unsupported or excluded product claims return `product_fact_ineligible`.
- Changed input digests make downstream approvals `stale`.
- Unknown writes retain the same body and idempotency key for recovery.
- Provider or broker outages do not manufacture new business state.
- Tool unavailability remains distinct from negative evidence.
- Technical failure cannot be shown as business rejection, and technical success cannot be shown as commercial approval.

## 14. Security and authority gates

The current application does not provide a complete user, tenant, RBAC, and actor-attribution boundary for autonomous mutating tools. ADR 0007 has accepted a local-review-only actor policy, separate Human Approval seam, deny-by-default application authorization, and additive PostgreSQL ledger. SV-102 implements the ledger schema plus an internal, flush-only Task repository for create/revise/get and factual replay; SV-103 adds only the internal synchronous read ToolRun journal. SV-104A/B adds a pure, built-in six-route planner and prerequisite evaluator without a writer or dispatcher. SV-105 adds only a pure independent next-gate reviewer; it does not persist a review or create an ApprovalEvent. `ActorStamp` is stored attribution only; it is not a verified identity or authorization adapter. Human Approval, Run/Artifact/RunPlan/reviewer writers, non-read ToolRun execution, persisted execution orchestration and public mutation remain inactive until their later tickets are implemented and validated. Until then:

- SV-Agent write tools remain local or explicitly user-confirmed.
- No public remote write surface is enabled.
- Approval events cannot claim authenticated organizational authority.
- Private asset identifiers, absolute local paths, credentials, cookies, private URLs, and raw private media never enter tracked artifacts or replay.

No historical Job may be backfilled into a synthetic Task. The approved additive schema and reversible local migration now exist; authenticated membership, remote write surfaces, verified actor adapters and every controlled writer remain blocked behind their later approval and test gates.

## 15. P0 consistency fixes before runtime work

1. Normalize `ReplicationPlan -> ReplicationContract -> AdaptationPackage` across the context and six mechanism SOPs.
2. Define one shared AdaptationPackage schema with a typed mechanism payload.
3. Add Media Integrity to every mechanism skill-map so no documented path can bypass it.
4. Add missing Agent discovery metadata for attention, conversion, trend, and media-integrity Skills.
5. Add a deterministic fixture oracle for all six routes, stable blockers, and allowed `proceed_with_limits` outcomes.

## 16. Delivery phases

### Phase 0 - Contract normalization

Exit gate: canonical artifacts, route contract, fixture oracle, and documentation agree.

### Phase 1 - Read-only Native Shell

Exit gate: the five screens render real read projections from existing services; no browser-local data is presented as authoritative.

### Phase 2 - Durable Run and approvals

Entry gate: ADR 0007 is explicitly accepted. Exit gate: approved Task/Run schema, append-only events, local-review-only actor attribution, idempotency, recovery, runtime lineage, and version-bound ApprovalRequest integration tests pass.

Current checkpoint: SV-104A/B adds a closed `sv-run-plan/v1` value, six-mechanism static
catalog, evidence-bound unique/ambiguous route handling and a pure prerequisite evaluator on
top of SV-103. SV-105 adds deterministic independent checks for artifact digest/scope, actual
single-variable isolation, visible-surface deny-set and Product Truth evidence bound to the same
Product Snapshot and Fact identity. SV-201 adds the
first public read-only Native Shell surface: a PostgreSQL-authoritative, bounded and reasoned
Task Inbox that verifies the current TaskBrief, active Run revision scope and complete Approval
decision handle, plus a visibly separate browser-draft section. SV-202 adds a complete, bounded and
resumable browser-local New Task brief with explicit rights and child-safety acknowledgements.
SV-203 adds a read-only Mission Control projection and route. It binds to the current PostgreSQL
Task/Run head and brief digest, and shows only unique validated Plan and canonical,
runtime-lineage-verified Artifact frontiers,
keeps unsupported stages unknown, and offers an in-memory command preview with explicit
non-effects. It does not create PostgreSQL Tasks, persist or execute a plan, resume a durable
command, dispatch a Tool, decide an ApprovalRequest or expose any public write. SV-204 adds the
bounded read-only `GET /api/v1/sv-agent/tasks/{task_id}/artifacts` projection and
`/sv-agent/tasks/:taskId/evidence` workspace. It validates canonical artifact envelopes, full-chain
semantics and graph integrity across the active Run's revisions, separates Product Truth,
Performance, Experiment and
Asset missing semantics, and refuses Control/Variant binding until typed immutable ScriptVersion
roles exist. Approval/Replay plus the remaining runtime capabilities still prevent this phase from
reaching its exit gate.

### Phase 3 - Controlled writes

Exit gate: approved write tools wrap application services, never repositories, and have happy, blocked, unknown-outcome, stale-approval, and recovery tests.

### Phase 4 - Media artifact review

Exit gate: controlled artifacts support provenance and all six Media Integrity gates. This phase does not authorize generation or publishing.

## 17. Verification strategy

- Unit tests for mechanism routing, artifact normalization, transition rules, missing-value semantics, and command compilation.
- Contract tests for every read and write tool.
- Integration tests for Task persistence, event ordering, approval staleness, idempotency, and recovery.
- E2E tests for Product Replication, Brand Voice, and Control/Variant review.
- Each E2E scenario covers happy, blocked, recovery, and human-approval paths.
- Architecture tests continue to prevent domain and application layers from importing adapters.
- Public-site and prototype fixtures remain demonstrations and cannot substitute for PostgreSQL runtime tests.

## 18. Decisions still requiring explicit approval

- Any authenticated membership, workspace ownership, remote write surface, organization-level authorization or PostgreSQL RLS model beyond that local MVP.
- Which reference connectors are allowed and what media is persisted.
- ProviderRun cost and attempt ledger.
- Whether future controlled media analysis runs locally or through a remote provider.
- Any RenderJob, video generation, publishing, billing, causal attribution, or production-acceptance scope.
