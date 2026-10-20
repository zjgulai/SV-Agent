---
name: viral-reference-intake
description: Establish a bounded, digest-linked ReferenceBundle for a candidate viral reference before decomposition or replication; use for source identity, performance window, playability, refreshability, rights scope, or evidence availability, and stop when the reference cannot be independently reproduced.
---

# Viral Reference Intake

Read `docs/index.md`, `docs/contexts/viral-replication/CONTEXT.md`, `docs/contexts/content-performance-intelligence/CONTEXT.md`, and `docs/research/oumomo/evidence-index.md` before using this skill.

## Interface

Accept a reference locator or local media, an explicit Performance Window when available, platform/market scope, and the intended replication question. Return a `ReferenceBundle` with source identity, digest, capture time, availability state, rights state, observed metrics, limitations, and source references.

## Procedure

1. Freeze the question: what mechanism is being considered, for which subject, platform, market, and window.
2. Record the source locator and a stable content digest. Keep source display, exact payload, and capture timestamp separate.
3. Test only the permitted read path. Record `playable`, `refreshable`, `reproducible`, `unavailable`, or `source_ambiguous`; never infer a ready reference from an iframe, ranking card, or URL alone.
4. Record rights/authorization scope as `confirmed`, `restricted`, or `unknown`. Unknown rights block downstream media use.
5. Separate Performance Observation from the reference media itself. Preserve observed zero, not reported, not collected, and unknown as distinct states.
6. List limitations before routing to decomposition. A high rank or high view count makes a candidate interesting; it does not establish a winner or causal mechanism.

## Stop conditions

- source identity, digest, capture scope, or window is unresolved;
- refresh/playability evidence is unstable or only claimed by UI state;
- rights or authorization is unknown for any planned downstream use;
- the request asks to treat reference speech, captions, or visual inference as Product Fact;
- a fuzzy brand, title, category, or model match is being used as subject binding.

## Completion criterion

The returned `ReferenceBundle` is complete only when every required field has a value or an explicit unavailable state, each observation has a source reference, and a reviewer can reproduce the exact scope without using hidden model inference.
