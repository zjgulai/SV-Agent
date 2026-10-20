---
name: factframe-workflows
description: Route substantial FactFrame work across Product Truth, safe product import, scripts and Storyboards, reliable execution, Creative Comparison, experiment evidence, Momcozy assets, and readiness verification. Use when a task spans bounded contexts or the correct project workflow is unclear; skip when one narrower FactFrame skill already matches.
---

# FactFrame Workflows

Use this as a thin router, not as a replacement for domain skills or `docs/index.md`.

## Start here

1. Read `docs/index.md`, then inspect `git status --short --branch` and the relevant living context.
2. Treat `.ua/knowledge-graph.json` as navigation only. If its HEAD, file set, or metadata is stale, verify conclusions against code, tests, migrations, ADRs, and living docs.
3. Select one primary workflow below. Load a second only when the task crosses an explicit seam.

| User intent or affected contract | Primary skill |
| --- | --- |
| Product Source, Snapshot, Fact lifecycle, claim eligibility, Promotion Fact | `$factframe-product-truth` |
| Public Schema.org Product URL, SSRF, bounded fetch, parse provenance | `$factframe-safe-product-import` |
| Script Generation, Pattern, validation, fact rebind, Storyboard review | `$factframe-script-storyboard` |
| Job, Outbox, Celery, retry, fencing, timeline, dead-letter recovery | `$factframe-reliable-execution` |
| Version comparison, Decision Brief, external package binding | `$factframe-creative-comparison` |
| Oumomo manifest, observation, credit, artifact, finding | `$factframe-experiment-evidence` |
| Momcozy Bundle, Aggregate Index, Synthetic CI, Private Gate | `$factframe-momcozy-assets` |
| Viral reference, mechanism decomposition, replication contract, narrative/proof/experience workflow | `$viral-reference-intake` + [Viral Replication workflow packs](../../workflows/viral-replication/README.md) |
| Complete, releasable, deployed, production-ready, proof scope | `$factframe-readiness` |

Read [references/capability-map.md](references/capability-map.md) only for cross-context sequencing or proof-level disputes.

### Seam disambiguation

- Promotion Fact creation/state belongs to Product Truth; provider exclusion and final CTA placement belong to Script/Storyboard.
- Manual `source_field` forgery belongs to Product Truth; public URL network/fetch behavior belongs to Safe Product Import.
- “Momcozy” performance or winner questions belong to Creative Comparison; only Bundle/Index/Private Gate work belongs to Momcozy Assets.
- “Production-ready” uses the affected domain skill for contract validity and Readiness only for proof scope.
- `publish-aggregate` means an immutable Aggregate release, never media or social publishing.
- “Viral”, “爆款复刻”, “reference remake”, or “creative replication” first routes through the Viral Replication decision tree. Load one primary mechanism workflow only: `narrative-transformation`, `proof-demonstration`, `experience-pov`, `attention-grammar`, `conversion-action`, or `trend-native`.
- Reference performance is a bounded observation. Do not promote reference speech, visual inference, ranking, or AI summary to Product Fact; use `$viral-fact-mapping` and the existing Product Truth seam.

## Shared decisions

- Authority order is code/database/tests, living docs and ADRs, implemented decision contracts, dated research evidence, then archived plans.
- PostgreSQL is business truth. Redis, Celery results, UI state, reports, capability graphs, and generated summaries cannot promote evidence into Product Facts.
- Keep Product Truth, performance, experiment, and asset evidence as separate typed planes. Never collapse them into a generic evidence list.
- Preserve append-only snapshots, versions, events, releases, manifests, and findings. Do not silently rewrite history.
- Do not persist or expose private reasoning. Persist typed inputs, outputs, findings, digests, and factual execution state.
- Distinguish local tests, disposable PostgreSQL integration, public Synthetic CI, Private Gate, deployment, live access, commercial approval, and production acceptance.

## Cross-context orchestration

1. Name the decision and the subject identity.
2. Establish the authoritative Product Snapshot and eligible Facts.
3. Freeze the generation contract before provider work.
4. Produce and validate append-only Script/Storyboard artifacts.
5. Compare immutable candidates using one current Product Truth observation.
6. Bind external evidence only through its own reviewed identity and lifecycle gate.
7. Compile deterministic findings and Decision Brief content without request-time inference.
8. Run the smallest sufficient validation gate and state its proof boundary.

For Viral Replication, the additional sequence is:

1. Build a digest-linked `ReferenceBundle`.
2. Produce a timed `DecompositionMap` and choose one primary mechanism.
3. Abstract a `PatternHypothesis` with invariant, replaceable, prohibited, and unknown elements.
4. Freeze a `ReplicationContract` with one changed Creative Dimension and the target Product Snapshot/Facts.
5. Hand off to `factframe-script-storyboard`, then reconcile execution and findings through `factframe-experiment-evidence`.

## Output contract

Report the selected workflow, authoritative source, changed contract, validation run, proof level, and unresolved boundary. If a requested action would upgrade evidence, broaden permissions, alter historical records, or cross an unimplemented gate, stop and name the required decision instead of improvising.
