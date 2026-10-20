---
name: factframe-reliable-execution
description: Design, change, diagnose, or verify FactFrame Jobs, transactional Outbox delivery, Celery redelivery, execution fencing, reconciliation, event timelines, dead-letter recovery, and browser operation recovery. Use for asynchronous reliability and state ambiguity; skip synchronous domain validation failures.
---

# FactFrame Reliable Execution

Read `docs/index.md`, the reliable execution and operation recovery decisions, current Job/Outbox domain, repositories, Worker/reconciler, and [references/state-fencing-and-recovery.md](references/state-fencing-and-recovery.md).

## State model

- PostgreSQL Job state is business truth. Outbox and Celery coordinate delivery; Redis results are disposable.
- Canonicalize the request. `(job_type, idempotency_key)` plus the same digest returns the original Job; a different digest is `IDEMPOTENCY_CONFLICT`.
- Create Job, initial JobEvent, and unique Outbox intent in one transaction.
- Broker failure returns Outbox to `pending`; Job remains `queued`.
- Reconcile with PostgreSQL time, `FOR UPDATE SKIP LOCKED`, random lease tokens, and expirations. Only the current lease holder may confirm publication.
- Messages contain an opaque Job UUID. Workers reload inputs from PostgreSQL and fence execution with the attempt count.
- Ordinary duplicates do not repeat business work. Celery redelivery/retry may resume eligible work; terminal replay performs no provider/connector call and appends no result.
- Known business failures use stable safe codes. Infrastructure failures are retried without converting uncertainty into success.
- JobEvent and ImportAttempt records are append-only and contain bounded factual provenance.
- A dead Outbox does not make the Job terminal. Only an operator may create a new delivery cycle for `dead + queued` after explicit confirmation.

## Diagnostic SOP

1. Define the expected terminal state and idempotency identity.
2. Read the PostgreSQL Job, ordered JobEvents, Outbox row/lease, and bounded attempt records before inspecting broker/Redis symptoms.
3. Classify the failure as domain rejection, publish failure, expired lease, stale publisher, duplicate delivery, infrastructure retry, execution uncertainty, or UI recovery ambiguity.
4. Prove the violated transition with a focused test before patching.
5. Keep the fix inside explicit application transactions and append immutable intent/evidence.
6. Verify unit state transitions, real PostgreSQL integration, timeline API, and Web/E2E recovery only where the change crosses those layers.

## Stop conditions

- Do not claim exactly-once execution; the contract is at-least-once delivery plus fenced business execution.
- Do not auto-take over `fetching`, `parsing`, `generating`, or `validating` work without an execution lease and provider idempotency design.
- Do not add an anonymous retry endpoint, tenant/RBAC behavior, or automatic dead-letter recovery.
- Browser recovery may replay only the exact persisted operation; ambiguous identity must remain unresolved.
- A local green test does not prove real broker recovery, provider idempotency, deployment, or production acceptance.
