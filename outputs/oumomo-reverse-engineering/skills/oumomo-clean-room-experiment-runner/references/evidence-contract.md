# Evidence contract

## Contents

- Evidence levels
- Experiment manifest
- Job events
- Credit ledger
- Artifact and media evidence
- Sensitive-data boundary
- Acceptance rules

## Evidence levels

- `F`: directly observed UI field, quote, balance, state, response or downloaded artifact.
- `I-H`: high-confidence inference supported by repeated controlled outputs.
- `I-M`: plausible inference with incomplete isolation or low sample size.
- `U`: unknown or blocked.
- `Vendor claim`: product marketing not independently reproduced.

Never upgrade an inference because it sounds architecturally plausible.
The manifest `confidence` value MUST be exactly one of `F`, `I-H`, `I-M`, `U`, or `Vendor claim`; labels such as `high` are invalid.

## Experiment manifest

Store one JSON object per line. Required for every record:

```text
experiment_id
feature
verdict: pass | fail | blocked | inconclusive
confidence
submit_count
```

Required when `submit_count > 0`:

```text
quote_before_submit
credit_before
credit_after
ledger_delta
```

Add when observed:

```text
control_experiment_id
config_digest
single_changed_variable
visible_model_or_mode
job_id_hash
state_sequence[]
terminal_state
artifact_sha256
duration/width/height/fps/codec
unsupported_claims[]
quality_scores
notes
```

Use SHA-256 for task identity. Do not retain the raw task value.

## Job events

Append the observed sequence; never replace ambiguity with a guessed terminal state.

```json
{
  "experiment_id": "X-B01",
  "job_id_hash": "<64-lowercase-hex>",
  "state_sequence": ["submitted", "frontend_error", "recovered", "succeeded"],
  "terminal_state": "succeeded"
}
```

If a later observation resolves an earlier cutoff, update the consolidated manifest and retain the intermediate state in `state_sequence`.

## Credit ledger

Required columns:

```text
experiment_id,observed_at,feature,quote,credit_before,credit_after,delta,terminal_state,notes
```

Invariants:

- `credit_before + delta = credit_after`.
- Each row's `credit_before` equals the previous row's `credit_after`.
- Sum of negative deltas never exceeds the approved budget.
- Refunds/adjustments are appended; original charges are not overwritten.
- `submit_count`, Job count, output count and debits reconcile.

## Artifact and media evidence

Store only owned, synthetic or authorized outputs. Record:

```text
relative path, sha256, bytes, mime
duration, width, height, fps, codecs, audio present
frame-grid/asr/ocr/shot-boundary references
fact, product-identity and quality scores
```

Keep score dimensions independent. Leave a value empty when it was not tested. A technical pass does not imply factual, visual or publication acceptance.

## Sensitive-data boundary

Forbidden fields at any depth:

```text
authorization, cookie, headers, password, phone,
raw_job_id, signed_url, token, job_id
```

Also exclude credentials, account identifiers, private URLs, full raw pages, databases, Redis state and model private reasoning. Persist typed inputs/outputs, visible prompts when needed for audit, findings and execution facts.

## Acceptance rules

An experiment is complete only when:

1. Configuration and changed variable are reconstructable.
2. Quote, submit count, task identity and balance reconcile.
3. Terminal state is observed or explicitly remains unknown/blocked.
4. Artifacts have hashes and technical metadata when produced.
5. Unsupported claims and untested dimensions are explicit.
6. Confidence matches evidence strength.
7. The validator passes.
