---
name: viral-fact-mapping
description: Map reference and target content claims to an immutable Product Snapshot and confirmed/locked Product Facts while preserving unsupported, excluded, promotion, and unknown states; use before script, storyboard, proof, or media acceptance.
---

# Viral Fact Mapping

Read `docs/contexts/product-truth-script/CONTEXT.md`, `factframe-product-truth`, the relevant claim audit SOP, and the current `ReplicationContract`. This skill protects the seam between creative hypothesis and Product Truth.

## Interface

Input: target Product Snapshot, Product Facts, selected/excluded sets, Promotion Facts when applicable, and reference/target claim candidates. Output: a typed claim map and deny-set report.

## Procedure

1. Enumerate every visible or audible claim: voiceover, caption, title, tag, visual direction, action, acceptance text, OCR, packaging, price, comparison, safety, performance, and promotion.
2. Map each candidate to a Fact ID from the same Snapshot. Classify as exact, approved paraphrase, unsupported, excluded, expired promotion, or unknown.
3. Require `confirmed` or `locked` state for acceptable product claims. Confidence, title similarity, reference wording, model output, and visual implication are not approval.
4. Keep Promotion Facts outside selected/excluded Product Facts and verify market, currency, value, validity window, and database time.
5. Search the full visible surface for excluded-fact resurrection. An excluded claim in visual, action, title, tag, caption, OCR, or ASR is blocking.
6. Emit deterministic findings with source refs and stable blocker codes. Never “repair” a missing fact by inventing a safer synonym.

## Stop conditions

- Snapshot identity or Fact state is unavailable;
- a manual/source provenance distinction is forged;
- an unsupported claim is needed for the reference mechanism;
- an excluded or expired claim reappears;
- promotion is rendered without an active Promotion Fact;
- the mapping relies on model reasoning or reference performance as evidence.

## Completion criterion

The mapping is complete only when claim precision is 100% for accepted claims, unsupported and excluded occurrences are explicitly counted, and every unresolved item has a next evidence action or a blocking disposition.
