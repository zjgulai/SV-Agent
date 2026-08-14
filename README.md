# FactFrame — Product Facts + Viral Script P0

FactFrame is an evidence-first script workspace. It captures immutable product snapshots and fact states, then generates typed short-form commerce scripts whose claims can be traced, validated, versioned, compared and exported.

## What is included

- Manual product input and public Schema.org Product import with multi-address DNS-pinned SSRF protection
- Evidence ledger with `proposed / confirmed / rejected / locked` facts
- Seven versioned creative patterns and 15/30/45-second script contracts
- Durable idempotent Jobs backed by PostgreSQL and executed by Celery
- Deterministic local provider and optional OpenAI-compatible strict JSON provider
- Structure, timeline, strict fact binding, server-owned creative-copy and prohibited-claim validation
- Database-enforced append-only snapshots/versions, field-level comparison and JSON/Markdown export
- Immutable storyboard review, deterministic zero-cost animatic preview and local approval events
- React Web, FastAPI OpenAPI, Docker Compose, CI and Playwright E2E

## Quick start

Prerequisites: Docker Desktop/Engine with Compose. For host development also install Python 3.12, uv 0.11.14 and Node 22.12–22.x.

```bash
rtk cp .env.example .env
rtk docker compose -f infra/docker-compose.yml up -d --build
```

Open:

- Web: <http://localhost:5173>
- OpenAPI: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>

The default provider is deterministic and makes no external model request.

## Host development

```bash
rtk docker compose -f infra/docker-compose.yml up -d postgres redis
rtk uv sync --project apps/api --python 3.12 --all-extras --frozen
rtk uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
rtk uv run --project apps/api uvicorn app.main:app --app-dir apps/api --reload
rtk npm --prefix apps/web ci
rtk npm --prefix apps/web run dev
rtk uv run --project apps/api celery -A app.worker.celery_app:celery_app worker --loglevel=INFO
```

## Optional real provider

Set these environment values without committing `.env`:

```dotenv
REM_SCRIPT_PROVIDER=openai_compatible
REM_PROVIDER_BASE_URL=https://api.openai.com/v1
REM_PROVIDER_MODEL=gpt-5-mini
REM_PROVIDER_API_KEY=replace-locally
```

The adapter sends only the selected snapshot fields, confirmed/locked facts and creative configuration. It does not send raw pages or unconfirmed facts.

## Verification

Use the complete commands and test architecture in [`docs/development/testing.md`](docs/development/testing.md). The long-lived component and data-flow decisions are in [`docs/architecture/p0-architecture.md`](docs/architecture/p0-architecture.md).

## Safety and scope

This P0/P2.0 slice does not include accounts, billing, sales rankings, video generation or social publishing. A local storyboard approval is only a future quote gate, never permission to render or publish. URL import handles public structured product data only and deliberately rejects credentials, query strings, fragments and non-standard ports; blocked or incomplete pages fall back to manual entry. PostgreSQL, not Redis or model prose, determines visible execution state.
