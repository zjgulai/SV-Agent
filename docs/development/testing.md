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
rtk uv run --project apps/api python -m mypy apps/api/app
rtk env TEST_DATABASE_URL="$TEST_DATABASE_URL" uv run --project apps/api python -m pytest apps/api/tests -q
```

Tests use a real PostgreSQL transaction and dependency overrides; API tests do not mock repositories. Provider tests use HTTPX `MockTransport`, while worker tests prove transactional Job/Outbox creation, broker-failure recovery without a false terminal Job, bounded delivery backoff, dead-letter recovery, queued replay publication, duplicate-delivery suppression, outbox lease fencing, execution fencing, generating/validating redelivery recovery, transient-database retryability, terminal replay, fact-state TOCTOU closure, ordered fact selection, excluded-fact deny-set enforcement, fact-bound version rebind idempotency and Redis-result loss. Database tests also exercise immutable JobEvent/ImportAttempt/outbox intent triggers, the fact-rebind provenance constraint and URL-source reuse. API tests verify that timeline endpoints expose only bounded digests, not raw pages or source URLs.

The unit architecture gate parses every `app/ports/*.py` module and rejects imports from `app.adapters`, preserving the dependency direction without loading infrastructure.

Pattern compiler tests cover every pattern/language across the deterministic 15-second
3 phase/4 shot, 30-second 4 phase/6 shot and 45-second 5 phase/8 shot defaults;
they also prove persisted `p1.3a` definitions are never reinterpreted through the
current registry. Provider and validator tests separately cover the complete shot plan,
role, timing budget and speaking-rate constraints.

P1.3c tests additionally cover the closed audience profile set, prove that only frozen
server-owned creative copy changes, and exercise typed Promotion Fact creation/idempotency.
Promotion tests must use real PostgreSQL constraints, reject direct generic-fact bypasses and
recheck inactive promotions before provider execution, version save and storyboard approval.

Creative Comparison tests verify that both candidates share one current Fact observation, Product Truth eligibility stays separate from stored/live script validation, rejected or missing contract Facts remain explicit, unknown persisted draft fields fail closed, frozen-field differences block, and the GET performs no external filesystem or network I/O. Web tests verify one Projection GET, local-only lens switching, distinct error recovery and the absence of prototype fixtures or mutation controls.

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

## Momcozy asset archive gates

The commercial media library is local and gitignored. Its acceptance is intentionally split into three distinct gates across two physically separated execution planes: public GitHub-hosted CI and the trusted local checkout.

### Public synthetic CI

GitHub-hosted CI runs only committed synthetic fixtures and production-tool static checks. It routes them into three named, fail-fast steps so a failing contract is visible without waiting for unrelated checks:

| Layer | Command surface | Step timeout | What the result means |
| --- | --- | --- | --- |
| 1 — contracts and static checks | `test_contracts`, Ruff, explicit-package Mypy | 3 minutes | Bundle structure, private-field rejection and production-tool static validity. |
| 2 — Aggregate Index contracts | `test_aggregate_index` | 5 minutes | Deterministic aggregate projection, release publication and failure-boundary contracts over synthetic fixtures. |
| 3 — Private Gate contracts | `test_private_gate` | 10 minutes | Synthetic fail-closed, double-fresh-compile and current-release consistency contracts; it is not a real-library Gate Receipt. |

The step timeouts are bounded operational ceilings, not performance SLAs. Layer 3 intentionally has the largest budget because its synthetic success path builds a 244-Bundle temporary library and exercises a baseline compile, an Aggregate Index CLI publish, and two fresh Private Gate compiles. Each step writes only its layer/scope/result to the GitHub job summary; detailed safe test output remains in the step log.

```bash
rtk uv run --project apps/api python -m unittest tools.momcozy_assets.tests.test_contracts -v
rtk uv run --project apps/api ruff check tools/momcozy_assets
rtk uv run --project apps/api python -m mypy --explicit-package-bases tools/momcozy_assets/aggregate_index.py tools/momcozy_assets/contracts.py tools/momcozy_assets/private_gate.py
rtk uv run --project apps/api python -m unittest tools.momcozy_assets.tests.test_aggregate_index -v
rtk uv run --project apps/api python -m unittest tools.momcozy_assets.tests.test_private_gate -v
```

This proves deterministic contracts and failure boundaries without mounting, caching or uploading the real ignored library. CI green is not evidence that the 244 real Bundles currently pass.

### Local private full-library gate

Validate the exact approved local root without printing private identifiers or copying media into tracked output:

```bash
rtk uv run --project apps/api python -m tools.momcozy_assets.validate outputs/momcozy-content-assets/<approved-scoped-root>
rtk uv run --project apps/api python -m tools.momcozy_assets.aggregate_index outputs/momcozy-content-assets/<approved-scoped-root>
rtk uv run --project apps/api python -m tools.momcozy_assets.private_gate outputs/momcozy-content-assets/<approved-scoped-root>
```

A valid Asset Bundle proves structure, hashes and sensitive-field boundaries. It does not prove per-file brand approval or publication readiness. Aggregate acceptance additionally requires the exact scope marker, closed source schemas, no duplicate structured identity, safe closed-value projection and identical pre/post source-content digests. It must reconcile 244 Bundle entries, 244 unique Bundle refs, 0 quarantined records, 235 `1K` image and 9 `480P` video resolutions, 244 timezone-aware observed timestamps, Batch metadata 235/244, Channel 12/244 and Concept Group 198/244; its QA disposition baseline is 36 `approved`, 198 `hold`, 2 `rejected`, 8 `revision_needed`. Commercial Approval remains unavailable for all 244 records, so the Index is `partial`. Re-running unchanged input must produce an identical canonical `aggregate-index-current.json` and byte-identical release JSON/Markdown. The Private Gate additionally binds the fixed baseline to the full `projection_digest`, validates release schema/internal digest/rendering, reads through owned non-writable directory descriptors and rereads the current release after its second fresh compile. `blocked`, stale, corrupt or failed validation must preserve the previous current manifest. Public CI uses only the committed synthetic tests; the real ignored library is a local/private acceptance surface.

### Local scheduled validation

The local automation may invoke only `private_gate` against the approved ignored root and report its bounded success line or stable failure code. It must not publish, repair, delete, update the baseline, expose paths/identifiers/hashes, or upload artifacts. An automation success is a Gate Receipt for that run only; it is not deployment, runtime, production or Commercial Approval evidence.

## Documentation and capability graph gates

After moving long-lived files or changing architecture relationships:

1. Run a full Understand-Anything scan and graph review in Chinese.
2. Confirm `meta.json`, `scan-result.json` and the final graph describe the same file set.
3. Reject duplicate nodes, dangling edge/layer/tour references and file-level nodes missing from layers.
4. Search for stale moved paths and validate Markdown/HTML links.
5. Run `rtk git diff --check`.
6. For external performance evidence, require source URL, subject, observation window, displayed precision, missing-versus-zero semantics and a claim-safety disposition; never validate it by graph presence alone.

Track only `.ua/knowledge-graph.json`, `.ua/fingerprints.json`, `.ua/meta.json`, `.ua/config.json` and `.ua/.understandignore`. The fingerprint baseline must match the scanned source set before `meta.json` is considered fresh. Intermediate, temp and delayed-trash directories are reproducible and ignored.

## Troubleshooting

- `DEPENDENCY_UNAVAILABLE`: inspect PostgreSQL health and `REM_DATABASE_URL`.
- Job remains queued: inspect the worker and Redis, then query the Job API; do not infer state from Redis alone. If its latest event is `dispatch_dead_lettered`, do not replay it from an HTTP client. A deployment operator may run `python -m app.worker.reconciler retry-dead-letter --job-id <uuid> --confirm DEAD_LETTER_RETRY` in the reconciler environment.
- URL import blocked: use manual input. Do not weaken SSRF validation for local/private hosts.
- uv-installed source contains binary/NUL data: run a full locked, no-cache reinstall: `rtk uv sync --project apps/api --python 3.12 --all-extras --reinstall --no-cache`.
