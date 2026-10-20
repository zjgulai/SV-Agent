# Oumomo Evidence Index

Oumomo materials are clean-room research evidence, not FactFrame business facts. This index routes readers to the right authority without moving or rewriting append-only ledgers and artifacts.

## Design and long-lived knowledge

- [Experiment design](experiment-design.md)
- [Knowledge base](knowledge-base.md)

## Machine evidence

- `outputs/oumomo-reverse-engineering/experiments/experiment-manifest.jsonl`
- `outputs/oumomo-reverse-engineering/experiments/job-state-events.jsonl`
- `outputs/oumomo-reverse-engineering/experiments/credit-ledger.csv`
- `outputs/oumomo-reverse-engineering/artifacts/hashes.csv`
- `outputs/oumomo-reverse-engineering/artifacts/scorecards.csv`

These files retain their original paths because reports, validators and hashes depend on them.

## Findings and procedures

- `outputs/oumomo-reverse-engineering/reports/` contains dated findings and acceptance records.
- `outputs/oumomo-reverse-engineering/sops/` contains executable operating procedures.
- `outputs/oumomo-reverse-engineering/skills/` contains the reusable clean-room runner and its validation contract.

`reports/project-node-review.md` is a historical baseline. Statements that the project lacks outbox recovery, Fact selection or polling recovery have been superseded by current code and [System Architecture](../../architecture/system-overview.md).

## Evidence levels

- **Fact**: directly observed state, local artifact, hash, ledger row or validated source record.
- **Inference**: interpretation supported by named facts and a stated scope.
- **Unknown**: missing, blocked or unmeasured evidence; never silently converted to a negative result.
