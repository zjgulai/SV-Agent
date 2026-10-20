---
name: factframe-readiness
description: Verify and report FactFrame change readiness or acceptance by selecting the smallest sufficient local, database, browser, CI, private-evidence, deployment, or live gate and stating exactly what the evidence proves. Use when asked whether work is complete, releasable, deployed, production-ready, or safe to accept.
---

# FactFrame Readiness

Read `docs/development/testing.md`, the affected context and decision records, current CI/deployment configuration, and [references/gate-matrix.md](references/gate-matrix.md).

## SOP

1. Write the exact claim to prove, such as “the URL import contract passes against a disposable PostgreSQL database” or “this exact commit passed public CI.”
2. Record branch, HEAD, dirty status, changed files, and the authority behind the claim.
3. Select the smallest sufficient layer: static/type/unit; disposable PostgreSQL integration; disposable migration replay; Web unit/build; Compose/Playwright; remote CI for an exact commit; local Private Gate; deployment; live endpoint.
4. Run gates after the relevant change. Historical green results do not validate newer edits.
5. Use a new disposable database for migration downgrade. Use real PostgreSQL/Compose for transaction, trigger, queue, and cross-layer UI contracts.
6. Keep public CI, Private Gate, deployment, live access, commercial approval, and production acceptance as separate evidence.
7. Report the exact command, result, scope, unverified layers, and why each remaining gap matters.

## Stop conditions

- If the dirty worktree differs from the tested commit, do not attribute remote CI to current local changes.
- If `TEST_DATABASE_URL` is not known to be disposable, do not run destructive integration or migration replay.
- If no deployment target, artifact identity, workflow run, or live endpoint is available, stop at local/CI readiness.
- Never use Synthetic CI as a substitute for the real private library, or a capability graph as runtime proof.
- Do not promote “tests pass” into commercial approval, deployment, production acceptance, or long-term availability.

## Report format

Lead with `accepted`, `partially accepted`, or `not accepted`, followed by the proven claim, current evidence, missing gate, and safest next action. Include no private URLs, credentials, local evidence paths, internal receipts, or model private reasoning.
