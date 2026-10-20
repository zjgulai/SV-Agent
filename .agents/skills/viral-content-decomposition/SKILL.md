---
name: viral-content-decomposition
description: Decompose an accepted ReferenceBundle into a timed, evidence-linked DecompositionMap covering hook, tension, proof, experience, visual/audio/text grammar, CTA, claims, and unknowns; use before pattern abstraction or script adaptation.
---

# Viral Content Decomposition

Read `docs/contexts/viral-replication/CONTEXT.md`, the selected workflow `SOP.md`, and the current reference evidence before starting. This skill observes the reference; it does not decide Product Truth or generate target copy.

## Interface

Input: a complete `ReferenceBundle` and an allowed local/read-only inspection surface. Output: a `DecompositionMap` with timed observations and source refs.

## Procedure

1. Preserve the source digest and inspect the reference in time order.
2. Record time ranges for Hook, Pain/Tension, Intervention, Proof, Experience, Result, CTA, and transition beats. If a beat is absent, record `not_present`; do not invent it.
3. Record visual grammar: framing, camera movement, product visibility, props, scene, action, cut rhythm, and continuity cues.
4. Record audio/text grammar: speech language, ASR observations, music/sound cues, captions, OCR, on-screen text, and their availability states.
5. Extract every product or performance claim as a `claim_candidate` with exact source location and disposition: `reported`, `supported_by_target_fact`, `unsupported`, `ambiguous`, or `not_a_product_claim`.
6. Mark surface features that must be adapted or rights-reviewed. Do not copy protected wording, identity, music, or brand presentation into the hypothesis.
7. Propose a primary mechanism only from observable evidence. If two mechanisms are inseparable, return `primary_mechanism_ambiguous` and route to contract design instead of choosing by intuition.

## Stop conditions

- ASR/OCR or visual inspection is unavailable for a field that determines the mechanism;
- the map contains unbounded prose instead of timed observations;
- a model-generated summary is being used without source location;
- reference claims are being promoted into target Product Facts;
- the primary mechanism cannot be isolated as one Creative Dimension.

## Completion criterion

The `DecompositionMap` is complete only when every observed beat, claim, surface feature, unknown, and limitation is timed or explicitly unavailable, and a second reviewer can reconstruct the proposed primary mechanism from the map alone.
