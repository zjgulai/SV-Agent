# P0 Architecture

## Purpose

This system turns bounded product sources into evidence-bearing facts, then into typed, validated and versioned short-form commerce scripts. Its core value is the evidence chain, not generic text generation.

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
  outbox events, generations and versions.
- Redis: Celery broker/result transport only. Deleting a Celery result cannot change a terminal Job.
- Celery worker: receives only a Job UUID, reloads all inputs from PostgreSQL and uses row locks for terminal replay.
- Outbox reconciler: a separate database-backed process that retries pending
  delivery intent; it does not depend on Celery Beat and never takes over a
  running Worker execution.

The deployment is a modular monolith. Domain models do not depend on FastAPI or SQLAlchemy. API routes convert typed HTTP schemas to application commands. Repositories flush but do not implicitly commit; transaction boundaries live in use cases/routes/workers.

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

## Extensibility gates for P1/P1.5/P2.0

Reverse-engineering evidence indicates the next durable architecture increments should be explicit, persisted, and idempotent:

- A read-only storyboard preflight projects a ScriptVersion only after re-reading the frozen selected/excluded fact contract and re-running validation. `ready` preflight can append one immutable `StoryboardVersion`; the frozen record retains pattern/version/phase sequence, fact lists, draft, validation report and canonical digests. An immutable `StoryboardApprovalEvent` then derives `unreviewed`/`approved`/`rejected`/`stale` from its event sequence plus a live fact recheck. Its deterministic animatic returns typed shot cards and public image indices only, performs no Provider call and cannot create a RenderJob. Keyframe assets, quote and render state remain later P2 work.
- Add immutable `ProviderRun` attempt records (request/response digest, provider id, latency, cost) separate from script draft artifacts.
- Add structured render lexemes/attribute constraints for semantic exclusion; the current deny-set only blocks direct normalized claim rendering, while the server-owned visible-copy contract limits the remaining free-text surface.
- Version every `CreativePattern` definition and bind it through all generated versions and exports.
