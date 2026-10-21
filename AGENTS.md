# Project Agent Guide

## Before changing code

Start at `docs/index.md`, then read only the routes relevant to the task:

1. `docs/architecture/project-layout.md` for repository roles, entrypoints and CRAFT-inspired Agent structure.
   Read `docs/architecture/sv-agent-project-layout-proposal.md` before changing SV-Agent paths or adding local module instructions.
2. `docs/architecture/system-overview.md` for current runtime, data flow and scope.
3. `docs/development/testing.md` for validation commands.
4. `CONTEXT-MAP.md` and the relevant `docs/contexts/*/CONTEXT.md` when domain language is involved.
5. `docs/decisions/` for implemented historical contracts and regression boundaries.
6. `docs/research/oumomo/evidence-index.md` for clean-room experiment work.
7. `tools/momcozy_assets/README.md` and ADR 0006 plus the local scoped index/report for Momcozy asset or Private Gate work.
8. `docs/research/leap/public-report-evidence.md` plus the Content Performance Intelligence context for external performance or creative-direction work.
9. `docs/product/insight-performance-projection-design.md` for the selected compare-bound Decision Brief, subject binding, missing-value semantics and reviewed-package gates.
10. `docs/product/project-skill-system.md` and `$factframe-workflows` when a task spans multiple capability contexts or needs project workflow routing.
11. `docs/product/viral-replication-execution.md`, `docs/product/viral-replication-graph-consistency.md` and `.agents/workflows/viral-replication/README.md` when the task concerns viral replication SOPs, skills, fixtures, graph consistency or workflow routing.
12. `docs/product/sv-agent-ui-ux-taste-audit.md` for SV-Agent shell, responsive navigation, information hierarchy, state-system or visual acceptance work.
13. `docs/research/sv-agent-video-model-selection.md` before adding video generation, model routing, TokenHub/VOD adapters, paid smoke tests or media-provider scope.

Before editing a high-risk subtree, read its scoped guide: [SV-Agent domain](apps/api/app/domain/sv_agent/AGENTS.md), [migrations](migrations/AGENTS.md), [Momcozy asset tools](tools/momcozy_assets/AGENTS.md), or [SV-Agent Web feature](apps/web/src/features/sv-agent/AGENTS.md). These files add local rules and never replace this root guide.

`docs/archive/implementation-plans/` records historical execution and blocked work. It is not the current TODO or architecture authority.

Inspect `git status --short --branch` before writes. Preserve unrelated changes. Work on `main`; do not create worktrees. Prefix every local shell command with `rtk`.

## Documentation and capability graph

- Treat the repository as a CRAFT-inspired Agent project: living specifications stay under `docs/`, evidence under `docs/research/` and tracked `outputs/`, reusable instructions under `.agents/`, current delivery tickets under `docs/product/`, and executable products under `apps/`, `tools/`, `infra/`, `migrations/` and `sites/`. Do not create duplicate facade trees.
- Authority order is code/database/tests, living docs and ADRs, implemented decision contracts, dated research evidence, then archived plans.
- `.ua/knowledge-graph.json` is generated navigation. It never proves runtime, deployment, data quality or production acceptance by itself.
- Track `.ua/knowledge-graph.json`, `.ua/fingerprints.json`, `.ua/meta.json`, `.ua/config.json` and `.ua/.understandignore`; do not track `.ua/intermediate/`, `.ua/tmp/` or `.ua/.trash-*`.
- Regenerate the graph after path, module, dependency or long-lived documentation changes. Reject dangling edges and stale `meta.json`.
- A gitignored path is not automatically garbage. In particular, preserve `outputs/momcozy-content-assets/`, Oumomo artifacts and scoring degradations unless an exact evidence-aware deletion is approved.
- When moving documents, update `docs/index.md`, cross-links, `AGENTS.md` routing and any relevant graph freshness instructions in the same change.

## Non-negotiable boundaries

- PostgreSQL is the only business fact source. Redis/Celery results are disposable.
- Product snapshots and script versions are append-only. Never overwrite historical records.
- Only `confirmed` or `locked` facts may support an acceptable product claim.
- Manual facts are always `user_assertion/manual-form`; only trusted connectors may create `source_field` evidence.
- Provider-controlled product wording is limited to exactly fact-bound voiceover/captions; all other visible creative copy is server-owned.
- Do not expose model private reasoning. Persist inputs, typed outputs, validation findings and factual execution state only.
- URL import is limited to public HTTP/HTTPS Schema.org Product data and must retain SSRF checks.
- Never commit `.env`, credentials, cookies, private URLs, raw full webpages, databases, Redis state or generated test artifacts.
- Keep the real Momcozy library in the local Private Gate. Public CI may use only committed Synthetic Fixtures; its success cannot be reported as real-library acceptance. Keep local automation paths, IDs, credentials and receipts out of tracked docs and the capability graph.
- Do not add account, billing, ranking, video generation or social publishing scope without a new approved design.

## Development method

Use test-first changes. Keep application transactions explicit and repository methods commit-free. Match RFC 9457 Problem Details and stable error codes. Update the architecture or testing document when a change creates lasting project knowledge.

Before reporting completion, run the checks in `docs/development/testing.md` appropriate to the change. Do not commit unless the user explicitly asks.
