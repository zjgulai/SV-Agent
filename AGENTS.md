# Project Agent Guide

## Before changing code

Read these sources in order:

1. `docs/superpowers/specs/2026-08-10-product-facts-viral-script-p0-design.md`
2. `docs/superpowers/specs/2026-08-11-oumomo-credit-experiment-system-design.md`
3. `docs/architecture/p0-architecture.md`
4. `docs/development/testing.md`
5. `outputs/oumomo-reverse-engineering/knowledge-base.md` for clean-room experiment work
6. `docs/superpowers/specs/2026-08-14-reliable-execution-ledger-p15-design.md` when P1.5 reliable execution is explicitly approved
7. `docs/superpowers/specs/2026-08-14-storyboard-approval-preview-p2-design.md` when P2.0 is explicitly approved
8. `docs/superpowers/specs/2026-08-14-outbox-dead-letter-retry-p151b-design.md` when P1.5.1b dead-letter recovery is explicitly approved
9. `docs/superpowers/specs/2026-08-14-client-operation-recovery-p141-design.md` when P1.4.1 client operation recovery is explicitly approved
10. `docs/superpowers/specs/2026-08-14-fact-bound-script-revision-p12a-design.md` when P1.2a fact-bound script revision is explicitly approved
11. `docs/superpowers/specs/2026-08-14-pattern-compiler-p13a-design.md` when P1.3a pattern compiler is explicitly approved
12. `docs/superpowers/specs/2026-08-14-duration-sensitive-storyboard-p13b-design.md` when P1.3b defaults are explicitly approved
13. `docs/superpowers/specs/2026-08-14-audience-promotion-contract-p13c-design.md` when P1.3c audience slots or Promotion Facts are explicitly approved
14. `docs/superpowers/specs/2026-08-14-p1-acceptance-closeout-p142-design.md` when P1.4.2 acceptance closeout is explicitly approved

Inspect `git status --short --branch` before writes. Preserve unrelated changes. Work on `main`; do not create worktrees. Prefix every local shell command with `rtk`.

## Non-negotiable boundaries

- PostgreSQL is the only business fact source. Redis/Celery results are disposable.
- Product snapshots and script versions are append-only. Never overwrite historical records.
- Only `confirmed` or `locked` facts may support an acceptable product claim.
- Manual facts are always `user_assertion/manual-form`; only trusted connectors may create `source_field` evidence.
- Provider-controlled product wording is limited to exactly fact-bound voiceover/captions; all other visible creative copy is server-owned.
- Do not expose model private reasoning. Persist inputs, typed outputs, validation findings and factual execution state only.
- URL import is limited to public HTTP/HTTPS Schema.org Product data and must retain SSRF checks.
- Never commit `.env`, credentials, cookies, private URLs, raw full webpages, databases, Redis state or generated test artifacts.
- Do not add account, billing, ranking, video generation or social publishing scope without a new approved design.

## Development method

Use test-first changes. Keep application transactions explicit and repository methods commit-free. Match RFC 9457 Problem Details and stable error codes. Update the architecture or testing document when a change creates lasting project knowledge.

Before reporting completion, run the checks in `docs/development/testing.md` appropriate to the change. Do not commit unless the user explicitly asks.
