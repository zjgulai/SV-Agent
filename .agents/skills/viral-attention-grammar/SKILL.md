---
name: viral-attention-grammar
description: Adapt an attention-grammar replication when the primary invariant is a timed hook, reveal or cut cadence, caption cadence, visual contrast, or sonic cue; use after pattern abstraction and before contract freeze followed by sequential ScriptVersion and StoryboardVersion compilation.
---

# Attention Grammar

Read `docs/contexts/viral-replication/CONTEXT.md`, `docs/contexts/content-performance-intelligence/CONTEXT.md`, the routing tree, the selected attention workflow `SOP.md`, and the current reference evidence. Attention observations describe expression in a bounded reference; they are not retention, conversion, or performance proof.

## Interface

Input: a stable `ReferenceBundle`, a timed `DecompositionMap`, a `PatternHypothesis` whose only primary mechanism is `attention-grammar`, the target Product Snapshot/Facts, and a frozen `CompiledPatternDefinition`. Output: an attention adaptation plan that records one selected attention component, its invariant function, target surface substitutions, frozen components, Pattern identity, shot/phase anchors, and evidence limits for the `ReplicationContract`.

## Attention component partition

Choose one component by the observation that changes between Control and Variant. The component must be observable from the timed map.

| Component | Invariant function | Evidence to retain |
| --- | --- | --- |
| `hook_trigger` | The opening information promise or question | opening time range, information shown or withheld, surface substitution |
| `reveal_cadence` | Timing and order of visual information or cuts | beat ranges, reveal order, cut boundaries |
| `caption_cadence` | Timing, chunking, and handoff of on-screen text | OCR/availability state, caption ranges, target Fact refs for claims |
| `visual_contrast` | A simultaneous visual relation that makes a difference legible | paired elements, time range, target asset and identity constraints |
| `sonic_timing` | Timing of speech, silence, or authorized sound cues | audio observation, ASR/availability state, rights scope |

`reveal_cadence` is about sequence over time. `visual_contrast` is about a relation visible at the same time. If a candidate needs two rows to change, split it into separate Variants or return `blocked: attention_component_ambiguous`.

## Procedure

1. Require time-ranged observations for the selected component, plus the Hook, visual/audio/text availability states, source refs, rights state, and a frozen Pattern identity (`pattern_key`, version, duration, language, phase/shot plan).
2. State the observed attention function without a performance claim. For example, record that a reference withholds an outcome until a timed reveal; do not state that the reveal improves retention.
3. Classify the reference surface. Exact wording, branded presentation, recognizable performers, protected visual gags, reference audio, and platform-native template elements require substitution or the relevant rights/trend route.
4. Preserve one component's function in a materially different target expression. Bind every target product statement in captions, voiceover, packaging text, and CTA to current `confirmed/locked` Facts; keep non-claim attention language separate.
5. Freeze the selected component as the only changed Creative Dimension. Keep product Snapshot, selected/excluded Facts, duration, language, market, platform, model, target assets, sound policy, budget, and every non-selected attention component equal between Control and Variant.
6. Anchor each attention observation to an existing `shot_index`, `phase_key`, role, and budget window in the frozen Pattern. Compile the target into a fact-bound ScriptVersion and then its StoryboardVersion, preserving the frozen duration and shot budget. Store the attention adaptation plan as contract input; this skill does not add a runtime Creative Pattern, phase, role, RenderJob, media generation, or publishing path.
7. Record results as observations and bounded inferences. A performance metric may stay `not_reported`, `not_collected`, `source_ambiguous`, or observed zero; none of those states may be rewritten into performance proof.

## Stop conditions

- the timed observation that determines the component is unavailable, source-ambiguous, or not reproducible;
- the primary mechanism is actually trend-native, conversion-action, proof-demonstration, experience-pov, or narrative-transformation;
- the target adaptation copies protected surface or lacks a usable rights scope;
- two attention components, duration, language, assets, or another Creative Dimension drift between Control and Variant;
- target captions, voiceover, visual text, or CTA require an unsupported or excluded Product Fact;
- the requested finding claims retention, views, conversion, causal lift, winner status, or production acceptance without its own evidence gate.

## Completion criterion

The adaptation is complete when a reviewer can reconstruct the timed attention function and its frozen Pattern anchors, name the single changed component, verify every target claim and surface substitution, and explain the result's evidence limit without using performance or causal language.
