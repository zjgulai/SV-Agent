---
name: viral-conversion-action
description: Adapt a conversion-action replication when the primary invariant is one objection-resolution, promotion-contract, CTA-invitation, or action-path component; use after pattern abstraction and before Script/Storyboard compilation and contract freeze.
---

# Conversion Action

Read `docs/contexts/viral-replication/CONTEXT.md`, `docs/contexts/product-truth-script/CONTEXT.md`, the routing tree, the selected conversion workflow `SOP.md`, and the current reference evidence. This skill governs a bounded creative mechanism; it does not create a checkout, link, account, billing, video-generation, or publishing capability.

## Interface

Input: a stable `ReferenceBundle`, a `DecompositionMap`, a `PatternHypothesis` whose only primary mechanism is `conversion-action`, the target Product Snapshot/Facts, an optional Promotion Fact, and a frozen `CompiledPatternDefinition`. Output: a document-level `ConversionActionPlan` recording one selected component, its evidence, all frozen conversion context, Fact/Promotion bindings, CTA policy, action-path state, and evidence limits for the `ReplicationContract`.

## Conversion component partition

Choose the one component that changes between Control and Variant. The rows answer four different questions and are mutually exclusive; a reference expression that materially changes more than one row must freeze the others or split into separate Variants.

| Component | It alone decides | Required binding and current limit |
| --- | --- | --- |
| `objection_resolution` | How to resolve one observed decision friction | Every product answer binds to an eligible same-Snapshot Product Fact; it does not set an offer, CTA invitation, or destination. |
| `promotion_contract` | What commercial term is available now | A separate active Promotion Fact is required; it is not selected/excluded and may not become provider input. If no promotion applies, record `not_applicable`. |
| `cta_invitation` | What the user is invited to do and where the final CTA appears | The frozen Pattern's `cta_policy` and final CTA role are the authority. The provider cannot choose CTA copy, policy, or promotion placement. |
| `action_path` | Which controlled handoff follows the invitation | Record an authorized path binding or `not_applicable`. Current runtime has no persisted action-path field, URL, checkout, or external execution contract; do not represent one as implemented. |

For example, “click now to get 20% off” changes both `promotion_contract` and `cta_invitation`; it is not a one-component Variant. A reference may contain a CTA without making conversion-action its primary mechanism.

## Procedure

1. Require the reference's objection, offer, CTA, and any claimed path to have source refs, availability state, rights scope, and a non-causal description. Route away if its main value is narrative relation, proof device, POV/experience, attention grammar, or an external trend/template.
2. Name one selected conversion component and classify all remaining conversion elements as frozen context. State the observed function without saying it improves conversion, sales, or performance.
3. For `objection_resolution`, bind every product answer in voiceover, captions, packaging text, titles, tags, action, and acceptance text to `confirmed` or `locked` Facts from the frozen Snapshot. An objection is not evidence for an unsupported answer.
4. For `promotion_contract`, load the Promotion Fact through the separate `promotion_fact_id` field. Require same-Snapshot identity, `confirmed` or `locked` state, its current typed value shape, and activity at PostgreSQL `statement_timestamp()`. Keep it out of `selected_fact_ids`, `excluded_fact_ids`, and the provider request.
5. For `cta_invitation`, use only the frozen Pattern policy: `server_generic_no_offer` or `server_promotion_final_cta`. The latter can render the active Promotion Fact only in the final `cta` role; server-owned copy determines the CTA surface. For `action_path`, retain a subject/market-bound authorized handoff or `not_applicable`; do not infer an external destination from wording.
6. Compile the existing fact-bound Script/Storyboard pattern. Preserve the frozen Pattern identity, duration, language, market, platform, model, target assets, rights scope, selected/excluded Fact order, budget, and every non-selected conversion component. The provider receives selected facts and generation parameters only; the server applies Promotion and CTA policy after provider output.
7. Freeze Control/Variant with one `changed_creative_dimension`, produce an isolation report, and record any result as observations, bounded inferences, unknowns, and next action. A missing platform metric remains missing; no local contract or fixture proves conversion lift, winner status, or production acceptance.

## Stop conditions

- the primary mechanism is not `conversion-action`, or its objection/offer/CTA/path evidence cannot be separated from another primary mechanism;
- a product answer lacks a same-Snapshot `confirmed`/`locked` Fact, or an excluded Fact reappears;
- a Promotion Fact is selected/excluded, belongs to another Snapshot, has an invalid value, is not active at database time, or is used with a Pattern that lacks `server_promotion_final_cta`;
- Promotion, CTA policy, audience policy, server-owned copy, or a free-form action destination enters provider input;
- Promotion renders outside the final `cta` role, generic and promotion CTA policies are conflated, or a required action path has no authorized binding;
- the Control/Variant changes more than one conversion component or also changes Product Truth, Pattern, duration, language, market, platform, model, assets, rights, or budget;
- the requested conclusion claims conversion, revenue, causal lift, winner status, checkout completion, publishing, or production acceptance without a separate evidence gate.

## Completion criterion

The adaptation is complete when a reviewer can name the one changed conversion component, recheck every product and promotion binding against the frozen Snapshot and database-time validity, verify final CTA ownership and action-path state, reproduce the one-field contract diff, and state the result's evidence limit.
