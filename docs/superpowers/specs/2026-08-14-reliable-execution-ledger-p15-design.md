# P1.5 Reliable Execution Ledger Design

## Scope

This approved P1.5 slice removes the API commit-to-Celery-publish failure gap and
makes import/job execution observable from PostgreSQL. It adds only:

- transactional `OutboxEvent` delivery for the two existing Job types;
- append-only `JobEvent` state history;
- append-only `ImportAttempt` observations for every product-fetch execution;
- a bounded outbox reconciler and a Job timeline API/UI projection.

It does not add users, tenants, billing, ProviderRun, media rendering, publishing,
or any real Oumomo credit operation.

## Authoritative state and delivery rule

PostgreSQL remains the only business authority. A queue request creates the Job,
its initial `JobEvent`, and exactly one `OutboxEvent` in one transaction. A
successful HTTP response therefore means the work is durably recoverable even if
the API process exits before it can notify Celery.

`OutboxEvent` has immutable intent (`job_id`, `task_name`, `payload_digest`,
`created_at`) and mutable delivery coordination only:

```text
pending --claim(token, expires_at)--> leased --broker accepted--> published
   ^                                  |
   +-------- broker error/expired ----+
```

Claiming locks a pending/expired row with `FOR UPDATE SKIP LOCKED`, increments
`delivery_attempt_count`, and records a random lease token. The task is sent only
after that claim commits. Publishing requires the same unexpired token. A crash
after broker acceptance but before `published` may send a duplicate; Job fencing
and duplicate suppression make that safe. A crash before broker acceptance leaves
an expired lease that the reconciler can claim again **only while its Job is still
`queued`**. It never republishes a Job already in a running state. This is at-least-once
delivery, not an unsafe claim of exactly-once task execution.

The API performs a best-effort immediate outbox nudge for normal latency but never
turns broker unavailability into a business `FAILED` Job. A separate long-running,
database-backed reconciler process invokes the publisher periodically; it is not a
Celery Beat task, because a broker outage must not prevent the recovery loop from
observing and retrying pending outbox rows.

## Ledger contracts

### JobEvent

Every Job state/attempt/error change appends one immutable row, including the
initial `queued` state. `event_sequence` is database allocated and gives a stable
total ordering. Rows contain only:

- job identity, state, attempt count;
- stable error code/detail where applicable;
- server timestamp.

The Job row remains the current-state projection. The event ledger is never
updated or deleted. A state write and its event are flushed in the same transaction.

### ImportAttempt

An `ImportAttempt` is an immutable, per-execution observation, not a mutable
replacement for `ProductSource`. It is appended at `started`, `parsed`, `succeeded`
or `failed` stages and contains the stable source/job identities plus only bounded
provenance: normalized URL digest, connector response digest, optional Snapshot ID
and stable error code. It does not store raw HTML, credentials, headers, cookies or
DNS/IP addresses. The URL source is revalidated by the existing connector at
execution time; security-sensitive resolution observations stay in operational
logs, not the business ledger.

`attempt_token` equals the Job fencing `attempt_count`. Consumers group the rows by
`job_id` and token to reconstruct a fetch attempt even when a Worker dies between
two stages. A database-assigned `attempt_sequence` gives a stable display order
even when multiple events share one transaction timestamp.

## API and UI contract

`GET /api/v1/jobs/{id}/events` returns ordered, immutable event rows, and
`GET /api/v1/product-imports/{id}/attempts` returns bounded provenance for import
jobs only. The existing Job response remains a current-state projection. The job
page renders the actual stage history (queued, fetching/generating,
parsing/validating, terminal) and timestamp instead of a fabricated percentage.
It keeps 1-second polling for the current Job while nonterminal; event reads use
the same PostgreSQL data.

## Failure boundaries and acceptance

- A test that raises after transaction commit and before the immediate nudge finds
  one pending OutboxEvent; reconciler delivery eventually starts exactly one Job
  business execution.
- Two publishers racing on the same pending event yield at most one active lease.
  An expired lease can be reclaimed; an old token cannot mark a newer claim
  published.
- Broker send failure keeps the Job queued and releases the outbox event for
  recovery. It never writes `BROKER_UNAVAILABLE` as a terminal business failure.
- Every queue, state transition and retry writes a JobEvent in order; database
  triggers reject its update/delete.
- An import creates immutable `ImportAttempt` observations with no raw payload;
  a successful final observation references the newly appended Snapshot.
- Migration is verified only against a disposable database by upgrade, downgrade
  and upgrade-to-head. Existing application databases receive forward migration
  only; downgrade is destructive and is never a production recovery method.

## Explicit follow-up, not hidden in this slice

Dead-letter policy, max-age/manual retry UX, tenant authorization and immutable
ProviderRun cost records are later P1.5 increments. This slice deliberately keeps
retryable queue transport failure separate from terminal product/script business
failure.
