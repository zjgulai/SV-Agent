---
name: viral-trend-native
description: Adapt a trend-native replication when an external trend signal, shared meme frame, challenge/template grammar, or observed audio function is the sole primary mechanism; use after pattern abstraction and before Script/Storyboard compilation and contract freeze.
---

# Trend Native

Read `docs/contexts/viral-replication/CONTEXT.md`, the routing tree, the selected trend-native workflow `SOP.md`, and the current reference evidence. This skill turns a bounded external observation into a document-level contract. It does not discover live trends, obtain audio/template rights, verify platform compatibility, create media, activate a template, upload, publish, or establish originality approval.

## Interface

Input: a stable `ReferenceBundle`, a timed `DecompositionMap`, a `PatternHypothesis` whose only primary mechanism is `trend-native`, the target Product Snapshot/Facts, and a frozen `CompiledPatternDefinition`. Output: a document-level `TrendNativePlan` that records one selected trend component, its observable function and target substitution, three frozen components, a frozen `TrendAdmissionRecord`, Pattern anchors, prohibited surface copy, and evidence limits for the `ReplicationContract`.

## Trend component partition

Choose the one component that differs between Control and Variant. These rows are mutually exclusive: they answer which external signal is bounded, how its shared meaning works, how a template is structured, or what sound does in time. Rights, platform compatibility, and originality review are admission gates, never the selected creative component.

| Component | It alone decides | Required observation | It does not prove |
| --- | --- | --- | --- |
| `trend_signal_binding` | Which external signal was observed, where, for whom, and in which bounded window | signal kind/ID, source refs, platform, market, language, observed-at, window, availability | current popularity, recommendation, entitlement, compatibility, or publishability |
| `trend_semantic_frame` | Which shared premise, turn, social context, or participation logic carries the observed meaning | timed premise/turn, audience context, source refs, target Fact refs or `not_a_product_claim` | permission to copy source wording, identity, branded surface, or unsupported product benefit |
| `template_grammar` | Which role order, transition, or shot relation makes an observed challenge/template legible | segment/time range, role, transition, observed function, template ref or `not_present`, surface class | that a template is installed, callable, reusable, or platform-authorized |
| `audio_function` | Which observed cue, beat, pause, turn, or synchronization role sound plays | audio observation/time ranges, cue function, source audio ref, availability, target sound policy | download, embedding, AI imitation, music license, or platform publishing permission |

If a candidate changes two rows, split it into separate Variants or return `blocked: trend_component_ambiguous`. A reference that merely contains a trend tag or background audio is not trend-native unless the expression loses its primary function without it.

## Frozen TrendAdmissionRecord

Every `TrendNativePlan` must freeze a `TrendAdmissionRecord`; it is a document-level evidence record, not a runtime entitlement or external integration.

```text
TrendAdmissionRecord
├── rights_scope
│   ├── reference_analysis_state
│   ├── adaptation_scope_state
│   ├── source_audio_reuse_state
│   ├── template_usage_state
│   └── evidence_refs
├── platform_compatibility
│   ├── target_platform / market / locale
│   ├── observed_constraints
│   ├── assessment_state: not_assessed | constraints_observed | external_verification_required
│   ├── execution_capability: not_implemented
│   └── external_action_requested: false
└── originality_delta
    ├── target_text / visual / audio substitutions
    ├── source_identity_exclusions
    ├── review_state: evidence_collected | deferred_to_vr_p4_004
    └── formal_gate: VR-P4-004
```

`reference_analysis_state` only permits bounded observation. `constraints_observed` is not `platform_compatible`; `review_state` is not an originality approval. A target Asset Bundle, technical QA status, Aggregate Index result, or Private Gate receipt may support target-material traceability but never proves source audio/template rights, platform permission, commercial approval, or publishing permission.

## Procedure

1. Require source locator/digest, capture time, platform, market, language, observation window, availability and rights state for each trend observation. State only what was observed in that window; do not call it currently popular, recommended, or available without its own evidence.
2. Confirm that the trend is the unique primary mechanism. Route to narrative, proof, experience, attention, or conversion when that mechanism remains intact after the incidental trend surface is removed. If two mechanisms cannot be isolated, stop with `primary_mechanism_ambiguous`.
3. Classify named audio, original wording, recognizable people, branded visuals, platform-native stickers, challenge template identifiers, and protected role/cut combinations as `prohibited_surface_copy` until an applicable scope is evidenced. Playability, visibility, a tag, or an AI summary never grants reuse permission.
4. Choose exactly one trend component, describe its observable function without a performance claim, and freeze the other three. Bind target product claims to same-Snapshot `confirmed`/`locked` Facts; keep trend language that is not a product claim separate.
5. Build the frozen `TrendAdmissionRecord`: record analysis/adaptation/audio/template evidence states, observed platform constraints, `execution_capability=not_implemented`, no external action request, target-side substitutions, source identity exclusions, and an originality review deferred to `VR-P4-004` unless a separate formal gate exists.
6. Preserve the chosen function only through materially distinct, target-controlled expression. The source audio must not become target execution input; target sound policy must be independently authorized or explicitly unavailable. Anchor the selected component to existing `shot_index`, `phase_key`, role, duration, language, market, platform, target assets, rights scope, and budget in the frozen Pattern.
7. Compile only the existing fact-bound Script/Storyboard pattern. Provider input remains limited to approved facts and required generation parameters; it must not receive reference URLs, named source audio/template instructions, rights assessments, platform actions, or source identity surfaces. This skill does not add a trend/audio/template runtime field or claim to have tested provider exclusion for one.
8. Freeze Control/Variant with one `changed_creative_dimension`; preserve the complete `TrendAdmissionRecord`, all non-selected trend components, Snapshot, Facts, Pattern, duration, language, market, platform, model, target assets, audio policy, rights, and budget. Record only observations, bounded inferences, unknowns, and next action.

## Stop conditions

- trend is not the unique primary mechanism, or it cannot be separated from another primary mechanism;
- signal identity, platform/market/language/window, source refs, capture state, or reproducibility is unresolved;
- a named audio, template, identity surface, source wording, or branded visual would be reused without a matching evidenced scope;
- the target sound substitution, template provenance, or target surface difference cannot be reconstructed;
- platform compatibility is asserted from local format observations, or any template activation, upload, account, publishing, or external platform action is requested;
- originality review is claimed as passed before the separate `VR-P4-004` formal gate;
- Control/Variant changes more than one trend component or also changes Product Truth, Pattern, duration, language, market, platform, model, target assets, audio policy, rights, or budget;
- the requested conclusion claims current trend status, entitlement, compatibility, media quality, distribution, conversion, causal lift, winner status, commercial approval, live, or production acceptance without its own evidence gate.

## Completion criterion

The adaptation is complete at the local contract level when a reviewer can reconstruct the bounded observation, name exactly one trend component, recheck the frozen admission record and target substitutions, verify every target claim and Pattern anchor, reproduce the one-field contract diff, and state explicitly that source rights, platform verification, originality approval, media generation, and publishing remain outside this skill.
