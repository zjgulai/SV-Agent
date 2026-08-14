# Skill forward-test results

## Baseline

Three fresh no-Skill agents all made safe high-level decisions:

- delayed/95% parse error → recover task and credits before any retry;
- abundant credits/no design → define inventory, baseline, caps, single-variable comparisons and repeats;
- succeeded media/unsupported claims → block publish and audit facts/OCR/audio/product identity.

Because baseline behavior was already safe, no hypothetical discipline rule was added. The Skill focuses on the missing Oumomo feature playbooks and deterministic evidence contract.

## Forward pass 1

Three fresh agents loaded the Skill and handled variants:

| Scenario | Observed behavior | Result |
|---|---|---|
| client timeout + debit + 70% queue | refused retry; created `unknown/recovering` sequence, ledger row and hash-only task rule | pass |
| hidden quote + unavailable upload | returned zero-submit `blocked`, `F`, with single-variable plan and no causal claim | pass |
| succeeded + ASR/OCR fact drift | separated Job/billing pass from factual/publication fail | partial |

The third response used `confidence: high` inside its example despite correctly discussing `F`. The original reference listed evidence levels but did not state that the manifest field is a closed enum, and the validator did not enforce it.

## Refactor

- Added an exact allowed confidence enum to `references/evidence-contract.md`.
- Added `CONFIDENCE_VALUES` and `VERDICT_VALUES` validation.
- Added a failing regression fixture for `confidence: high`, observed failure, then implemented the check.

## Forward pass 2

A fresh agent ran the same factual-drift variant. It returned one manifest object with `confidence: F`, `verdict: fail`, valid 64-character job hash, reconciled quote/credits, recovered-to-succeeded state sequence, artifact metadata and unsupported claims, while blocking publication.

Result: pass.

## Structural and executable validation

- Skill Creator `quick_validate.py`: pass.
- SKILL.md: 470 words, below the 500-word target.
- Evidence validator unit tests: pass.
- Current real evidence directory: `evidence valid`.
