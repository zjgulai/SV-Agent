# SV-Agent Implementation Tickets

Status: Batch 1, SV-101 through SV-103 and bounded SV-104A/B are complete and validated locally; SV-005 is accepted; Git, remote CI, deployment and production status must be verified independently
Architecture authority: `docs/product/sv-agent-native-agent-spec.md`
Runtime implementation includes the domain kernel, internal persistence/read seams and pure planning/evaluation; public writes, durable plan execution and authorization remain inactive.

## Delivery rules

- Work on `main`; do not create a worktree.
- Preserve unrelated dirty changes.
- Follow test-first implementation.
- Do not add a migration, backfill, destructive data operation, authentication model, or public write route without explicit approval.
- Every ticket must preserve Product Truth authority, immutable versions, missing-value semantics, and independent approvals.
- A ticket is complete only when its acceptance criteria and the relevant checks in `docs/development/testing.md` pass.

## Dependency map

```text
SV-001 -> SV-002 -> SV-003 -> SV-004
                    |          |
                    `------> SV-005

SV-005 -> approval of schema and auth design
       -> SV-101 -> SV-102 -> SV-103 -> SV-104
                                |          |
                                `------> SV-105

SV-102 -> SV-201 -> SV-202 -> SV-203 -> SV-204 -> SV-205
SV-104 -> SV-301 -> SV-302 -> SV-303
SV-105 -----------------------> SV-303
```

## Epic 0 - Normalize the product kernel

### SV-001 - Canonical artifact schemas

Priority: P0
Status: completed locally in Batch 1
Scope: define machine-readable schemas for ReferenceBundle, DecompositionMap, PatternHypothesis, ReplicationPlan, FactMap, ReplicationContract, AdaptationPackage, MediaIntegrityRecord, and ReplicationFinding.

Acceptance:

- Every schema has version, digest, input refs, subject binding, evidence level, proof level, limitations, and closed status values.
- AdaptationPackage has a shared envelope and exactly one typed mechanism payload.
- FactMap and ReplicationContract use the same closed `claim_scope = product_claims | no_product_claims`; no-product scope requires `subject_binding.state=not_applicable` and empty snapshot, claim, selected/excluded Fact, and unsupported-claim sets.
- Unknown, not reported, not collected, source ambiguous, unavailable, quarantined, and an observed numeric zero remain distinct; zero remains `state=observed` rather than a separate invented state.
- Schema validation has positive and adversarial tests.

Validation: 32 positive and adversarial tests pass; Ruff format/check and explicit-package Mypy pass. The validator covers closed six-mechanism decomposition observations, Task/Run-scoped refs, cross-artifact digests and lineage, same-Snapshot Promotion binding, provider exclusion evidence, claim scope, frozen configuration, and Media Integrity state consistency.

### SV-002 - Normalize workflow order and gates

Priority: P0
Depends on: SV-001
Status: completed locally in Batch 1

Acceptance:

- Context, six SOPs, workflow README, and skill maps agree on `ReplicationPlan -> FactMap -> ReplicationContract -> AdaptationPackage`.
- Media Integrity appears in every mechanism path.
- Multiple inseparable mechanisms return `primary_mechanism_ambiguous` and recommend two Variants.
- No path claims render, publish, rights, commercial, or production approval.

Validation: the context, workflow README, shared contracts, six SOPs, six skill maps, live Skill guidance, and Media Integrity SOP use the same canonical chain and gate boundaries. Twelve SOP/map route files pass the static order and Media Integrity check.

### SV-003 - Complete Agent Skill metadata

Priority: P0
Depends on: SV-002
Status: completed locally in Batch 1

Acceptance:

- Attention, conversion, trend, and media-integrity Skills have valid Agent discovery metadata.
- All viral Skills pass the project Skill validator.
- Metadata describes capabilities without overstating runtime or media-generation support.

Validation: all 14 viral Skills pass the project `quick_validate.py` validator; the four Batch 1 discovery metadata files explicitly invoke their matching Skill and preserve runtime/media limitations.

### SV-004 - Deterministic fixture oracle

Priority: P0
Depends on: SV-002
Status: completed locally in Batch 1

Acceptance:

- One runner evaluates every adversarial fixture.
- Expected `blocked`, `proceed_with_limits`, and stable failure codes are asserted.
- All six mechanism routes have positive, ambiguous, and blocked fixtures.
- Narrative and experience routes receive dedicated forward tests.
- CI output distinguishes schema validity from workflow correctness.

Validation: 13 oracle tests pass; 26/26 committed fixture files are readable and fixture-shape valid, 43/43 workflow expectations pass, and all six mechanisms cover positive, ambiguous, and blocked cases. CI and testing docs report canonical artifact validation, fixture-shape validation, and workflow expectation coverage as separate evidence layers.

### SV-005 - Task runtime and authorization ADR

Priority: P0
Depends on: SV-001, SV-004
Status: accepted on 2026-10-21; SV-101 authorized

Deliverable: an approved design for Task, Run, Artifact, ToolRun, ApprovalRequest, DecisionEvent, actor attribution, authorization, migration, rollback, and recovery. The accepted decision is [`ADR 0007`](../adr/0007-sv-agent-task-runtime-and-authorization.md).

Acceptance:

- Compares at least three persistence and interface alternatives.
- Defines business authority and append-only boundaries.
- Includes migration, rollback, compatibility, retention, and test plans.
- Explicit approval is recorded before SV-101 begins.

Current gate result:

- Selected persistence: relational current heads plus typed append-only ledgers.
- Selected interface: `SVRuntime.engage` / `inspect` plus independent `HumanApproval.decide`.
- Selected actor scope: local-review-only Human, internal Agent/System, and separate deployment Operator; public remote writes remain disabled.
- Selected migration strategy: additive, no historical Job backfill, feature-off first, non-destructive operational rollback after real writes.
- This design gate did not itself execute schema/migration work. The later explicit Batch 3 authorization opened SV-102 only; write routes, actor runtime, deployment, render, publish, rights, commercial, and production approval remain outside the gate.

## Epic 1 - Durable Agent runtime

### SV-101 - Task and Run domain model

Priority: P1
Depends on: approved SV-005
Status: completed locally on 2026-10-21

Acceptance:

- Implements the specified Run state machine with invalid-transition tests.
- Task goal track is separate from Primary Mechanism.
- Technical terminal state is separate from business and approval states.
- No domain import depends on database, web, broker, or model-provider adapters.

Implementation result:

- Immutable `TaskBrief`, `Task`, and revision-pinned `Run` values live in `app.domain.sv_agent`.
- The 10-state graph closes exactly 22 legal transitions and rejects every unspecified transition.
- Two Goal Tracks remain independent from the six Primary Mechanisms; all 16 mechanism / Creative Dimension pairs use one closed partition, and a Run cannot replace its selected pair.
- State semantics explicitly separate orchestration, business disposition, approval pause, and technical terminal meanings; `succeeded` is not a Run state.
- A dedicated AST architecture test rejects database, web, broker, worker, and model-provider dependencies from this domain package.
- This ticket adds no schema, migration, repository, route, worker, ToolRun, Approval runtime, deployment, render, publish, rights, commercial, or production capability.

### SV-102 - Persistence and event journal

Priority: P1
Depends on: SV-101
Status: completed locally on 2026-10-21

Acceptance:

- Approved migrations are reversible and have integration tests.
- Task revision uses optimistic concurrency.
- Run, ToolRun, ArtifactRef, ApprovalRequest, and DecisionEvent retain immutable history.
- Replay can rebuild the factual timeline without model private reasoning.

Implementation result:

- `0012_sv_agent_persistence` adds exactly 13 isolated `sv_*` tables, one shared runtime event sequence, append-only history triggers, current-head guards and `RESTRICT` relationships without backfill or changes to existing business-table semantics.
- The internal flush-only repository implements Task create/revise/get, server-scoped command receipts, same-digest replay, different-digest conflict and explicit `UPDATE ... WHERE current_revision = expected RETURNING` compare-and-swap.
- Factual replay merges Task, ToolRun and Decision streams by the shared sequence, fixes a snapshot boundary for pagination, verifies canonical digests and fails closed on unsupported event types or private reasoning fields.
- Real PostgreSQL tests cover atomic Task head/revision/event/receipt writes, idempotency, stale/missing Task separation, append-only guards, payload ceilings, three-stream ordering and stable replay pagination. Separate committed multi-connection tests prove same-command convergence and exactly-one Task CAS winner.
- Disposable migration validation passes `0011 -> 0012 -> 0011 -> 0012`; each upgraded state contains 13 tables, 13 business triggers and one runtime sequence, while the downgraded state contains none of those SV objects.
- This ticket exposes no HTTP route, verified actor adapter, HumanApproval writer, Run/ToolRun/Artifact writer, planner, provider action, deployment, render, publish, rights, commercial or production capability.

### SV-103 - Read-only tool registry

Priority: P1
Depends on: SV-102
Status: completed locally on 2026-10-21

Acceptance:

- Tools wrap application services or HTTP contracts, never repositories or Celery.
- Product, Job, Script, Storyboard, and Comparison reads have typed input/output contracts.
- Every ToolRun records intent summary, input digest, status, artifact refs, errors, and recovery action.
- Unavailable tools remain distinct from negative evidence.

Implementation result:

- A static `1.0.0` registry exposes exactly six closed read capabilities:
  `product_truth.inspect`, `pattern_contract.inspect`, `job.inspect`,
  `script.inspect`, `storyboard.inspect`, and `creative_comparison.inspect`.
  Every command and result is a frozen, `extra=forbid` typed contract; unknown names,
  dynamic plugins, remote tools, and generic extension payloads fail closed.
- Job, Script, and Storyboard query facades now keep repository access behind application
  services. The registry and tool handler import neither persistence adapters nor workers;
  they call Product, Pattern, Job, Script, Storyboard, and Creative Comparison application
  seams only.
- Script inspection has closed `inspect`, `version`, `diff`, and in-memory `export` actions.
  Storyboard inspection has closed `preflight`, `preview`, and `approval_state` actions.
  None creates a ScriptVersion, StoryboardVersion, Job, Outbox event, provider call, file, or
  approval decision.
- The internal flush-only ToolRun journal records `pending -> running ->
  completed|failed|unavailable` as current-head revisions plus append-only factual events.
  Tool intent and server-derived input digest are immutable; terminal updates are revision
  fenced against the expected revision, prior status, and attempt token. Task then Run are
  locked in a fixed order when the ToolRun is created. A successful terminal event stores a
  server-derived digest of the typed output, without persisting the full result in the ledger.
  Negative evidence such as a missing subject completes with a typed `not_found` result that
  retains the queried subject reference, while an uninstalled/disabled adapter terminates as
  technical `unavailable`.
- Job events/import attempts and Script version collections are explicitly bounded to 1-200
  items per call. Job projections expose stable error codes but omit provider `error_detail`.
  Real PostgreSQL tests exercise every found read action, completed negative evidence,
  technical unavailability, safe failure, the prior-state CAS fence, output digests, and prove
  that the reads leave Product, Job, Outbox, Script, and Storyboard business rows unchanged.
- The caller still owns transaction commit and rollback. SV-103 adds no public SV-Agent
  route, command receipt/idempotent resume contract, Run writer, planner/orchestrator,
  HumanApproval writer, Job/Outbox/Celery integration, remote tool, render, generation,
  publishing, deployment, rights, commercial, or production authority.

### SV-104 - Planner and orchestrator

Priority: P1
Depends on: SV-103
Status: SV-104A/B pure planning implementation completed locally on 2026-10-21;
repository acceptance and durable orchestration are separate gates

Acceptance:

- Planner compiles a typed RunPlan from the Task brief.
- Orchestrator advances only when artifact and approval prerequisites are satisfied.
- Routing is deterministic for unique mechanisms and stable-blocking for ambiguous mechanisms.
- Resume is idempotent and does not duplicate writes or cost.

SV-104A/B implementation result:

- A closed `sv-run-plan/v1` contract pins Task/Run revisions, TaskBrief digest,
  workflow/catalog version and digest, exact route and FactScope evidence, ordered steps,
  five typed guard primitives, limitations and a canonical server-derived digest. It
  remains distinct from the creative `ReplicationPlan`.
- The static `1.0.0` catalog covers exactly six Primary Mechanisms and their existing closed
  Creative Dimension sets. It never parses Skill files or loads dynamic workflows.
- The planner accepts lineage-verified DecompositionMap handles and an explicit FactScope
  evidence handle; Brand Voice does not imply the absence of product claims. Zero candidates return
  `primary_mechanism_required`; exactly one compiles a plan; multiple candidates return
  `primary_mechanism_ambiguous` without changing the Run.
- Planner validation is staged before route cardinality: Task/Run lifecycle, immutable catalog,
  FactScope lineage/Goal Track compatibility and every candidate scope must be valid before a
  missing or ambiguous route disposition can be returned. Product Replication cannot use the
  closed no-claims projection; that projection requires `not_applicable` subject binding and zero
  claim mappings/facts.
- The pure evaluator rejects cross-Task/Run snapshots, conflicting artifact or approval
  projections, non-prefix completion and ApprovalRequest binding drift. Approval guards bind
  the request digest, Task/Run revisions, artifact identity/digest and precondition digest;
  only a unique, non-stale `VERIFIED_HUMAN` projection can satisfy one. The projection is a
  closed internal value, not proof that the still-deferred trusted HumanApproval adapter exists.
  Stable priority is `blocked > awaiting_approval > awaiting_input > ready`.
- Equal in-memory inputs produce equal plans, digests and decisions with no database write,
  Tool dispatch or cost. This is computational idempotency only. Run/RunPlan persistence,
  command receipts, concurrent exactly-once behavior, state advancement and recovery remain
  open work before the full SV-104 acceptance can be claimed.

### SV-105 - Independent reviewer

Priority: P1
Depends on: SV-103

Acceptance:

- Recomputes artifact digests and validates single-variable isolation, deny-set, and evidence boundaries.
- Returns only `blocked`, `proceed_with_limits`, or `ready_for_next_gate` plus typed findings.
- Reviewer recommendations cannot create human ApprovalEvents.

## Epic 2 - A-direction Agent UX

### SV-201 - Task and Decision Inbox

Priority: P1
Depends on: SV-102

Acceptance:

- Shows waiting decisions, running Tasks, blockers, completed-with-limits, and stopped Tasks.
- Ordering reason is visible.
- Browser-local drafts are clearly separated from persisted Tasks.
- No unavailable Render, Publish, or Ship action appears.

### SV-202 - New Task brief

Priority: P1
Depends on: SV-201

Acceptance:

- Captures goal track, question, reference, subject, platform, market, language, window, stop condition, and initial rights state.
- Brand Voice does not require Product Snapshot until a product claim is introduced.
- Rights and child-safety boundaries are explicit and cannot be auto-approved.
- Creating a draft does not trigger providers or write tools.

### SV-203 - Mission Control

Priority: P1
Depends on: SV-202, SV-104

Acceptance:

- Displays current stage, Run state, Plan, blockers, next safe action, ToolRuns, and current artifact.
- Conversational input previews the compiled AgentCommand and side effects.
- Agent explanations cite artifact and evidence refs rather than private reasoning.
- Reload resumes from authoritative PostgreSQL state.

### SV-204 - Evidence and Artifact workspace

Priority: P1
Depends on: SV-203

Acceptance:

- Displays the canonical artifact dependency graph.
- Product Truth, Performance, Experiment, and Asset evidence remain separate.
- Each conclusion can open source, subject, window, limitation, and proof-level details.
- Control and Variant comparison uses immutable version refs.

### SV-205 - Approval and Replay workspace

Priority: P1
Depends on: SV-204

Acceptance:

- Approval cards show target version, effects, non-effects, evidence, limitations, and stale conditions.
- Decisions are `approve`, `reject`, `request_evidence`, or `stop`.
- Replay orders Plan revisions, ToolRuns, artifacts, approvals, and decisions.
- Raw UUIDs, digests, and JSON are hidden by default but available in audit details.

## Epic 3 - Controlled writes and recovery

### SV-301 - Version-bound HumanApproval service

Priority: P1
Depends on: SV-104, approved actor model

Acceptance:

- Every ApprovalRequest binds exact artifact identity, version, and digest.
- Input changes make affected approvals stale.
- Agent recommendations cannot impersonate a human actor.
- Fact, Contract, Storyboard, rights, Media, and commercial gates remain independent.

### SV-302 - Approved write-tool adapters

Priority: P1
Depends on: SV-301

Acceptance:

- Initial adapters are limited to public Product import, manual Fact proposal, Script queueing, Fact rebind, and Storyboard review-object creation.
- Each command has actor, approval, expected revision, typed body, and idempotency key.
- Unknown outcomes resume the original request and never create a silent duplicate.
- Provider cost remains blocked until the ProviderRun ledger design is approved.

### SV-303 - End-to-end recovery and approval tests

Priority: P1
Depends on: SV-105, SV-302, SV-205

Acceptance:

- Product Replication, Brand Voice, and Control/Variant review each cover happy, blocked, recovery, and approval paths.
- Browser reload, broker outage, stale approval, unavailable evidence, ambiguous mechanism, and duplicate command scenarios pass.
- PostgreSQL remains authoritative throughout.
- Technical success is never rendered as commercial, publishing, deployment, or production approval.

## Epic 4 - Controlled media artifact review

### SV-401 - Media analysis tool contracts

Priority: P2
Depends on: SV-303 and separate provider/privacy approval

Acceptance:

- Defines bounded ASR, OCR, probe, keyframe, and identity-continuity observations.
- Tool output contains provenance, availability, source refs, and stable errors.
- No tool claims rights, originality, platform compatibility, or commercial approval.

### SV-402 - Six-gate Media Integrity review

Priority: P2
Depends on: SV-401

Acceptance:

- Traceability, technical, communicative, identity, source-use, and originality gates remain independent.
- Preflight explicitly reports pending artifact state.
- Artifact review requires controlled evidence.
- One successful gate cannot substitute for another.

## Recommended execution batches

### Batch 1 - Machine contracts only; no database schema change

SV-001, SV-002, SV-003, SV-004.

Status: completed locally on 2026-10-21. Local machine-readable schemas, workflow normalization, Skill metadata, a deterministic fixture oracle, and documented test commands are present and pass their scoped checks. A public synthetic CI step is configured; remote CI status must be verified from the target repository. Canonical artifact validation, fixture-shape validation, and workflow expectation coverage remain separate evidence layers. This completion does not authorize or prove a PostgreSQL schema, migration, Task/Run runtime persistence, provider execution, real-media acceptance, public write surface, deployment, publication, rights, commercial approval, or production acceptance.

### Batch 2 - Design gate

SV-005. ADR 0007 was accepted on 2026-10-21. The approval authorizes the bounded ticket sequence but does not by itself execute a migration, enable a write route, deploy, publish, or grant rights, commercial, or production approval.

### Batch 3 - Read-only Native Agent

SV-101 through SV-105, then SV-201 through SV-205, initially with read-only tools.

Current checkpoint: SV-101 through SV-103 plus SV-104A/B are complete and validated
locally. The current evidence proves a closed internal read-tool registry, factual
ToolRun journal, deterministic typed plan compiler and pure prerequisite evaluator. It does
not claim durable RunPlan persistence, state advancement, command-receipt resume,
HumanApproval writer, public write surface, deployment, render, publication, rights,
commercial approval, or production acceptance.

### Batch 4 - Controlled writes

SV-301 through SV-303 after actor attribution and authorization are approved.

### Batch 5 - Media review

SV-401 and SV-402. Video generation and publishing remain separate future projects.
