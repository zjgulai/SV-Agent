# SV-Agent Implementation Tickets

Status: Batch 1, SV-101 through SV-103, bounded SV-104A/B, SV-105 and SV-201 through SV-205 are complete and validated locally; SV-005 is accepted; Git, remote CI, deployment and production status must be verified independently
Architecture authority: `docs/product/sv-agent-native-agent-spec.md`
Runtime implementation includes the domain kernel, internal persistence/read seams, pure planning/evaluation, one public read-only Task Inbox, a browser-local New Task brief, read-only Mission Control, Evidence and Artifact, and Approval and Replay workspaces; public writes, durable plan execution and authorization remain inactive.

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
Status: completed locally on 2026-10-21 as a pure next-gate domain reviewer

Acceptance:

- Recomputes artifact digests and validates single-variable isolation, deny-set, and evidence boundaries.
- Returns only `blocked`, `proceed_with_limits`, or `ready_for_next_gate` plus typed findings.
- Reviewer recommendations cannot create human ApprovalEvents.

Implementation result:

- `IndependentReviewer.review(NextGateReviewPackage)` is the only public seam. It consumes
  upstream canonical-validated serialized artifact snapshots, one Task/Run binding, actual
  Control/Variant mechanism values, frozen context, visible claims and typed evidence.
- The reviewer independently recomputes artifact digests and common-envelope scope, then derives
  the actual Control/Variant diff. Exact mechanism coverage is required; exactly one dimension may
  change, and it must equal the ReplicationContract selection. Configuration, Fact binding,
  subject, material scope and claim-contract digests stay frozen.
- The reviewer scans voiceover, caption, on-screen text, visual, action, acceptance, title, tag and
  shooting-list claim projections. Excluded Facts cannot reappear, and Product claims require a
  selected `confirmed` or `locked` Fact plus resolvable Product Truth Fact evidence bound to the
  same Product Snapshot and Fact identity as the ReplicationContract.
- Required next-gate evidence must be `observed` at Fact level. Unknown, unreported, uncollected,
  source-ambiguous, unavailable, quarantined or inference-only required evidence blocks; the same
  states on optional evidence produce `proceed_with_limits`.
- Findings and disposition are deterministic, typed and order-independent. The module performs no
  I/O, persistence, Tool dispatch or state advancement and cannot create an ApprovalEvent.
- This local result does not validate the full durable SV-104 orchestrator, a trusted
  HumanApproval adapter, a public route, production media, deployment, publication, rights,
  commercial approval or production acceptance.

## Epic 2 - A-direction Agent UX

### SV-201 - Task and Decision Inbox

Priority: P1
Depends on: SV-102
Status: completed and validated locally on 2026-10-21

Acceptance:

- Shows waiting decisions, running Tasks, blockers, completed-with-limits, and stopped Tasks.
- Ordering reason is visible.
- Browser-local drafts are clearly separated from persisted Tasks.
- No unavailable Render, Publish, or Ship action appears.

Implementation result:

- `TaskInbox.inspect()` projects at most 100 PostgreSQL Task/current-revision/active-Run heads,
  returns `truncated` when more exist, and applies a versioned deterministic lane order with an
  explicit reason on every item. It reconstructs the current TaskBrief, verifies its digest, and
  rejects an active Run whose `task_revision` is not the current Task revision.
- A Task enters `needs_decision` only when its current Task and Run revisions have an unresolved
  current ApprovalRequest. A DecisionEvent resolves that request only when ID/version, request
  digest and Task/Run revisions all match. Lane, count and gate kinds come from one statement snapshot. A
  waiting-approval Run without that record, or another Run state with a pending request, fails
  closed into technical attention; missing input, business blocker, technical failure, active work,
  completed-with-limits, stopped and not-started remain separate lanes.
- `GET /api/v1/sv-agent/tasks` returns a typed PostgreSQL-authoritative read projection and maps
  journal drift and database unavailability to stable RFC 9457 problems. It creates no writer or
  migration.
- `/sv-agent/tasks` shows persisted records and bounded `sessionStorage` drafts in separate
  authority sections. Denied storage access and corrupt local draft data are ignored locally and
  cannot affect the server projection. No Render, Publish, Ship, Task mutation or Approval action
  is exposed.

Validation: targeted backend contract/integration tests, the full SV-Agent integration directory,
the complete API unit suite, Ruff, Mypy, Web tests, TypeScript, ESLint and the production Web build
pass locally. This validates the read-only Inbox only; it does not prove SV-202 Task creation,
durable plan execution, approval decisions, deployment or production acceptance.

### SV-202 - New Task brief

Priority: P1
Depends on: SV-201
Status: completed and validated locally on 2026-10-21

Acceptance:

- Captures goal track, question, reference, subject, platform, market, language, window, stop condition, and initial rights state.
- Brand Voice does not require Product Snapshot until a product claim is introduced.
- Rights and child-safety boundaries are explicit and cannot be auto-approved.
- Creating a draft does not trigger providers or write tools.

Implementation result:

- `/sv-agent/tasks/new` captures the full brief through controlled native form controls. Product
  Replication requires a Product Snapshot candidate reference. Brand Voice requires one only after
  the user introduces product claims.
- Complete drafts are bounded to 20 records and a 256 KiB versioned `sessionStorage` envelope.
  Public references accept only absolute HTTP/HTTPS URLs without credentials. Saving does not
  fetch the reference or call an API.
- Rights and child-safety start from unresolved states. The form offers no approved value and
  requires two separate acknowledgements that these boundaries still need human gates.
- Inbox cards keep v2 drafts visibly separate from PostgreSQL Tasks and can reopen the same draft
  without changing its identity. Legacy v1 drafts remain readable and are not
  overwritten or presented as complete v2 briefs.
- Denied storage keeps the completed form visible and reports that nothing was saved. A corrupt v2
  envelope, including malformed or oversized data, can be replaced by a valid user submission
  without hiding the authoritative Inbox; parsed drafts are rebuilt from known fields so unknown
  properties are not retained.
- Custom validation marks and focuses the first invalid field while preserving the user's inputs.
- Browser tests observe only the Inbox `GET`; the implementation adds no API mutation, provider,
  Run, Job, Tool, Approval, Render or Publish seam.

Validation: targeted New Task and Inbox tests, the complete Web test suite, TypeScript, ESLint and
the production Web build pass locally. This proves the browser-local brief and authority split
only. It does not create a PostgreSQL Task, validate Product Snapshot existence, approve rights or
child safety, start an Agent Run, deploy or establish production acceptance.

### SV-203 - Mission Control

Priority: P1
Depends on: SV-202, SV-104
Status: complete and validated locally; read-only projection and browser preview only

Acceptance:

- Displays current stage, Run state, Plan, blockers, next safe action, ToolRuns, and current artifact.
- Conversational input previews the compiled AgentCommand and side effects.
- Agent explanations cite artifact and evidence refs rather than private reasoning.
- Reload resumes from authoritative PostgreSQL state.

Implemented result:

- `GET /api/v1/sv-agent/tasks/{task_id}` projects one current Task/Run head from PostgreSQL.
  RunPlan and Artifact frontiers are shown only when the exact current revision has one unique,
  closed-contract-valid candidate. The RunPlan TaskBrief input digest must match the current brief;
  an Artifact must pass the shared canonical schema, exact row-envelope binding and runtime-lineage
  proof.
- The seven-stage path uses `unknown` when persisted evidence cannot prove a stage. ToolRun success,
  downstream artifacts and prototype examples never backfill stage completion, mechanism confidence
  or reviewer recommendations.
- Plan, Artifact, runtime-lineage, ApprovalRequest and ToolRun reads are bounded and deterministically ordered.
  A DecisionEvent resolves an ApprovalRequest only through the complete digest-and-scope handle.
  Approval drift, ambiguous or unverified frontiers, digest/scope drift, rights blocks and technical
  failures fail closed. Runtime-lineage verification payloads must match their stored canonical
  digest. Task/Run heads are rechecked after the projection is assembled.
- `/sv-agent/tasks/:taskId` follows the approved Variant C information hierarchy: explanation and
  seven-stage path in the main pane, replication package and safety boundary in the side pane.
  Raw refs are collapsed into audit details; arbitrary payloads, digests and private reasoning are
  not returned.
- The conversational area creates a browser-memory preview of a closed `ContinueTask` intent and
  instruction. It performs no `POST`, stores no preview, cannot approve/reject, and disables recovery
  when no verified command receipt is available.

Validation: backend projection and HTTP tests cover no-Run, exact/ambiguous/invalid Plan and Artifact
frontiers, runtime-lineage digest drift, unknown stages, approval drift and bounds, ToolRun bounds, 200/404/500/503,
and unchanged row counts. Frontend tests cover complete and missing workspaces, authority boundaries,
command-preview non-effects, truncation, error recovery and Inbox navigation. Backend type/lint/format
checks and the complete Web test, typecheck, lint and production build gates pass locally. This does
not prove durable orchestration, a public command writer, HumanApproval decisions, provider execution,
deployment or production acceptance.

### SV-204 - Evidence and Artifact workspace

Priority: P1
Depends on: SV-203
Status: complete and validated locally; read-only PostgreSQL projection and browser workspace only

Acceptance:

- Displays the canonical artifact dependency graph.
- Product Truth, Performance, Experiment, and Asset evidence remain separate.
- Each conclusion can open source, subject, window, limitation, and proof-level details.
- Control and Variant comparison uses immutable version refs.

Implemented result:

- `GET /api/v1/sv-agent/tasks/{task_id}/artifacts` reads the current Task revision and active
  Run, then projects a deterministic artifact graph across that Run's persisted revisions. The
  route is bounded to 50 nodes, 200 edges and 100 runtime-lineage links; overflow fails closed
  instead of returning a graph that looks complete.
- A row is accepted as a canonical artifact only when the shared deployable Pydantic contract,
  record envelope, payload digest, the canonical content digest, timestamps, Task/Run scope,
  direct refs, full-chain semantic validation and graph resolution agree. FactMap and
  ReplicationContract claim scope, subject, selected Facts and excluded Facts must match. Declared
  and verified edges cannot point backward to an artifact that did not
  yet exist. Dangling refs, cycles, duplicate or conflicting runtime links, verification drift and
  a changed current head return `JOURNAL_INTEGRITY_ERROR`.
- Product Truth becomes `available` only for one current, non-stale FactMap/ReplicationContract
  frontier and one exact Product Snapshot digest whose selected Facts still belong to that Snapshot
  and remain `confirmed` or `locked`. A closed, empty `no_product_claims` chain is `out_of_scope`;
  hidden mappings or competing frontiers are quarantined. Performance, Experiment and Asset remain
  separately `unavailable`; the reader performs no package, filesystem, network or private-library
  access.
- Current canonical artifacts do not declare typed Control and Variant ScriptVersion roles.
  Comparison therefore returns `COMPARISON_VERSION_REFS_UNAVAILABLE`; generic `control_id` /
  `variant_id`, latest-version selection and similarity never create a comparison binding.
- `/sv-agent/tasks/:taskId/evidence` shows the graph, the four evidence planes and artifact-named,
  expandable source-kind, subject, window, limitation and proof-level summaries. Conclusion source
  kinds and one unambiguous observation window are inherited only through declared
  ReferenceBundle lineage. Raw refs and stable codes are collapsed by default. The page makes one
  GET request and exposes no Task/Run write, Approval, Render, Publish or production action.

Validation: backend application and HTTP tests cover no-Run, canonical semantic rejection, exact
Product Truth, current-frontier/no-claim scope, cross-revision chains, time-travel rejection,
closed-envelope drift, dangling refs, digest drift, cycles, output redaction, post-query head
recheck, size bounds, conflicting runtime links, unchanged row counts and 404/500/503 Problem
Details. Frontend tests cover graph/detail rendering, artifact-specific disclosure names, four
distinct evidence planes, closed missing semantics, unavailable comparison, empty/error recovery
and GET-only behavior. The complete SV-Agent regression suite, Web tests, typecheck, lint and
production build pass locally. This does not prove D2 external
evidence binding, private-library acceptance, Control/Variant version availability, HumanApproval,
deployment, publication or production acceptance.

### SV-205 - Approval and Replay workspace

Priority: P1
Depends on: SV-204
Status: completed and validated locally on 2026-10-21

Acceptance:

- Approval cards show target version, effects, non-effects, evidence, limitations, and stale conditions.
- Decisions are `approve`, `reject`, `request_evidence`, or `stop`.
- Replay orders Plan revisions, ToolRuns, artifacts, approvals, and decisions.
- Raw UUIDs, digests, actor refs, rationale, and JSON are not rendered in the browser workspace. Audit details expose only the safe event type, event sequence, and Task/Run revisions.

Implemented result:

- `GET /api/v1/sv-agent/tasks/{task_id}/replay` captures one per-Task replay snapshot fingerprint
  (maximum visible sequence plus visible event count), anchors
  ApprovalRequests, matching DecisionEvents and the shared factual replay to that boundary, then
  rechecks both the boundary and current Task/Run heads before returning. Approval decision state
  and current/stale scope state remain independent.
- DecisionEvents resolve a request only when event type, request ID/version/digest, Task/Run scope,
  human actor kind, closed decision vocabulary and closed payload all match. Replay Plan, ToolRun,
  Artifact and Approval handles are re-bound to their exact stored records; digest/schema/integrity
  drift fails closed with stable RFC 9457 error codes.
- Approval target currentness is limited to canonical `ArtifactType` records and requires exact
  artifact ID/version/digest plus Task/Run scope. Stale/superseded records and older versions are
  shown as stale. External ScriptVersion/StoryboardVersion targets fail closed until an authoritative
  resolver exists. Because the precondition aggregate payload is not persisted in this phase,
  `precondition_digest` is not recomputed; declared `stale_if` conditions remain visible limitations.
- The public projection uses allow-listed, bounded statement fields and performs no write, state
  advance, Tool/provider call, render or publication. It returns no raw payload, digest, actor ref,
  Approval/Artifact identifier, rationale, filesystem path, credential, JSON-shaped string or model
  reasoning. The same visible-text guard applies to Task subject; only the existing route-bound
  Task/Run identity remains in the HTTP shell contract.
- `/sv-agent/tasks/:taskId/approval-replay` renders current, decided and stale approval cards plus an
  event-sequence-ordered factual timeline. It provides navigation back to Mission Control and
  Evidence, but no approve/reject/request-evidence/stop control and no browser-local authority.

Validation: application and HTTP integration tests cover no-Run output, a decided current request,
closed decision vocabulary, exact request binding, ordered cross-stream replay, zero database writes,
404/500/503 Problem Details and safe output keys. Browser tests cover approval state, effects,
non-effects, evidence, limitations, stale conditions, ordered replay, collapsed safe audit metadata,
GET-only behavior, absence of decision controls, and absence of visible raw IDs and digests. The complete SV-Agent and Web
regression gates, Ruff, Mypy, lint, typecheck and production build pass locally. This does not prove a
HumanApproval writer, authenticated human authority, durable orchestration, deployment, publication,
commercial approval or production acceptance.

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

Current checkpoint: SV-101 through SV-103, SV-104A/B, SV-105 and SV-201 through SV-205 are complete and
validated locally. The current evidence proves a closed internal read-tool registry, factual
ToolRun journal, deterministic typed plan compiler, pure prerequisite evaluator, pure independent
next-gate reviewer and a PostgreSQL-authoritative public read-only Task Inbox with a separate
browser-draft authority plane plus a complete local New Task brief that can be resumed from the
Inbox. It also proves a bounded read-only Mission Control with exact current-frontier checks,
unknown-state semantics and an in-memory command preview, plus a fail-closed Evidence and Artifact
workspace that keeps Product Truth, Performance, Experiment and Asset evidence separate. It also
proves a bounded Approval and Replay projection with version-bound request cards, exact
DecisionEvent resolution and one shared, ordered factual timeline. It does not claim PostgreSQL Task
creation, durable RunPlan persistence, state
advancement, command-receipt resume, HumanApproval writer, public write surface, deployment,
render, publication, rights, commercial approval, or production acceptance.

### Batch 4 - Controlled writes

SV-301 through SV-303 after actor attribution and authorization are approved.

### Batch 5 - Media review

SV-401 and SV-402. Video generation and publishing remain separate future projects.
