---
name: factframe-creative-comparison
description: Inspect, design, or change FactFrame read-only Creative Comparison, compare-bound Decision Briefs, typed external evidence packages, subject binding, and comparison UI projections. Use for comparing immutable Script Versions or integrating performance, experiment, or asset insight into that surface.
---

# FactFrame Creative Comparison

Read `docs/index.md`, `docs/contexts/content-performance-intelligence/CONTEXT.md`, `docs/product/insight-performance-projection-design.md`, current comparison code/tests, and [references/implementation-gates.md](references/implementation-gates.md). For external packages also read [references/evidence-binding.md](references/evidence-binding.md).

## Detect the implemented gate first

Do not treat a design as runtime. Inspect code, tests, migrations, routes, and Web negotiation before choosing work:

- v1 compares two immutable Script Versions and exposes Product Truth/readiness/differences.
- D1 defines typed external package contracts, validators, Synthetic Fixtures, and unavailable/in-memory readers only.
- D2 descriptor readers, reviewed binding registry, v2 Projection/UI, and content negotiation require their own implementation gate.
- D3 identity/RBAC/private evidence and D4 standalone Insight remain separate future scope unless current code proves otherwise.

## Invariants

- Control and Variant are distinct, belong to one Script Generation, and share the frozen Snapshot, ordered selected/excluded facts, Promotion, and Pattern.
- Read current Facts for both candidates in one PostgreSQL statement and at one database timestamp.
- Product Truth failure blocks the comparison; external evidence failure stays isolated and cannot alter blockers, differences, validation, or Storyboard state.
- Preserve stored validation, live validation, fact-contract findings, Storyboard preflight, and external evidence as distinct planes.
- Without an append-only comparison contract, single-variable status is `unverified`. Return all semantic differences; fact-binding and unexpected changes block readiness.
- Keep product truth, performance, experiment, and asset evidence as four typed sections.
- Preserve `missing`, `unknown`, `not_reported`, `not_collected`, `source_ambiguous`, observed zero, and `unavailable` as different meanings.
- Bind a package by reviewed `{Snapshot id, recomputed canonical digest, evidence context}`. Brand, title, category, or model similarity is never enough.
- A reviewed source selection is partial/source-scoped; only canonical identity is exact.
- Decision Brief text is deterministically compiled from server-owned `text_key` and typed args. Do not call an LLM at request time.
- Do not calculate winner, score, priority, or causal lift. `reviewable` means eligible for human review only.
- Public projections never expose paths, signed URLs, cookies, task IDs, private Bundle references/hashes, credentials, or quarantine details.

## SOP

1. Validate subject identities and the shared frozen generation contract.
2. Read one current Product Truth observation and compute both candidates' fact eligibility.
3. Preserve and project stored/live validation and Storyboard preflight independently.
4. Compile every semantic difference in stable order.
5. Build Product Truth blockers before consulting external evidence.
6. Apply only the currently implemented gate: v1 returns honest unavailable sections; D1 changes contracts/validators/readers only; D2 first validates reviewed bindings, digests, scope, lifecycle, safe values, and quarantine behavior.
7. Compile readiness and Decision Brief through fixed rule tables, then scan output for sensitive values and compute a canonical digest.
8. Keep Web tabs as local lenses over one Projection request.

## Stop conditions and proof

Reject fuzzy subject binding, evidence upgrades, request-time inference, direct ignored-directory scans, write effects in comparison GETs, and unsupported v2 negotiation. Verify duplicate/cross-generation identities, fact degradation, missing semantics, row-order determinism, no I/O or writes, package lifecycle/quarantine, sensitive-value exclusion, and one-request Web behavior. Public fixtures do not prove real Leap, private Momcozy, deployment, or production acceptance.
