---
name: viral-experiment-evaluation
description: Reconcile a frozen replication contract with execution state, artifacts, media checks, ledger, scorecard, and bounded findings; use after a Control/Variant run and never to infer production or causal success from one sample.
---

# Viral Experiment Evaluation

Read `docs/contexts/viral-replication/CONTEXT.md`, `factframe-experiment-evidence`, `outputs/oumomo-reverse-engineering/sops/single-variable-experiment.md`, and `outputs/oumomo-reverse-engineering/sops/ai-media-qc.md` before evaluating a run.

## Interface

Input: immutable `ReplicationContract`, execution timeline, terminal Job state, ledger, Artifact inventory/digests, Media QA, and independent scorecard. Output: `ReplicationFinding` with observations, bounded inferences, unknowns, anomalies, evidence level, next action, and limitations.

## Procedure

1. Verify contract digest and Control/Variant isolation before reading quality or performance results.
2. Reconcile terminal state from the authoritative persistence layer. Progress percentage, UI completion, or a broker result is not a terminal business fact.
3. Reconcile quote, reservation, consumption, release, failure, and ledger digest. Unknown or mismatched accounting blocks effect interpretation.
4. Verify every Artifact has stable identity, source/config digest, hash, and safe local provenance. Preserve failed or blocked observations instead of editing history.
5. Run technical, ASR/OCR, product identity, claim, rights, and continuity gates independently. `unavailable` stays unavailable.
6. Separate observations from inferences and unknowns. Report group variance and group difference when repeats exist; with n=1 report only the observed run.
7. Choose only a bounded next action: `revise`, `collect_evidence`, `test`, `hold`, or `stop`. Never return winner, causal lift, universal formula, commercial approval, or production acceptance without a separate gate.

## Stop conditions

- contract drift or more than one changed variable;
- incomplete terminal state, credit mismatch, missing Artifact digest, or unknown provenance;
- unsupported claim, product identity failure, rights failure, or critical media tool unavailable;
- the requested conclusion exceeds evidence scope.

## Completion criterion

The Finding is complete only when every conclusion points to a reconciled observation, every unknown is explicit, every blocker has a stable code and next action, and proof level is separated across local, CI, private, deployment, live, and production contexts.
