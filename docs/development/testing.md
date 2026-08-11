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

Integration tests require:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/reverse_engineer_mode
```

## Backend gates

```bash
rtk uv sync --project apps/api --python 3.12 --all-extras --frozen
rtk uv run --project apps/api ruff check apps/api migrations
rtk uv run --project apps/api mypy apps/api/app
rtk env TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api pytest apps/api/tests -q
```

Tests use a real PostgreSQL transaction and dependency overrides; API tests do not mock repositories. Provider tests use HTTPX `MockTransport`, while worker tests prove broker-failure persistence, queued replay publication, duplicate-delivery suppression, execution fencing, generating/validating redelivery recovery, transient-database retryability, terminal replay, fact-state TOCTOU closure and Redis-result loss. Database tests also exercise append-only triggers and concurrent URL-source convergence.

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

MSW replaces HTTP only. Tests render the real router, QueryClient, forms and resource states.

## Full stack and browser tests

```bash
rtk docker compose -f infra/docker-compose.yml up -d --build
rtk npm --prefix apps/web exec -- playwright install chromium
rtk npm --prefix apps/web run e2e
```

The success E2E creates and locks a fact, generates an acceptable script, appends a derived version, compares it and verifies both downloads. The failure E2E uses an ordinary locked guarantee claim to exercise the real prohibited-claim validator; no test-only production behavior is enabled.

## Troubleshooting

- `DEPENDENCY_UNAVAILABLE`: inspect PostgreSQL health and `REM_DATABASE_URL`.
- Job remains queued: inspect the worker and Redis, then query the Job API; do not infer state from Redis alone.
- URL import blocked: use manual input. Do not weaken SSRF validation for local/private hosts.
- uv-installed source contains binary/NUL data: run a full locked, no-cache reinstall: `rtk uv sync --project apps/api --python 3.12 --all-extras --reinstall --no-cache`.
