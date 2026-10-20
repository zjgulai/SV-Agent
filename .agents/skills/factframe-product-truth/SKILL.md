---
name: factframe-product-truth
description: Govern FactFrame Product Sources, immutable Product Snapshots, evidence-bound Product Facts, Promotion Facts, fact states, and claim eligibility. Use for product intake contracts, fact provenance and lifecycle, snapshot identity, or selected/excluded fact rules; skip creative performance, experiments, and asset QA.
---

# FactFrame Product Truth

## Establish authority

Read `docs/index.md`, `docs/contexts/product-truth-script/CONTEXT.md`, the relevant P0 decisions, current domain entities, repositories, migrations, and tests. Use [references/change-matrix.md](references/change-matrix.md) to choose the narrowest code and test surface.

## Invariants

- PostgreSQL is the only business fact source.
- Every new observation creates a new Product Snapshot. A canonical content digest does not replace Snapshot identity.
- Only `confirmed` or `locked` Product Facts may support an acceptable claim. Confidence is not approval.
- A locked Fact is not edited in place; create a new Fact with explicit provenance.
- Manual facts are always `user_assertion/manual-form`. Only trusted connectors create `source_field` evidence.
- Evidence fields are immutable after creation.
- `selected_fact_ids` and `excluded_fact_ids` are ordered, unique, disjoint, and bound to the frozen Snapshot.
- Promotion Facts use their own field and database-time validity. Never mix them into selected or excluded facts.
- Application services own explicit transactions; repositories remain commit-free; ports do not import adapters.

## SOP

1. Classify the change as source observation, snapshot, fact evidence, lifecycle transition, Promotion Fact, or selection contract.
2. State the business claim and the database invariant that must protect it.
3. Write the failing test first, including domain and PostgreSQL enforcement when historical integrity is involved.
4. Express states and typed values in the domain; coordinate locks and transactions in application services; keep persistence mechanical.
5. Add an append-only migration and database constraint/trigger when application validation alone cannot preserve the invariant.
6. Map failures to stable codes and RFC 9457 Problem Details without leaking source content.
7. Run targeted unit tests, disposable PostgreSQL integration, architecture import checks, Ruff, and Mypy as required by `docs/development/testing.md`.

## Stop conditions

- Do not let a manual API forge `source_field` provenance.
- Do not update an old Snapshot, locked Fact, or immutable evidence to make a test pass.
- Do not treat successful import, external performance, experiment output, or asset metadata as a confirmed Product Fact.
- Before schema migration, backfill, or data movement, describe the affected rows, rollback boundary, and disposable verification database.
- Hand public URL fetch security to `$factframe-safe-product-import`; hand frozen facts to `$factframe-script-storyboard`; hand external insight to `$factframe-creative-comparison`.

## Completion evidence

Show that cross-Snapshot selection, duplicate/intersecting sets, locked mutation, forged trusted evidence, and Promotion bypass fail closed. State separately what local tests, database integration, CI, and live verification prove.
