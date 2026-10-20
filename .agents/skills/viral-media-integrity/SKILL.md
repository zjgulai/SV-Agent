---
name: viral-media-integrity
description: Establish or review a fail-closed media-integrity gate for a frozen viral replication contract, covering artifact traceability, technical media, visible/audible claims, target identity, source-use scope, and originality delta; use when at least one typed ScriptVersion or StoryboardVersion exists and before a ReplicationFinding.
---

# Viral Media Integrity

Read `docs/contexts/viral-replication/CONTEXT.md`, the selected replication workflow `SOP.md`, `07-media-integrity/SOP.md`, `outputs/oumomo-reverse-engineering/sops/ai-media-qc.md`, `factframe-momcozy-assets`, `factframe-script-storyboard`, `viral-fact-mapping`, and the current immutable `ReplicationContract`. This skill creates a document-level quality and admission record. It does not render media, inspect a platform, obtain legal advice or licenses, approve commercial use, publish content, or turn a local Asset Bundle / Aggregate Index / Private Gate receipt into any of those conclusions.

## Interface

Input: frozen `ReplicationContract`, at least one typed fact-bound ScriptVersion or StoryboardVersion ref for bounded preflight, target Product Snapshot/Facts, available Artifact identity/provenance, Media QA observations, target Asset evidence, source-use evidence, and target/reference surface-difference evidence. Output: a `MediaIntegrityRecord` with six independent gate states, stable blockers, human/tool fallback state, a bounded disposition, and a handoff to `ReplicationFinding`.

The standard complete chain compiles ScriptVersion and then StoryboardVersion before MediaIntegrityRecord. Choose `mode=preflight` when no target artifact exists yet; this bounded mode requires at least one of those typed refs, keeps artifact-dependent gates `not_applicable_pending_artifact`, and never becomes an accepted media result. With exactly one version ref, set `storyboard_lineage=null`. Whenever both refs exist, `storyboard_lineage` must repeat the exact StoryboardVersion ref and its declared source ScriptVersion ref with `evidence_scope=declared_artifact_lineage`. Choose `mode=artifact_review` only for a local controlled or evidenced-authorized artifact; it requires both refs, complete lineage, and the controlled artifact. ReplicationFinding rechecks the same lineage, while preflight alone cannot enter that Finding. This lineage is a declarative artifact contract, not runtime database derivation proof.

## MECE integrity-gate partition

Each gate answers one question. All six must be explicitly assessed; a status is not inherited from a neighboring gate.

| Gate | It alone decides | Minimum evidence | It never proves |
| --- | --- | --- | --- |
| `artifact_traceability` | Is this the exact artifact/plan being reviewed? | artifact ID or explicit pending state, SHA-256 when present, source/config/contract digest, terminal/provenance state | technical quality, rights, originality, commercial approval, or publication |
| `technical_profile` | Does the file conform to the frozen technical contract? | probe/manual review state, MIME/bytes/duration/dimensions/fps/codec/audio as applicable, target constraints | claim accuracy, identity, licensing, or platform acceptance |
| `communicative_surface` | Do visible/audible words and symbols comply with Product Truth? | ASR/OCR or explicit dual-human fallback, full-surface Fact map, unsupported/excluded counts | asset ownership, identity continuity, or media aesthetics |
| `target_identity_continuity` | Is the intended target product and its required attributes continuous through the reviewed surfaces? | target asset refs, frame/shot observations or explicit human fallback, identity/continuity findings | technical validity, Product Fact eligibility, or rights |
| `source_use_scope` | Is each planned reference/target use covered by evidence at the required use level? | source class, intended use, analysis/adaptation/reuse state, evidence refs, unresolved scope | legal approval, commercial approval, platform permission, or originality |
| `originality_delta` | Can an independent reviewer reconstruct how target expression differs from protected/identity-bearing source surface? | target text/visual/audio substitutions, source identity exclusions, comparison method, review state | a legal non-infringement opinion, commercial approval, or publish permission |

`source_use_scope` asks what evidence permits a planned use. `originality_delta` asks whether target and source surfaces have been independently differentiated. Keep them separate even when both are blocked. `commercial_disposition=approved`, a valid Aggregate Index, a Private Gate receipt, successful `ffprobe`, an AI similarity opinion, or model review alone cannot pass either gate.

## MediaIntegrityRecord

```text
MediaIntegrityRecord
├── schema_version: sv.media-integrity-record.v1
├── mode: preflight | artifact_review
├── replication_contract_ref / adaptation_package_ref
├── script_version_ref / storyboard_version_ref
├── storyboard_lineage: declared_artifact_lineage | null
├── controlled_artifact_ref: controlled_media | null
├── gate_checks: artifact_traceability / technical_profile / communicative_surface
│   / target_identity_continuity / source_use_scope / originality_delta
├── fallback_strategy
├── blockers / unknowns / evidence_limits
└── disposition: blocked | proceed_with_limits | ready_for_next_gate
```

Every state must include its evidence source or an explicit `unavailable` / `not_applicable_pending_artifact` value. Preserve tool output, human-review identity/role and scope, and digest references as typed evidence; do not store raw private media, local private paths, credentials, signed URLs, receipts, or private reviewer reasoning in tracked workflow documents.

## Procedure

1. Recheck the immutable contract digest, one creative dimension, same-Snapshot Fact sets, Pattern, duration, language, market, platform, target assets, source-use plan, rights, and budget before inspecting media. Contract drift blocks every downstream integrity conclusion.
2. Select mode. `preflight` records the acceptance plan and source/target substitution evidence without fabricating Artifact, `ffprobe`, ASR, OCR, frame, or rendered-media results. A one-ref preflight keeps `storyboard_lineage=null`; any record with both version refs must declare their exact lineage. `artifact_review` requires both version refs, the matching lineage, an artifact identity, safe provenance, and a controlled/authorized review path.
3. Assess `artifact_traceability` separately: identify the exact artifact or pending state, its hash/digests, terminal state, and bounded provenance. An Asset Bundle may support its own target-material traceability only; it cannot authorize a reference surface or a generated media output.
4. Assess `technical_profile` against the frozen contract. Use a controlled technical probe or recorded human fallback. A tool that is unavailable remains unavailable unless the fallback records who reviewed which bounded attribute and why that is sufficient for this review.
5. Assess `communicative_surface` over all visible and audible fields: voiceover, captions, OCR, packaging, price, title, tag, actions, acceptance copy and promotion. Use `viral-fact-mapping`; every accepted product claim binds to a current same-Snapshot `confirmed`/`locked` Fact, and excluded/unsupported counts must be zero.
6. Assess `target_identity_continuity` independently from Fact mapping: inspect product color, package, component, quantity, material, logo and cross-shot identity only as the frozen acceptance criteria require. Record unknowns rather than using visual resemblance as a Product Fact.
7. Assess `source_use_scope` for each reference audio/template/text/person/brand/asset and each target asset. State intended use precisely: analysis, adaptation, reuse, embedding, redistribution, commercial use, or publishing. Evidence insufficient for the planned use is a blocker; never infer scope from visibility, playability, technical QA, source hash, Asset Bundle validity or model output.
8. Assess `originality_delta` with a reviewer-independent comparison method. Reconstruct target text/visual/audio substitutions and source identity exclusions; record the review state and the `VR-P4-004` evidence limit. A model may surface candidates but cannot be the sole approval authority.
9. Produce a bounded disposition. `ready_for_next_gate` only means the complete local integrity record may enter the next named gate; it does not mean media accepted for commercial or external use. Send observations, blockers, unknowns, evidence level and next action to `viral-experiment-evaluation` and `factframe-readiness`.

## Stop conditions

- contract digest, Product Snapshot/Fact mapping, artifact identity, target assets, terminal state, or review scope cannot be reconstructed;
- a required technical/ASR/OCR/identity check is unavailable and there is no bounded independent human fallback;
- an unsupported, excluded, expired promotion, or unreviewed visible/audible claim appears;
- product identity or continuity drifts from frozen target requirements;
- analysis-only, unknown, or mismatched source-use evidence is used to justify adaptation, reuse, embedding, redistribution, commercial use, or publishing;
- a source identity surface appears in target output without a traceable substitution/difference record;
- a single model or mechanical similarity score is treated as originality, legal, commercial, platform, or publication approval;
- a QA disposition, Aggregate Index, Private Gate receipt, tool success, local fixture, CI, deployment, or graph is presented as a different proof layer;
- the request adds RenderJob, provider media generation, account, billing, trend discovery, platform API, upload, social publishing, or production acceptance scope.

## Completion criterion

The record is complete when an independent reviewer can recheck all six gate states against the same frozen contract, distinguish tool evidence from human fallback and unavailable states, locate every target claim and source-surface substitution, reproduce the bounded disposition, and name the next gate without claiming license, originality approval, commercial approval, platform compatibility, publishing, or production acceptance.
