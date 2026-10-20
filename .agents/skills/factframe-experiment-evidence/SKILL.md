---
name: factframe-experiment-evidence
description: Plan, inspect, validate, reconcile, or summarize FactFrame Oumomo clean-room experiment evidence, including manifests, Job observations, credit ledgers, artifacts, scorecards, and findings. Use for local experiment evidence; skip Product Facts, external performance reports, and private Momcozy assets.
---

# FactFrame Experiment Evidence

Read `docs/index.md`, `docs/contexts/experiment-evidence/CONTEXT.md`, `docs/research/oumomo/evidence-index.md`, the current experiment runner/contracts, and [references/experiment-sop.md](references/experiment-sop.md).

## Evidence model

- Freeze the research question, control, variant, dimension, configuration, budget, and stop rule before spending credits.
- A Job observation is factual execution evidence; a Finding is a reviewed interpretation. Keep them separate.
- Queue/progress screens are not terminal evidence. Reconcile the final Job state, credit ledger, artifacts, and observed outputs.
- Artifacts require stable identity and digests. Unknown or unavailable dimensions stay explicit; do not impute a score.
- Credit accounting reconciles reservation, consumption, release, and failure. UI balances alone are insufficient.
- Bound all stored identity and content. Exclude credentials, cookies, signed URLs, private task details, raw full pages, and model private reasoning.
- Findings are scoped to the frozen experiment and observed artifacts. They do not become Product Facts, causal claims, universal winners, or production acceptance.

## SOP

1. Define the decision the experiment may inform and what it cannot establish.
2. Validate the closed manifest, subject identity, control/variant isolation, dimension, budget, and stop conditions.
3. Execute only through the existing deterministic runner or documented manual boundary; do not invent credits or synthetic success.
4. Reconcile terminal Job state, timestamps, ledger movements, artifact inventory, digests, and score availability.
5. Separate the report into observations, bounded inferences, unknowns, anomalies, and next action.
6. When projecting into Creative Comparison, produce a typed experiment package and require the reviewed binding/lifecycle gate from `$factframe-creative-comparison`.
7. Run the relevant runner validator, experiment tests, Ruff, and Mypy. Record whether validation used real local evidence or a committed Synthetic Fixture.

## Stop conditions

Stop on manifest drift, ambiguous subject identity, incomplete terminal state, credit mismatch, missing artifact digest, unsafe value, or unsupported dimension. Never repair a failed observation by editing its historical record. Never report clean-room findings as a verified Product Claim, measured causal lift, commercial approval, deployment, or live production result.
