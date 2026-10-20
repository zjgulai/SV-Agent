---
name: viral-replication-contract
description: Freeze Control, Variant, one Primary Replication Mechanism, one Creative Dimension, Product Truth, configuration, budget, rights, stop conditions, and acceptance gates for a replication experiment; use before execution or comparison.
---

# Viral Replication Contract

Read `docs/contexts/viral-replication/CONTEXT.md`, the selected workflow `SOP.md`, `factframe-creative-comparison`, `factframe-experiment-evidence`, and `factframe-product-truth` before creating a contract.

## Interface

Input: `ReferenceBundle`, `PatternHypothesis`, target Product Snapshot/Facts, and the proposed execution configuration. Output: immutable `ReplicationContract` and a canonical configuration digest.

## Procedure

1. Name the decision and the exact subject identity. Do not use brand/title/category similarity as binding.
2. Select exactly one primary mechanism and one `changed_creative_dimension`.
3. Define Control and Variant. Every other field—Product Snapshot, selected/excluded Facts, language, market, platform, duration, model, input assets, count, resolution, budget, and rights—must be equal or explicitly declared as a separate contract field.
4. Freeze the ordered `selected_fact_ids` and disjoint `excluded_fact_ids`. Promotion Facts remain separate and time-bound.
5. Define terminal states, unknown recovery, budget/ledger expectations, media QA gates, rights gates, and evidence level before execution.
6. Compute a canonical digest over the complete contract. Do not allow a provider or UI to mutate the contract after submission.
7. Produce an isolation report listing every Control/Variant difference. If there is more than one unapproved difference, return blocked.

## Stop conditions

- no stable subject identity or Product Snapshot;
- no confirmed/locked Facts for required product claims;
- selected and excluded sets are missing, intersecting, reordered, or cross-Snapshot;
- more than one Creative Dimension changes;
- model/provider/quote/input/rights cannot be frozen;
- the requested conclusion is causal, universal, commercial, or production-level without its own gate.

## Completion criterion

The contract is complete only when a second agent can regenerate the same canonical digest from the written fields, identify the single permitted difference, and enumerate every condition that would block execution or downgrade the finding.
