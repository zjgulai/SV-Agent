# Capability Fusion Roadmap

## Current closeout

The local fusion baseline now includes the read-only Creative Comparison Projection, Momcozy Aggregate Index, local Private Gate and a selected design for the compare-bound Insight & Performance Decision Brief. The Decision Brief remains design-only: no reviewed package, runtime adapter, database table, tenant/auth, ranking, video generation, RenderJob or publishing was added.

| Priority | Increment | Value | Required evidence/gate | Current disposition |
|---|---|---|---|---|
| P0 | Versioned capability graph and documentation authority | Makes current implementation and evidence navigable | Graph schema/referential validation, docs link audit | Implemented locally; refreshed after structural changes |
| P0 | Momcozy Aggregate Index | Reconciles 244 bundles across batches, statuses and channels | Full-library validator, index schema, no private identifiers | Implemented locally; partial metadata; not runtime-connected |
| P0 | Archive dated capability reports | Prevents old gaps from being read as current truth | Baseline date/status and current replacement links | In this batch |
| P1 | Public synthetic CI + local Private Gate | Makes archive contracts repeatable without exposing real assets | Deterministic fixtures, fixed baseline, closed current release and safe Gate Receipt | Implemented locally; public CI and private data physically separated; deploy/live acceptance absent |
| P1 | Resolve `port → adapter` dependency | Restores intended connector boundary | Test-first type relocation with no API behavior change | Implemented locally; `ParsedProduct` is port-owned and the dependency rule has a regression test |
| P1 | Read-only Insight Projection | Exposes evidence-backed decision context without merging fact stores | Compare-bound Interface, explicit Subject Binding, provenance, permissions, UX and rollback | Design selected; implementation not started; standalone hub deferred |
| P2 | ProviderRun attempt/cost records | Adds provider latency/cost audit separate from creative artifacts | Immutable attempt contract and credential-safe payload digests | New design required |
| P2 | Structured visual-claim constraints | Extends deny-set beyond direct normalized wording | Render lexeme schema and adversarial validator tests | New design required |
| P1 | Read-only Performance Signal Projection | Brings bounded platform/video observations into the comparison Decision Brief without creating Product Facts | Reviewed package schema, separate Snapshot id + digest + evidence-context binding registry, missing-value semantics, ownership, deduplication, permissions and rollback | Design merged into Decision Brief; runtime/package absent |
| P1 | Creative Comparison Lab read projection | Compares two immutable Script Versions through current Fact, validation and Storyboard gates | Approved read-only Interface, stable projection, no external runtime I/O | Implemented locally; CI/deploy/live acceptance absent |
| P1 | Signal-to-experiment compiler | Converts Content Direction into frozen test dimensions | Fact-gated claims, versioned pattern delta, control/comparison contract | Phase 2 gate; runtime absent |
| Out of scope | RenderJob, video generation and social publishing | Material production capability | New approved product, billing, authorization and safety design | Not planned here |

## Recommended sequence

1. Refresh the capability graph and close current local acceptance for the Private Gate.
2. Keep the closed port/adapter dependency guarded: `ParsedProduct` is port-owned and adapters implement the Interface without a reverse import.
3. Keep the completed value decision: the first Insight/Performance product is a compare-bound Decision Brief; do not build a standalone Insight Hub yet.
4. As a separately approved gate, implement only context-specific package contracts, validators and Synthetic Fixtures; keep every runtime evidence section unavailable.
5. After a separate reviewed registry selects a verified public package by one frozen Product Snapshot id + recomputed canonical digest + evidence context, evaluate a default-off local Performance pilot; label it source-scoped until canonical target identity exists and keep private Oumomo/Momcozy evidence outside application runtime.
6. Approve the append-only Creative Comparison Contract, canonical subject ownership and compiler design before producing a single-variable Hook Variant.
7. Reassess ProviderRun cost records and visual claim constraints before any media generation proposal.

## Acceptance rule

An increment is not complete because a plan exists or a graph contains a node. Completion requires its own source facts, tests, data/permission boundary and—when applicable—live or production acceptance evidence.
