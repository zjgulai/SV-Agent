---
name: factframe-momcozy-assets
description: Inspect, validate, aggregate, publish, or privately verify FactFrame's local Momcozy Asset Bundles, Aggregate Index releases, current manifest, Synthetic CI, and Private Gate. Use for the Momcozy asset evidence plane; skip media generation, commercial approval, deployment, and social publishing.
---

# FactFrame Momcozy Assets

Read `docs/index.md`, `tools/momcozy_assets/README.md`, ADR 0006, current contracts/tests, and [references/asset-modes-and-proof.md](references/asset-modes-and-proof.md).

## Choose an explicit mode

### `synthetic-ci`

Validate committed Synthetic Fixtures and production tooling. It cannot inspect or prove the real Momcozy library.

### `publish-aggregate`

This is a write operation. Use only an exact approved root containing the scoped marker. Reject symlinks, broad roots, unknown schemas, duplicate identities, path/hash/status conflicts, sensitive projections, and source drift. Canonically render JSON/Markdown into staging, `fsync`, atomically publish an immutable digest release, require byte identity for an existing digest, and switch the current manifest only after the full release succeeds. Any block or I/O failure preserves the prior current manifest.

### `private-gate`

This is a read-only verification of the ignored real library against a fixed tracked baseline. Traverse owned non-writable directory descriptors; require regular, current-owner, single-link, bounded leaf files; validate the closed manifest, paths, hashes, schema, internal digests, and Markdown rerender; fresh-compile twice; re-read current and root identity. Return only safe state/count receipts or a stable failure code.

## Invariants

- The real library stays local and ignored; public CI may use only committed Synthetic Fixtures.
- A Bundle is the atomic validation unit. Aggregate releases and current manifests are deterministic and append-only.
- Fail closed and preserve the previous current release.
- A gitignored output is not automatically garbage. Never delete or rewrite evidence without an exact evidence-aware boundary.
- Structural validity, QA, commercial approval, deployment, and production acceptance are separate states.
- Do not expose local paths, automation IDs, media, manifests, internal hashes, credentials, or private receipts in tracked docs or ordinary projections.
- Asset evidence cannot create or confirm a PostgreSQL Product Fact.

## Stop conditions and validation

Stop when the root is not explicitly approved, the marker mismatches, permissions are broad, a symlink appears, baseline/current diverges, fresh compile blocks, or sources change. Do not auto-repair or update the baseline; baseline changes require separate review. Run the existing Momcozy unit suite, Ruff, and explicit-package Mypy. State whether evidence is synthetic, a newly published aggregate, or a read-only Private Gate receipt.
