# System Architecture

## Purpose

FactFrame turns bounded product sources into evidence-bearing facts, then into typed, validated and versioned short-form commerce scripts and Storyboards. Its core value is the evidence chain, not generic text or media generation. Momcozy is the primary Brand Workspace; it does not replace the platform identity or the PostgreSQL fact model.

```text
manual form / public Schema.org Product
                 │
                 ▼
ProductSource → immutable ProductSnapshot → ProductFact ledger
                                                │ confirmed / locked only
                                                ▼
                                      ScriptGeneration + Job
                                                │ Celery/provider
                                                ▼
                              append-only ScriptVersion + ValidationReport
```

## Runtime components

- `apps/web`: React/Vite client. It renders database-backed resource state, never model reasoning.
- `apps/api`: FastAPI HTTP contract, application use cases, pure domain rules and infrastructure adapters.
- PostgreSQL: authoritative sources, snapshots, facts, jobs, execution ledgers,
  outbox events, generations and versions. The additive SV-Agent namespace holds
  Task/Run current heads, immutable revisions/envelopes and one factual event timeline.
- Redis: Celery broker/result transport only. Deleting a Celery result cannot change a terminal Job.
- Celery worker: receives only a Job UUID, reloads all inputs from PostgreSQL and uses row locks for terminal replay.
- Outbox reconciler: a separate database-backed process that retries pending
  delivery intent; it does not depend on Celery Beat and never takes over a
  running Worker execution.

The deployment is a modular monolith. Domain models do not depend on FastAPI or SQLAlchemy. API routes convert typed HTTP schemas to application commands. Repositories flush but do not implicitly commit; transaction boundaries live in use cases/routes/workers.

## Capability planes

The repository contains two local evidence planes and one bounded external signal source that are deliberately outside the application runtime:

- `tools/oumomo_experiments` and `outputs/oumomo-reverse-engineering` form a clean-room Experiment Evidence context with append-only file ledgers, hashes and findings.
- `tools/momcozy_assets` and the ignored `outputs/momcozy-content-assets` form a local Momcozy Asset Intelligence context with Asset Bundles, provenance and QA.
- `docs/research/leap/public-report-evidence.md` records a dated public LeapAI cross-platform report as Content Performance Intelligence. It preserves the displayed window, aggregates, rankings and method gaps without importing report output into PostgreSQL.

These planes can support capability findings, creative hypotheses and roadmap decisions, but they do not write Product Facts or application state. Reported selling points must pass the same confirmed/locked fact gate as every other claim. Their relationship is documented in [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md) and [`docs/product/capability-model.md`](../product/capability-model.md).

`tools.momcozy_assets.aggregate_index` is a local deep Module over an explicitly marker-approved Momcozy Brand Workspace root. Its read-only compile Interface hides recursive source discovery, closed source schemas, Bundle contract validation, C/D/E ledger and Batch F plan reconciliation, scoped channel metadata, disposition normalization, duplicate/conflict checks, closed-value privacy projection, pre/post content-digest drift detection, stable sorting and JSON/Markdown rendering. The separate CLI publishing path creates an immutable digest release and atomically switches one current manifest only after both projections are complete and atomically installed; a blocked or failed build cannot replace the current release. The current local result covers all 244 Bundle records but remains `partial`: Batch metadata covers 235, Channel 12 and Concept Group 198; no separate Commercial Approval record is present. The generated files stay inside the ignored private asset root and are not a PostgreSQL fact source or runtime connector.

`tools.momcozy_assets.private_gate` is the read-only local acceptance Interface over that Module. It compiles the approved root twice, binds a tracked non-sensitive baseline to the complete projection digest, and uses owned non-writable directory descriptors to validate and reread the canonical current manifest plus immutable release schema, internal digest and rendered bytes. It emits only a bounded Gate Receipt and does not publish, repair, access network/database/Redis/Celery or create Product Facts. Public GitHub-hosted CI executes only committed synthetic fixtures; a local scheduler may invoke the same private gate against the ignored library. These paths are physically separated, and neither public CI nor scheduling upgrades technical validation into Commercial Approval, deployment or production acceptance.

`ProductConnector` owns the `ParsedProduct` ingress DTO returned by connector implementations. `SchemaOrgProductConnector` imports and produces that port type; the port layer has no adapter dependency. The DTO retains bounded parser output and resolution evidence at the connector Interface without turning either into a Product domain entity. A unit-level architecture check rejects future `app.ports → app.adapters` imports. This ownership change does not alter HTTP, parsing, persistence or Worker behavior.

The Phase 1 `CreativeComparisonLab` is a read-only application Module behind `GET /api/v1/scripts/{script_id}/creative-comparison`. It reads two append-only Script Versions, obtains the current Product Facts and `statement_timestamp()` in one Fact query, and evaluates both candidates against that shared observation. Product Truth eligibility, stored validation, live validation and comparability findings remain distinct; external Performance, Experiment and Asset evidence stays explicitly `unavailable`. The Web compare page consumes one Projection and switches Script/Storyboard/Asset lenses locally. `VITE_CREATIVE_COMPARISON_LAB=false` restores the legacy field-diff view. This capability creates no comparison identity, decision, render or publication state.

The selected Insight/Performance design deepens that same Module rather than introducing a standalone Insight Hub. D1 supplies typed public reviewed-package contracts, closed missing-value semantics, one committed Synthetic Fixture, and implementation-private `UnavailableComparisonEvidenceReader` / `InMemoryComparisonEvidenceReader` seams. They are deliberately not wired into a route, `CreativeComparisonLab`, PostgreSQL, filesystem or private evidence. A later `creative-comparison-view-v2` may compile a deterministic Decision Brief through this seam; the caller still supplies only the existing Script and Control/Variant identities. The first eligible source would be a public, reviewed, digest-bound offline Performance package selected by a separate deployment-local binding registry using one frozen Product Snapshot's database id, recomputed canonical digest and closed evidence context. The portable package does not contain FactFrame runtime identity, and this manual selection alone does not prove Market/Model/Variant equivalence. Brand/title/category similarity is never a binding. The audited Leap bottle-washer/warmer subject and the M5 private asset baseline therefore remain unjoined. D2 remains separately approved work; the current Module still performs no package/filesystem/network I/O.

## Evidence and immutability

`ProductSource` stores only necessary bounded fields. A re-parse creates a new `ProductSnapshot`; existing snapshots are never updated. Concurrent imports of the same normalized public URL converge on one source through a partial unique index and upsert. `ProductFact` includes claim, typed value, evidence kind, locator, bounded excerpt, confidence and state. Manual APIs always stamp `user_assertion/manual-form`; only trusted connectors can create `source_field` evidence.

Every `ScriptGeneration` binds a snapshot digest, an ordered `selected_fact_ids` list, an explicit `excluded_fact_ids` deny-set, configuration, the complete versioned CreativePattern definition, provider/model and prompt contract version. The selected list is non-empty, unique, limited to confirmed/locked facts from the latest snapshot, and its order is provider priority; excluded IDs are unique, disjoint, and must belong to that snapshot. Both lists enter the input digest, read API and export. Each `ScriptVersion` binds that generation and retains its complete validation report. Derived versions use `parent_version_id` and append a new record. PostgreSQL triggers reject updates/deletes to snapshots, generations and versions, reject deletion or evidence mutation of facts, and reject any mutation after a fact is locked. `JobEvent` and `ImportAttempt` are also append-only; their database sequence is the only timeline ordering source.

The implemented P1.2a revision path is deliberately narrower than a free-form editor: a request supplies one selected frozen Fact ID for every existing shot and an idempotency key. The server rejects blocked parents, stale facts, incomplete/repeated indices and excluded or out-of-contract facts; it preserves phase/timing and all server-owned creative fields, then rebuilds only voiceover, caption, product claims and supported Fact IDs from the chosen fact's stored claim. The child is saved only after the frozen contract validates, with fixed `fact_rebind/local_operator/fact_rebind` provenance and a request digest. PostgreSQL permits either legacy null provenance or that exact complete provenance tuple, and makes `(parent_version_id, operation_key)` unique. No client-supplied title, copy, timing, author or free-text reason is accepted before the separately approved tenant/approval design.

P1.3a compiled the original frozen contract; P1.3b compiled duration-sensitive `p1.3b`/`1.2` definitions. P1.3c now compiles new patterns into `p1.3c`/`1.3`: 15/30/45-second defaults use 3/4, 4/6 and 5/8 phase/shot topology, while a closed audience profile only changes frozen server-owned scene/prop copy. An optional Promotion Fact is a separate immutable, time-bounded contract, never a selected product claim; it may render only in the final CTA slot and is rechecked at queue, provider execution, version save, preflight and approval. Provider, renderer, validator, storyboard and revision paths reload the frozen object rather than the live registry. Old `1.0`, `p1.3a` and `p1.3b` generations use only their stored plans and are never reinterpreted. The read-only pattern catalog gives the Web a duration/language-specific preview that renders every shot; provider payload excludes audience profile, resolved copy and promotion.

## Job semantics

Product import:

```text
queued → fetching → parsing → succeeded
                      └──────→ failed
```

Script generation:

```text
queued → generating → validating → succeeded
                              └──→ validation_failed
```

`(job_type, idempotency_key)` is unique. Reusing the key with the same input digest returns the original Job; a different digest returns `IDEMPOTENCY_CONFLICT`. A queue transaction creates the Job, its initial `JobEvent`, and one immutable-intent `OutboxEvent` together. The API may nudge that exact outbox event for low latency; the reconciler independently leases and publishes pending or expired events. Broker publication failure releases the lease to `pending` with bounded exponential backoff and writes a delivery event, while the Job remains `queued`; it is not a business `FAILED` result. A delivery cycle that reaches its configured attempt or age limit becomes `OutboxEvent.dead`, writes `dispatch_dead_lettered`, and no longer consumes reconciler work. Only a deployment-channel operator command can create the next `pending` delivery cycle; no anonymous HTTP retry endpoint exists before P1.5.3 tenant/auth. The delivery lease is fenced by a random token, so an old publisher cannot acknowledge a newer claim. A crash after send but before the published acknowledgement can produce a duplicate message, and the Job Worker remains responsible for suppressing duplicate business execution.

Celery uses late acknowledgement, disables failure ACK and enables worker-lost rejection. SQLAlchemy/OS infrastructure failures are not converted into business failure states: both tasks automatically retry them with capped exponential backoff, and Celery retry messages enter the same fenced redelivery path. Workers lock the Job before state changes, ignore ordinary duplicate deliveries while it is running, and only resume a running Job for broker redelivery or an explicit Celery retry. `attempt_count` is also the execution fencing token: every transition, failure and result write must match the token acquired at start, so a stale Worker cannot overwrite a newer delivery. Every Job state or attempt change appends a `JobEvent`. Each product-fetch execution appends bounded `ImportAttempt` observations (`started`, `parsed`, terminal) with URL/DNS/response digests and an optional Snapshot ID, never raw pages or credentials. The reconciler only publishes `queued` Jobs; it never auto-reclaims `fetching`, `parsing`, `generating`, or `validating` without a separately approved execution-lease and provider-idempotency design. A terminal Job—including `FAILED` without a script version—is replayed without invoking the provider or appending another version.

The Web client retains a bounded versioned `sessionStorage` operation record only for URL imports and script generation. It freezes the route, JSON payload and idempotency key before POST. A transport failure or a 2xx response that is not JSON becomes an `unknown` operation rather than a new submission; if a same-origin, query-free `Location: /api/v1/jobs/{id}` is present, the client opens that existing Job directly. The only recovery action replays the exact stored body and key, relying on the server idempotency contract to converge on one Job. No response body is stored or shown. Job polling pauses while hidden, backs off read failures, stops at terminal/dead-letter state and offers a GET-only reconnect control.

## Validation pipeline

The fixed order is structure, timeline, factuality, excluded-fact deny-set, server-owned creative contract and prohibited claims. Findings are sorted by `(path, rule_id)` for deterministic output. A script is acceptable only when there are no blocking findings. Every shot must declare a product claim, the rendered voiceover/caption must exactly match that declaration, and the declaration must exactly match one referenced fact from the same snapshot in `confirmed` or `locked` state. An excluded fact's normalized claim cannot appear in any visible field: phase purpose, voiceover, caption, visual/action/acceptance directions, declared product claim, title, tag or shooting list; it produces `FACT_EXCLUDED`. All other visible copy is replaced with a small server-owned template vocabulary and independently validated. The Worker rechecks selected fact readiness and excluded-fact snapshot ownership before calling a provider, then locks and reloads both sets in the same transaction that validates and saves the version. Prohibited-claim rules still scan every visible script field. Timeline checks include zero start, no overlap, at most 0.1-second gaps, target-end tolerance and conservative English/Chinese speaking rates.

## URL safety

The URL connector accepts only query-free, fragment-free HTTP/HTTPS URLs on their scheme's standard port and rejects credentials. The API resolves every A/AAAA address before persistence and requires public IPs; the Worker repeats validation, tries every address from that validated DNS snapshot while preserving the original Host/TLS SNI, disables environment proxies and redirects, and applies DNS, phase and total deadlines plus a 1 MiB body limit. MIME types are matched exactly. Connector-extracted and manually entered images are capped and each independently passes the same public URL/DNS policy before persistence. It accepts HTML or direct JSON Schema.org Product data, persists only bounded extracted fields, and maps network failures to URL-free stable errors. Re-importing the same safe URL reuses the source and appends a snapshot. It never runs page JavaScript or asks an LLM to invent missing data.

## Provider boundary

`ScriptProvider` receives a typed request containing the snapshot identity, ordered confirmed/locked selected facts, the explicit excluded-fact deny-set, and the exact persisted `PatternDefinition`. The service overwrites provider-supplied duration, language, audience, snapshot identity and non-claim visible copy with the persisted/server-owned contract before validation; the audience is omitted from the OpenAI-compatible Provider payload. Validation enforces the compiled phase order, phase-to-shot role plan, weighted timeline budget, versioned speaking rate, fact binding and server-owned copy. `DeterministicScriptProvider` powers local/E2E execution. `OpenAICompatibleScriptProvider` requests a strict schema in which every object rejects extra properties and every field is required, permits one format-repair attempt, records that attempt on the Job, and maps rate limit, availability and invalid output to stable domain errors. Missing, empty or whitespace-only provider credentials fail readiness and task creation rather than leaving a queued Job. API keys remain environment-only.

## Current boundary and future gates

The following are current implementation facts:

- Storyboard preflight re-reads the frozen selected/excluded fact contract and re-runs validation. A `ready` preflight can append one immutable `StoryboardVersion`; `StoryboardApprovalEvent` derives `unreviewed`/`approved`/`rejected`/`stale` with a live fact recheck.
- Storyboard preview returns typed shot cards and public image indices only. It performs no Provider call and cannot create a RenderJob.
- Creative Pattern definitions are versioned and frozen through generations, versions, Storyboards and exports.
- Creative Comparison Lab Phase 1 is implemented locally as a read-only projection; it has no external evidence connector, deployment or production acceptance.
- SV-Agent SV-101 is implemented locally as a pure domain kernel: immutable Task/Run values, a closed Run state machine, revision-pinned Goal Track, and one closed Primary Mechanism / Creative Dimension pair per routed Run.
- SV-Agent SV-102 is implemented locally as `0012_sv_agent_persistence`: 13 additive `sv_*` tables, a shared Task/ToolRun/Decision event sequence, append-only and current-head database guards, server-scoped command receipts, explicit Task revision CAS and a read-only factual replay adapter. The repository flushes only; its caller still owns transaction commit/rollback. Only Task create/revise/get and replay have an application-facing persistence seam in this batch.
- SV-Agent SV-103 is implemented locally as a closed internal read-tool layer. Six versioned typed tools wrap Product Truth, Pattern, Job, Script, Storyboard, and Creative Comparison application reads. Job/Script/Storyboard repository access stays behind dedicated application query facades; collection outputs are bounded and provider error details are not projected. A separate flush-only ToolRun journal records immutable intent, server-derived input digest and `pending -> running -> completed|failed|unavailable` events. Current-head writes fence revision, prior status and attempt token; successful terminal events retain the typed output digest. Negative evidence remains a completed typed `not_found` result with its queried subject reference. The caller still owns the transaction, and no public route or business write is enabled.
- SV-Agent SV-104A/B is implemented locally as a pure planning layer. A closed
  `sv-run-plan/v1` contract binds TaskBrief, catalog, route, FactScope and exact
  ApprovalRequest identity; the built-in six-mechanism catalog is digest-bound and explicitly
  `planning_only`. A pure evaluator rejects cross-scope or conflicting projections and returns
  stable blocked, approval, input, ready or complete decisions. `VERIFIED_HUMAN` is only an
  internal projection contract until the trusted adapter exists. This layer does not persist
  or execute plans, dispatch Tools, advance Run state, or create approvals.
  Planner outcomes are computed only after Task/Run, catalog, FactScope and all route evidence
  pass one authoritative-context stage; invalid authority input therefore cannot be masked by
  a missing or ambiguous route disposition.

The following remain future design gates, not implemented capabilities:

- SV-Agent durable Run/RunPlan orchestrator, command-receipt resume for tool invocation, verified actor and authorization adapter, Run/Artifact/runtime-lineage writers, HumanApproval service, workspace projections and every public write route. The pure SV-104A/B planner and internal read ToolRun journal do not make those capabilities active.
- Immutable `ProviderRun` attempt/cost records separated from script artifacts.
- Structured render lexemes and attribute constraints for semantic visual exclusion.
- Keyframe assets, quote state, RenderJob, video generation and publishing.
- Implementation of the selected compare-bound Decision Brief. The Interface, missing-value, provenance, UX and rollback design is documented, but context-specific package schemas/validators and a public, separately bound, source-scoped Snapshot pilot still require separate approval. Private Experiment/Asset evidence additionally requires tenant, Brand Workspace membership, canonical Product Family/Model/Variant binding, RBAC, a safe materialized projection and migration/retention/audit design.
- A standalone Brand Insight Hub. It remains deferred until real non-comparison callers, canonical subject identity, permissions and at least two approved evidence planes exist.
