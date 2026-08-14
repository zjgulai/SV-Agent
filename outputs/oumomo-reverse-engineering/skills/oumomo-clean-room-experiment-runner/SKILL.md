---
name: oumomo-clean-room-experiment-runner
description: Use when evaluating Oumomo or a similar paid AI commerce-creative product through black-box experiments, especially when jobs can outlive frontend errors, credits must reconcile, outputs need fact/media audits, or OAuth and publishing boundaries must remain untouched.
---

# Oumomo Clean-room Experiment Runner

## Overview

Run paid black-box experiments as recoverable operations with evidence, not as repeated button clicks. Treat Job success, factual acceptance, media quality, billing and publication as separate states.

## Required references

Read both files completely before any paid submission:

- [references/evidence-contract.md](references/evidence-contract.md): manifest, ledger, hashes, confidence and redaction rules.
- [references/feature-playbooks.md](references/feature-playbooks.md): feature-specific controls, gates and stop points.

## Workflow

1. **Define the decision.** State hypothesis, control, one changed variable, repetitions, budget cap and stop conditions.
2. **Freeze input.** Hash local fixtures and canonicalize configuration. Use only public, synthetic, owned or authorized material.
3. **Inspect for free.** Discover fields, model identity, quote visibility, task recovery and output contracts before upload or submit.
4. **Pass gates.** Require a visible immutable quote, reconciled balance, valid comparison and recoverable operation identity. A hidden quote or broken input path is `blocked`, not permission to improvise.
5. **Submit once.** Persist the operation/idempotency key first. Disable retries until the original task and credit ledger are recovered.
6. **Observe factual state.** Record database/project/queue states and task hash. A frontend parse error yields `unknown/recovering`; it does not prove failure.
7. **Audit output.** Separate typed structure, unsupported claims, technical media, ASR/OCR, product identity, continuity and publication readiness.
8. **Record without secrets.** Append manifest, job events, ledger, artifact hashes and findings. Never store raw task IDs, signed URLs, credentials, cookies, private pages or model private reasoning.
9. **Validate after every batch.** Run:

   `python scripts/validate_evidence.py <evidence-root> --max-spend <approved-budget>`

10. **Stop at external authority.** Do not authorize OAuth, bind accounts/products, schedule or publish without a separate explicit approval.

## Decision table

| Observation | Action |
|---|---|
| Frontend error after click | Recover original operation and ledger; do not resubmit |
| Quote hidden or over cap | Mark blocked; zero debit |
| Output succeeded with unsupported claims | Fail factual acceptance; keep Job success unchanged |
| No repeats/control | Report observation only; no causal conclusion |
| Project selector changes route | Record routing defect; do not treat the target feature as tested |
| ASR/OCR/tool unavailable | Mark dimension unavailable; use documented manual fallback |
| OAuth/final publish reached | Stop before the state-changing action |

## Common mistakes

- Equating `succeeded` with accepted or publishable.
- Retrying after an HTML/JSON error without checking credits and queues.
- Comparing models while prompt, reference bytes, resolution or duration differ.
- Calling output diversity “deduplication” without a before/after control.
- Copying vendor claims such as official weighting or fixed success rates into findings.
- Overwriting prior observations instead of appending a corrected terminal state.
