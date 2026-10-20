# Integrated Capability Model

## Purpose

本模型把 Leap Content Performance Intelligence、FactFrame 运行能力、Oumomo clean-room evidence 和 Momcozy local asset intelligence 组织成一条可审计决策链。融合发生在术语、关系、证据引用和决策视图；四个上下文的事实权威与运行时继续隔离。

```text
bounded product / performance source
  → immutable observation
  → Creative Signal or governed Product Fact
  → fact-gated, frozen creative hypothesis
  → durable execution
  → validated script/storyboard
  → controlled experiment
  → traceable asset
  → insight card
  → ship / revise / stop decision
```

## Capability layers

| ID | Capability | Current evidence | Authority | Status | Momcozy decision value |
|---|---|---|---|---|---|
| C01 | Bounded product intake | Manual form and public Schema.org Product connector with SSRF controls | PostgreSQL Product Source/Snapshot | Implemented | Establishes which product information may enter the system |
| C02 | Immutable fact governance | Fact states, evidence kind, locator, confidence and append-only guards | PostgreSQL + migration constraints | Implemented | Separates usable claims from proposed or rejected content |
| C03 | Fact selection and exclusion | Ordered selected facts and explicit deny-set | Script Generation | Implemented | Makes creative priority and prohibited claims reviewable |
| C04 | Versioned creative contract | Duration-sensitive pattern, phase/shot plan, audience and Promotion Fact slots | Frozen Pattern Definition | Implemented | Turns a content hypothesis into a repeatable test contract |
| C05 | Typed provider boundary | Strict request/output schema and server-owned visible copy | Application service + provider adapter | Implemented | Limits model freedom to fact-bound claim surfaces |
| C06 | Deterministic validation | Structure, timeline, factuality, exclusion, creative contract and prohibited claims | Validation Report | Implemented | Produces a blocking gate instead of subjective approval prose |
| C07 | Append-only creative versions | Script Version, fact-bound child revision, comparison and export | PostgreSQL | Implemented | Preserves why a Momcozy script changed and which facts moved |
| C08 | Reliable asynchronous execution | Job events, outbox lease, dead letter, retries and execution fencing | PostgreSQL; Redis is transport only | Implemented | Distinguishes broker trouble from business failure and prevents false completion |
| C09 | Storyboard review gate | Frozen Storyboard, zero-cost typed preview and approval events | PostgreSQL | Implemented | Enables pre-render review without claiming a video was generated |
| C10 | Clean-room capability experiments | Manifest, job events, credit ledger, hashes and scorecards | Oumomo evidence files | Implemented locally | Tests provider behavior and cost without contaminating Product Facts |
| C11 | Traceable commercial asset archive | Asset Bundle, Recipe, Provenance, QA and hashes | Local Momcozy asset library | Implemented locally | Makes generated images/videos reviewable and recoverable |
| C12 | Capability relationship graph | File/function/class/document nodes and validated edges | `.ua/knowledge-graph.json` | Generated | Helps reviewers traverse evidence and find missing or reversed dependencies |
| C13 | Insight storyline | Evidence-to-decision narrative and comparison matrix | Living product docs | Implemented in this documentation layer | Converts isolated outputs into a decision sequence |
| C14 | Momcozy aggregate library view | Deterministic whole-workspace JSON/Markdown projection with immutable digest releases over 244 validated Bundles, ledgers, scoped index and frozen plan | Local ignored Momcozy library + `tools.momcozy_assets.aggregate_index` | Implemented locally; partial metadata; not runtime-connected | Reports exact status and coverage distributions without guessing missing evidence; blocked/failed builds cannot replace the current release |
| C15 | Cross-platform performance intelligence | Seven-day Momcozy report with exact totals, platform breakdown and cumulative trends | Dated Leap public report evidence | Verified externally; method-limited | Identifies where performance and interaction are concentrated without claiming causality |
| C16 | AI video and storyboard decomposition | Ranked Content Directions plus Hook/Clip/CTA, voice-over, visual, scene and technique fields | Leap getter payload and bounded evidence summary | Verified externally; quality-limited | Converts observed videos into testable creative dimensions while surfacing language, unit and completeness defects |
| C17 | Fact-gated signal handoff | Content Performance context, claim disposition and ADR boundary | Living docs + existing confirmed/locked validation | Defined; not productized | Prevents external selling points or rankings from becoming scripts, patterns or Product Facts without evidence |
| C18 | Creative Comparison Lab read projection | Deep Module, stable GET Projection, production compare page and rollback flag | Existing Script identity and one PostgreSQL Fact observation shared by both candidates | Implemented locally; external evidence unavailable; not deployed | Makes Control/Variant differences, current Fact blockers and evidence gaps reviewable without introducing a new fact store or external connector |
| C19 | Private asset validation gate | Projection-digest-bound baseline, double fresh compile, descriptor-bound canonical current release validation and bounded Gate Receipt | Ignored local Momcozy library + `tools.momcozy_assets.private_gate`; public CI uses synthetic fixtures only | Implemented locally; scheduled local validation; not runtime-connected | Detects same-shape evidence substitution, blocked, drifted, stale or corrupt library state without exposing or modifying private assets |
| C20 | Insight & Performance Decision Brief | Compare-bound v2 design with explicit Subject Binding, typed evidence sections, missing-value semantics, reviewed-package provenance and rollback | Selected design + dated public evidence; no runtime package | Designed; implementation not started | Places Observation, Inference, Unknown, Action and Guardrail beside one immutable comparison without treating brand similarity, ranking or external claims as truth |

## Module insight value

| Module | What it knows | High-value question it can answer | Data fusion rule | Failure boundary |
|---|---|---|---|---|
| Product Source/Snapshot | What was observed from a bounded source at a point in time | Which inputs were actually available when a claim was formed? | Join only through Snapshot identity and digest | Never retain raw full pages or treat latest as implicit |
| Product Fact ledger | Which claims are proposed, confirmed, rejected or locked | What may the brand safely say, and what must remain excluded? | Only confirmed/locked facts support accepted claims | Confidence alone is not approval |
| Creative Pattern compiler | Which narrative topology, shot roles and timing were frozen | Is a creative result comparable to another run? | Compare only versions bound to explicit Pattern Definition | Registry defaults cannot reinterpret old generations |
| Job/Outbox execution | What was queued, delivered, retried or dead-lettered | Did the operation fail as a business outcome or only as delivery? | Use database event sequence, not Redis result state | A 95% UI state or broker send is not completion |
| Script validator | Why content is acceptable or blocked | Which exact field violates fact, timing or creative policy? | Findings remain attached to an immutable Script Version | Model prose cannot waive blocking findings |
| Storyboard review | Whether a validated script is ready for local pre-render review | Is there enough frozen evidence to approve the storyboard without spending on media? | Recheck live fact eligibility before approval | Approval is not render, legal or publishing permission |
| Oumomo experiments | Observed external provider behavior, cost and artifact quality | Which provider capability is reproducible under a frozen configuration? | Findings support roadmap only; never import them as Product Facts | Small samples and blocked observations remain scoped |
| Momcozy asset archive | Which local assets exist and how they were produced/reviewed | Which candidate can be reused, revised or held for a channel? | Use Bundle ID, hashes, provenance and explicit index scope | Technical validation is not commercial approval |
| Momcozy Private Gate | Whether the approved local library, fixed baseline and current release agree now | Is the evidence surface technically consistent enough for a reviewer to continue? | Treat each Gate Receipt as time-scoped technical evidence; keep public synthetic CI separate | A receipt is not commercial approval, deployment or publication permission |
| Content Performance Intelligence | Which videos, platforms and creative directions were associated with performance in a bounded window | Which signal deserves a controlled creative test, and which reported claim must be blocked? | Preserve report subject/window/precision; map selling points through confirmed/locked facts | Ranking is not causality; missing, zero and rounded values remain distinct |
| Insight & Performance Decision Brief | Which bounded evidence applies to this exact Control/Variant review, and what is the smallest safe next step? | Should the reviewer revise, collect evidence, prepare a test or stop? | Use a separate reviewed registry to select a verified package by frozen Snapshot id + recomputed canonical digest + evidence context; until canonical subject identity exists this is source-scoped hypothesis context, not proof of target Market/Model/Variant | Current runtime has no package reader, tenant/RBAC or safe private evidence channel; M5 and bottle-care evidence cannot be brand-only joined |
| Capability graph | Where implementation, docs, tests and evidence connect | Which capability lacks a code/test/evidence edge or violates layer direction? | Every claim must link back to an authoritative node | Graph presence is not proof of runtime or production acceptance |

## Insight card contract

Every decision-facing insight should contain:

1. **Question** — the decision being supported.
2. **Subject and window** — brand, product, channel, configuration and observation time.
3. **Observed facts** — direct source records with identifiers or hashes.
4. **Inference** — a separately labeled interpretation.
5. **Unknowns** — missing source, sample, time window or approval.
6. **Capability path** — relevant graph nodes and evidence chain.
7. **Action** — ship, revise, test, collect or stop.
8. **Guardrail** — conditions that invalidate the action.

Private model reasoning is never part of the card. Only inputs, typed outputs, findings and factual execution state are retained.

For the selected compare-bound Decision Brief, `ship` is not an available action. `reviewable` means the comparison may continue to human review; it is not render, commercial or publishing approval.

## Known structural findings

- The connector boundary is now directionally closed: `ProductConnector` owns `ParsedProduct`, `SchemaOrgProductConnector` implements that Interface, and an architecture test rejects any future `app.ports → app.adapters` import. The DTO remains an ingress contract rather than a Product Fact or domain entity.
- The local Aggregate Index reconciles 244/244 structurally valid Bundles: 235 image and 9 video; QA disposition is 36 approved, 198 hold, 2 rejected and 8 revision-needed. Batch metadata covers 235, Channel 12 and Concept Group 198; 9 early Bundle batch assignments, 232 Channels, 46 Concept Groups and every independent Commercial Approval remain unknown. Batch E-A's 396-credit balance is a historical scoped fact; Batch F closes the subsequent 396-to-0 spend.
- `project-node-review.md` contains dated gaps that have since been implemented. It remains research history and must not be read as current capability truth.
- Storyboard preview is implemented; RenderJob, video generation and publishing remain outside scope.
- The verified Leap slice covers 22 videos in one Germany product workspace over seven days. Its Top 10 hold 86.09% of views, but the report omits collection, deduplication, ranking, snapshot and model-review methods; it is a Creative Signal source, not representative market research.
- Leap's AI analysis contains language, unrelated-text, unit and storyboard-completeness defects. Those failures validate the need for FactFrame's schema, language, unit, fact and evidence-support gates rather than weakening them.
- The selected Decision Brief design extends the existing comparison seam rather than creating a generic Insight endpoint. The current Leap bottle-care subject conflicts with the M5 private asset baseline at Product Family/Model grain; a separate reviewed registry must select a verified package by frozen Snapshot id + recomputed canonical digest + evidence context, and that selection remains source-scoped until canonical target identity is proven.
