# Development and Testing

## Toolchain

- Python 3.12 and uv 0.11.14
- Node 22.12–22.x and npm
- Docker Desktop / Docker Engine with Compose

The repository pins Python and npm dependencies in `apps/api/uv.lock` and `apps/web/package-lock.json`. Do not use `--force` or `--legacy-peer-deps` to hide compatibility problems.

## Local dependencies

```bash
rtk docker compose -f infra/docker-compose.yml up -d postgres redis
rtk uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
```

Integration tests require a **separate disposable database** (create it once after
PostgreSQL is healthy, then run its migrations):

```bash
rtk docker compose -f infra/docker-compose.yml exec -T postgres createdb -U reverse_engineer_mode rem_test
rtk env REM_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_test uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
export TEST_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_test
```

## Backend gates

```bash
rtk uv sync --project apps/api --python 3.12 --all-extras --frozen
rtk uv run --project apps/api ruff check apps/api migrations
rtk uv run --project apps/api mypy apps/api/app
rtk env TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api pytest apps/api/tests -q
```

Tests use a real PostgreSQL transaction and dependency overrides; API tests do not mock repositories. Provider tests use HTTPX `MockTransport`, while worker tests prove transactional Job/Outbox creation, broker-failure recovery without a false terminal Job, bounded delivery backoff, dead-letter recovery, queued replay publication, duplicate-delivery suppression, outbox lease fencing, execution fencing, generating/validating redelivery recovery, transient-database retryability, terminal replay, fact-state TOCTOU closure, ordered fact selection, excluded-fact deny-set enforcement, fact-bound version rebind idempotency and Redis-result loss. Database tests also exercise immutable JobEvent/ImportAttempt/outbox intent triggers, the fact-rebind provenance constraint and URL-source reuse. API tests verify that timeline endpoints expose only bounded digests, not raw pages or source URLs.

Pattern compiler tests cover every pattern/language across the deterministic 15-second
3 phase/4 shot, 30-second 4 phase/6 shot and 45-second 5 phase/8 shot defaults;
they also prove persisted `p1.3a` definitions are never reinterpreted through the
current registry. Provider and validator tests separately cover the complete shot plan,
role, timing budget and speaking-rate constraints.

P1.3c tests additionally cover the closed audience profile set, prove that only frozen
server-owned creative copy changes, and exercise typed Promotion Fact creation/idempotency.
Promotion tests must use real PostgreSQL constraints, reject direct generic-fact bypasses and
recheck inactive promotions before provider execution, version save and storyboard approval.

`TEST_DATABASE_URL` must identify a disposable database, never the development or deployment database. Append-only ledger tests intentionally cannot clean rows by deleting them; use the fixture transaction rollback for routine tests and a one-off database for any multi-connection concurrency test.

Migration rollback is destructive. Verify it only against a newly created disposable database, never against the application database:

```bash
rtk docker compose -f infra/docker-compose.yml exec -T postgres createdb -U reverse_engineer_mode rem_migration_check
rtk env REM_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_migration_check uv run --project apps/api alembic -c apps/api/alembic.ini upgrade 0002_integrity_guards
rtk env REM_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_migration_check uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
rtk env REM_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_migration_check uv run --project apps/api alembic -c apps/api/alembic.ini downgrade base
rtk env REM_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_migration_check uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
rtk docker compose -f infra/docker-compose.yml exec -T postgres dropdb -U reverse_engineer_mode rem_migration_check
```

## Frontend gates

```bash
rtk npm --prefix apps/web ci
rtk npm --prefix apps/web run lint
rtk npm --prefix apps/web run typecheck
rtk npm --prefix apps/web test -- --run
rtk npm --prefix apps/web run build
```

MSW replaces HTTP only. Tests render the real router, QueryClient, forms and resource states. The recovery cases must cover a `202` whose body is HTML or malformed JSON with a safe Job `Location`, plus a transport failure followed by a browser-session reload and exact idempotency-key/body replay. Fact-bound revision tests must assert the client only sends `fact_bindings` plus an idempotency key, never title, free copy or timeline fields. They must never assert or render a proxy response body. Polling tests cover terminal/dead-letter stop, hidden-page pause and bounded read backoff.

## Full stack and browser tests

```bash
rtk docker compose -f infra/docker-compose.yml up -d --build
rtk npm --prefix apps/web exec -- playwright install chromium
rtk npm --prefix apps/web run e2e
```

The success E2E creates and locks a fact, generates an acceptable script, opens the storyboard preflight, appends and approves an immutable zero-cost storyboard preview, appends a derived version, compares it and verifies both downloads. The failure E2E uses an ordinary locked guarantee claim to exercise the real prohibited-claim validator; no test-only production behavior is enabled. Compose includes an isolated outbox reconciler process; verify its logs and the Job timeline when testing broker recovery locally.

## Clean-room experiment evidence gates

The Oumomo clean-room outputs use standalone deterministic tools; they do not call the live site:

```bash
rtk uv run --project apps/api python -m unittest discover -s tools/oumomo_experiments/tests -v
rtk uv run --project apps/api ruff check tools
rtk uv run --project apps/api mypy --explicit-package-bases tools/oumomo_experiments
rtk uv run --project apps/api python outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/scripts/validate_evidence.py outputs/oumomo-reverse-engineering --max-spend 980
```

The evidence validator checks manifest fields, closed confidence/verdict enums, hash-only task identity, forbidden sensitive fields, credit arithmetic/continuity and the approved spend cap. It does not prove website availability, provider quality, deployment or production publication.

## Troubleshooting

- `DEPENDENCY_UNAVAILABLE`: inspect PostgreSQL health and `REM_DATABASE_URL`.
- Job remains queued: inspect the worker and Redis, then query the Job API; do not infer state from Redis alone. If its latest event is `dispatch_dead_lettered`, do not replay it from an HTTP client. A deployment operator may run `python -m app.worker.reconciler retry-dead-letter --job-id <uuid> --confirm DEAD_LETTER_RETRY` in the reconciler environment.
- URL import blocked: use manual input. Do not weaken SSRF validation for local/private hosts.
- uv-installed source contains binary/NUL data: run a full locked, no-cache reinstall: `rtk uv sync --project apps/api --python 3.12 --all-extras --reinstall --no-cache`.
