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
- PostgreSQL: authoritative sources, snapshots, facts, jobs, generations and versions.
- Redis: Celery broker/result transport only. Deleting a Celery result cannot change a terminal Job.
- Celery worker: receives only a Job UUID, reloads all inputs from PostgreSQL and uses row locks for terminal replay.

The deployment is a modular monolith. Domain models do not depend on FastAPI or SQLAlchemy. API routes convert typed HTTP schemas to application commands. Repositories flush but do not implicitly commit; transaction boundaries live in use cases/routes/workers.

## Evidence and immutability

`ProductSource` stores only necessary bounded fields. A re-parse creates a new `ProductSnapshot`; existing snapshots are never updated. Concurrent imports of the same normalized public URL converge on one source through a partial unique index and upsert. `ProductFact` includes claim, typed value, evidence kind, locator, bounded excerpt, confidence and state. Manual APIs always stamp `user_assertion/manual-form`; only trusted connectors can create `source_field` evidence.

Every `ScriptGeneration` binds a snapshot digest, selected fact IDs, configuration, the complete versioned CreativePattern definition, provider/model and prompt contract version. Each `ScriptVersion` binds that generation and retains its complete validation report. Derived versions use `parent_version_id` and append a new record. PostgreSQL triggers reject updates/deletes to snapshots, generations and versions, reject deletion or evidence mutation of facts, and reject any mutation after a fact is locked.

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

`(job_type, idempotency_key)` is unique. Reusing the key with the same input digest returns the original Job; a different digest returns `IDEMPOTENCY_CONFLICT`. A new Job is published to Celery, and an idempotent replay republishes it only while PostgreSQL still says `queued`; this repairs a process crash between commit and broker publication. Duplicate messages are safe. Broker publication failure moves the durable Job to `FAILED/BROKER_UNAVAILABLE` instead of leaving it queued.

Celery uses late acknowledgement, disables failure ACK and enables worker-lost rejection. SQLAlchemy/OS infrastructure failures are not converted into business failure states: both tasks automatically retry them with capped exponential backoff, and Celery retry messages enter the same fenced redelivery path. Workers lock the Job before state changes, ignore ordinary duplicate deliveries while it is running, and only resume a running Job for broker redelivery or an explicit Celery retry. `attempt_count` is also the execution fencing token: every transition, failure and result write must match the token acquired at start, so a stale Worker cannot overwrite a newer delivery. A terminal Job—including `FAILED` without a script version—is replayed without invoking the provider or appending another version.

## Validation pipeline

The fixed order is structure, timeline, factuality, server-owned creative contract and prohibited claims. Findings are sorted by `(path, rule_id)` for deterministic output. A script is acceptable only when there are no blocking findings. Every shot must declare a product claim, the rendered voiceover/caption must exactly match that declaration, and the declaration must exactly match one referenced fact from the same snapshot in `confirmed` or `locked` state. All other visible copy—phase purposes, visual/action/acceptance directions, titles, tags and shooting list—is replaced with a small server-owned template vocabulary and independently validated. The Worker rechecks fact readiness before calling a provider, then locks and reloads selected facts in the same transaction that validates and saves the version. Prohibited-claim rules still scan every visible script field. Timeline checks include zero start, no overlap, at most 0.1-second gaps, target-end tolerance and conservative English/Chinese speaking rates.

## URL safety

The URL connector accepts only query-free, fragment-free HTTP/HTTPS URLs on their scheme's standard port and rejects credentials. The API resolves every A/AAAA address before persistence and requires public IPs; the Worker repeats validation, tries every address from that validated DNS snapshot while preserving the original Host/TLS SNI, disables environment proxies and redirects, and applies DNS, phase and total deadlines plus a 1 MiB body limit. MIME types are matched exactly. Connector-extracted and manually entered images are capped and each independently passes the same public URL/DNS policy before persistence. It accepts HTML or direct JSON Schema.org Product data, persists only bounded extracted fields, and maps network failures to URL-free stable errors. Re-importing the same safe URL reuses the source and appends a snapshot. It never runs page JavaScript or asks an LLM to invent missing data.

## Provider boundary

`ScriptProvider` receives a typed request containing the snapshot identity, confirmed/locked facts and the exact persisted CreativePattern version, phase sequence and shot roles. The service overwrites provider-supplied duration, language, audience, snapshot identity and non-claim visible copy with the persisted/server-owned contract before validation. `DeterministicScriptProvider` powers local/E2E execution. `OpenAICompatibleScriptProvider` requests a strict schema in which every object rejects extra properties and every field is required, permits one format-repair attempt, records that attempt on the Job, and maps rate limit, availability and invalid output to stable domain errors. Missing, empty or whitespace-only provider credentials fail readiness and task creation rather than leaving a queued Job. API keys remain environment-only.
