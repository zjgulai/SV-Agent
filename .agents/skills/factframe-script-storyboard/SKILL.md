---
name: factframe-script-storyboard
description: Build or change FactFrame frozen Script Generation, Creative Pattern, provider boundary, deterministic validation, fact rebind, Storyboard preflight, preview, and approval workflows. Use for authoring and review after Product Truth is established; skip cross-version insight and media publishing.
---

# FactFrame Script and Storyboard

Read `docs/index.md`, `docs/contexts/product-truth-script/CONTEXT.md`, current generation and storyboard decisions, then the mode-specific reference: [generation-and-revision.md](references/generation-and-revision.md) or [storyboard-review.md](references/storyboard-review.md).

## Frozen contract

- Freeze Snapshot, ordered selected/excluded facts, compiled Pattern, provider/model, prompt contract, duration/language/audience inputs, and input digest before execution.
- Reinterpret historical work using its stored Pattern Definition, never the current registry.
- Send only selected facts and necessary generation parameters to the provider.
- Visual, action, acceptance, phase purpose, titles, tags, shooting list, audience copy, and Promotion CTA are server-owned.
- Promotion data never enters the provider request and may only appear through the final server-owned CTA rule.
- Every visible Product Claim binds exactly to an eligible Fact in the frozen Snapshot. Excluded Facts are a deny-set across all visible fields.
- Preserve stored validation, current live validation, fact-contract findings, and Storyboard preflight as distinct signals.
- Script Versions, Storyboards, and Approval Events are append-only. Approval does not imply render, media generation, or publication.

## Choose one mode

### Generation

Compile and freeze the Pattern; validate facts and Promotion; create Job, initial event, generation, and Outbox intent transactionally; run the provider; overwrite all server-owned fields; reread facts before saving; run the full deterministic validator; append a Script Version.

### Fact rebind

Require an acceptable parent and exactly one binding per shot. Allow only facts selected by the frozen generation. Copy parent structure, rebuild claim-bearing copy and identifiers on the server, rerun frozen Pattern/excluded/Promotion validation, and append an idempotent child version.

### Storyboard review

Load the frozen generation, immutable version, and current facts. Merge distinct validation planes. Create only from a ready preflight; lock and recheck facts at create and approve; derive deterministic preview; compute stale status at read time without mutating historical approval.

## Stop conditions and proof

- Never fix a provider mismatch by surrendering server-owned copy.
- Never accept free-form rebind text, timeline changes, partial shot bindings, or stale fact approval.
- Do not add RenderJob, account, billing, ranking, video generation, or social publishing scope.
- Use `$factframe-reliable-execution` for queue/delivery semantics and `$factframe-creative-comparison` for comparing immutable versions.
- Verify changed Pattern/language/duration plans, validation failures, provider request exclusion, fact degradation at each boundary, append-only database triggers, deterministic preview, and relevant API/Web behavior.
