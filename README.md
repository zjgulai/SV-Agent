# SV-Agent — Evidence-First Viral Replication Agent

SV-Agent turns a viral-video brief into a reviewable chain of evidence, plans, scripts, storyboards and decisions. It is built on the FactFrame runtime, which keeps product facts, immutable versions and execution state traceable. Momcozy is the primary Brand Workspace; Oumomo clean-room experiments, the local Momcozy asset archive and scoped external performance reports supply separate evidence planes without becoming PostgreSQL business facts.

## Agent starts here

1. Read [`AGENTS.md`](AGENTS.md) for safety rules and task routing.
2. Read [`docs/architecture/project-layout.md`](docs/architecture/project-layout.md) for the Agent project map and CRAFT-inspired directory roles.
3. Read [`docs/product/sv-agent-native-agent-spec.md`](docs/product/sv-agent-native-agent-spec.md) for the product contract.
4. Read [`docs/product/sv-agent-implementation-tickets.md`](docs/product/sv-agent-implementation-tickets.md) for the active delivery ledger.
5. Run the checks in [`docs/development/testing.md`](docs/development/testing.md) before claiming completion.

The repository keeps executable code in `apps/`, migrations in `migrations/`, agent Skills and workflows in `.agents/`, research evidence in `docs/research/` and tracked `outputs/`, and public static experiences in `sites/`. This preserves existing imports and deployment paths while making each Agent-development role explicit.

## What is included

- Manual product input and public Schema.org Product import with multi-address DNS-pinned SSRF protection
- Evidence ledger with `proposed / confirmed / rejected / locked` facts
- Seven versioned creative patterns and 15/30/45-second script contracts
- Durable idempotent Jobs backed by PostgreSQL and executed by Celery
- Deterministic local provider and optional OpenAI-compatible strict JSON provider
- Structure, timeline, strict fact binding, server-owned creative-copy and prohibited-claim validation
- Database-enforced append-only snapshots/versions, field-level comparison and JSON/Markdown export
- Immutable storyboard review, deterministic zero-cost animatic preview and local approval events
- Deterministic local Momcozy Aggregate Index over validated Asset Bundles, with explicit missing-evidence coverage
- Read-only Momcozy Private Gate with public synthetic CI and physically isolated local-library validation
- SV-Agent domain kernel plus local Task CAS, immutable journal schema, factual replay, a closed read-tool registry and pure typed plan evaluation; durable execution and public writes remain disabled
- React Web, FastAPI OpenAPI, Docker Compose, CI and Playwright E2E

## Quick start

Prerequisites: Docker Desktop/Engine with Compose. For host development also install Python 3.12, uv 0.11.14 and Node 22.12–22.x.

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d --build
```

Open:

- Web: <http://localhost:5173>
- OpenAPI: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>

The default provider is deterministic and makes no external model request.

## Host development

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis
uv sync --project apps/api --python 3.12 --all-extras --frozen
uv run --project apps/api python -m alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api uvicorn app.main:app --app-dir apps/api --reload
npm --prefix apps/web ci
npm --prefix apps/web run dev
uv run --project apps/api celery -A app.worker.celery_app:celery_app worker --loglevel=INFO
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

Start at [`docs/index.md`](docs/index.md). Use the complete commands and test architecture in [`docs/development/testing.md`](docs/development/testing.md); current component and data-flow decisions are in [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md), the repository map is in [`docs/architecture/project-layout.md`](docs/architecture/project-layout.md), and the integrated Momcozy capability model is in [`docs/product/capability-model.md`](docs/product/capability-model.md).

## Safety and scope

The current system does not include accounts, billing, sales rankings, RenderJob, video generation or social publishing. A local Storyboard Approval is only a future quote gate, never permission to render or publish. URL import handles public structured product data only and deliberately rejects credentials, query strings, fragments and non-standard ports; blocked or incomplete pages fall back to manual entry. PostgreSQL—not Redis, research files, generated assets, capability graphs or model prose—determines visible business execution state.
