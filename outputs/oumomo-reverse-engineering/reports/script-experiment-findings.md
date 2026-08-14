# Viral script experiment findings

## Current status

All 12 planned script experiments completed successfully. Browser control recovered through a fresh Chrome tab; S-B01 was not resubmitted. Every run reconciled exactly after one click. Total script debit: 120 credits. Current balance: 860.

## First confirmed result

The 30-second baseline produces a coherent four-phase, five-shot TikTok shooting script in about 29 seconds. Its commercial structure is strong, but its factual contract is weak: the model freely strengthens product claims and invents visible details across every user-visible field.

The highest-value reverse-engineering insight is therefore not the prompt alone. A production clone needs:

1. a fact-bound input claim set;
2. typed phase and shot roles;
3. exact claim references for voiceover and captions;
4. server-owned visual, action, title and tag wording;
5. a validator that rejects unsupported benefits before persistence.

This matches the current P0 architecture and is a defensible improvement over the observed product behavior.

## Baseline repeat: S-B02

The repeat took 48.162 seconds and again produced four phases and five shots. Structure is stable enough to treat the generator as a constrained shooting-script template rather than unconstrained prose: scenario pain point, product intervention, usage demonstration, then result and CTA.

The factual failure is also stable. S-B02 introduced electrolyte wording, instant recovery, instant dissolving, sweet taste, green packaging, blue liquid and `clean energy` without a typed evidence boundary. Titles and tag families varied only slightly from S-B01, which suggests high prompt/template anchoring but no effective product-claim validator.

S-B03 confirms the conclusion while exposing one structural variance: the generator used four shots instead of five. The four-phase arc remained identical. Across the three baselines, elapsed time ranged from 29.003 to 48.162 seconds, phases stayed at four, shots ranged from four to five, and every output added unsupported product wording.

## Duration sensitivity: S-D15

Changing only duration from 30 to 15 seconds reduced the script from four phases to three, but kept four shots. The generator merged product introduction into the mixing demonstration instead of simply deleting a shot. This is a useful replicable rule: duration controls phase compression, while a minimum shot budget appears to remain.

The factual failure did not improve. S-D15 retained instant-effect claims and invented visual states, so a clone cannot treat shorter duration as a safety mechanism.

S-D45 expands the pattern to five phases and eight shots. Across the duration series, the observed scaling rule is 15s → 3 phases/4 shots, 30s → 4 phases/4–5 shots, and 45s → 5 phases/8 shots. Longer duration adds a dedicated taste/result block and a separate CTA, but also creates a larger surface for unsupported claims. Duration should therefore be implemented as a typed structure budget, not as a free-form word-count target.

## Script-type sensitivity: S-T01

口播种草型 changes the rhetorical engine rather than only renaming phases. It uses an opinion hook, first-person endorsement and one-shot-per-phase delivery. The resulting evidence model is testimonial rather than demonstrative, so a production clone should require explicit support not only for product facts but also for comparative and personal-experience statements.

The output contains a narrow medical-claim caution in its execution notes, yet still invents numerous commercial benefits. This is evidence of a prompt-only guardrail rather than a validator.

S-T02 demonstrates that script-type schemas can create risk by construction. The misconception/consequence/correction frame invented price, sugar, blood-sugar, crash, savings and healthy-hydration claims to fill required rhetorical slots. A safe clone must either require evidence for each comparative slot or disable this pattern when the fact snapshot lacks the necessary data.

## Language sensitivity: S-L01

普通话 is a distinct generation template rather than a translation pass. With every other control unchanged, the output doubled to eight shots, localized the shopping-cart direction and introduced culturally familiar comparison targets and idioms. This means language belongs in the creative-contract version and needs separate evaluation coverage.

The localized output also created new factual risks that did not appear verbatim in the English baseline, including coffee-induced shaking and ineffective Red Bull. A post-generation translation architecture would be easier to govern than allowing each language prompt to regenerate product claims independently.

## Audience sensitivity: S-A01

The `大学生` audience label rewrote scenario, props, time of day, titles, tags and price sensitivity. Audience is therefore a high-leverage creative control, but the observed implementation treats it as an invitation to infer unstated persona facts. A clone should separate audience-owned scene adaptation from product claims and require evidence before introducing affordability or comparative messaging.

## Promotion propagation: S-P01

The exact test input `[EXPERIMENT ONLY] 10% test discount` was transformed into six live-sounding 10% offer mentions, while the protective marker disappeared entirely. The generator added `right now`, `today` and explicit shopping CTA language. This is a direct commercial-integrity failure.

A clone should not expose promotion as unconstrained text. The minimum safe contract needs a promotion ID, value type, amount, currency or percentage, region, validity window, source and current status. Rendering must remain server-owned and generation should fail closed when the offer is not active.

## Selling-point order: S-O01

Moving the aesthetic point from third to first did not make it the leading derived claim or the first product proof. The output regenerated its own ordered list and even added a fourth point from the product title. This contradicts the UI promise that drag order controls priority.

Order should be modeled as a binding list of fact IDs and tested end to end. If the model may choose a different narrative order, the UI must say so and the actual chosen order must be persisted separately from the user's requested order.

## Selling-point deletion: S-F01

Deleting the aesthetic/blue-color point did not remove that concept from generation. The output used blue powder or liquid five times in English, required a visible color transformation and regenerated additional core claims from the product title. The delete control therefore changes an editable list but does not act as a negative generation constraint.

For a clone, deleted or excluded fact IDs must be carried into generation and validation as an explicit deny-set. The server should reject any visible copy or shot requirement that reintroduces a denied claim.

## Script-matrix conclusion

The useful engine is a small family of typed rhetorical templates with duration budgets, not the unconstrained prose itself. The observed stable core is:

1. select a phase schema from script type;
2. allocate a phase/shot budget from duration and language;
3. adapt scenes, props and titles to audience;
4. render product proof and CTA copy;
5. derive titles and tags from the resulting narrative.

The product's critical weakness is that steps 2–5 freely regenerate claims from product title, inferred category, audience and rhetorical needs. User edits, order and deletion are weak hints, and promotion text is treated as authoritative. The highest-value clone is therefore a fact-bound template engine plus deterministic validation, not a prompt replica.

## Cross-cutting frontend error

The same `Unexpected token '<'` signature was logged on multiple script routes even when generation later succeeded. The URL-video experiment confirmed the broader failure pattern: an HTML response can be parsed as JSON while a paid backend operation is actually accepted. A clone needs content-type checks, RFC 9457 errors, idempotent submission and durable operation recovery.

## Unpaid public-sample contract check (2026-08-12)

Two public Top-5 samples expose a consistent read-only result contract without spending credits. Each contains: video metadata; a product card with image, title, category and selling points; an ordered phase structure; and a timed execution script. Every shot carries a phase label, shot title, voiceover, visual, action, captions and a phase-acceptance shot.

This independently supports the P0 typed `phase -> shot -> visible fields -> acceptance` model. It is useful for reconstructing the presentation schema and duration budgeting, but not as a factual source: both samples include benefit, safety, or audience assertions that cannot be verified from the visible product card. The clone must retain the schema while binding every user-visible product claim to locked facts and rejecting unsupported creative copy.

## Regression: control persistence remains absent (2026-08-12)

Two fresh default 30-second English scenario-test runs kept the four-phase arc but varied from four to eight shots. Both regenerated unsupported packaging colour, instant-dissolving, taste, hydration, energy and competitor-comparison copy. Deleting the third auto-extracted selling point before a third run did not suppress the corresponding colour concept: the result repeated blue-drink wording six times and also retained unrelated unsupported claims.

The result is a direct product requirement, not a prompt-tuning suggestion: selected and excluded fact IDs must be immutable inputs to generation and validation. An excluded fact must be a deny-set for every user-visible output field, while an accepted factual claim needs an explicit fact reference. The current P0 fact gate already provides the safe half of this solution; the next Web/API increment is fact selection, ordering and exclusion rather than more free-form prompt controls.
