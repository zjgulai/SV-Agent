# SV-104 Planner and Orchestrator Plan

Status: SV-104A/B implementation, regression and graph review complete; Git/remote CI, durable orchestration and production acceptance remain separate gates
Date: 2026-10-21
Authority: `sv-agent-native-agent-spec.md`, ADR 0007 and `sv-agent-implementation-tickets.md`

## Outcome

SV-104 turns the accepted Task/Run contract and the SV-103 read-tool boundary into a deterministic planning kernel. The first batch intentionally stops before persistence and execution: it produces a version-bound `RunPlan`, returns stable routing or prerequisite decisions, and performs no database write, Tool dispatch, provider call or paid action.

## Scope

### SV-104A — typed planning kernel

- Define a `RunPlan` that is distinct from the creative `ReplicationPlan` artifact.
- Pin Task/Run identity, TaskBrief digest, workflow version, catalog version and digest,
  route ArtifactHandle, explicit FactScope evidence, ordered steps, exact input refs,
  limitations and a server-derived digest.
- Support only five closed guard primitives: artifact available, route is, approval granted, fact scope satisfied and media mode.
- Reject generic JSON guards, expressions, scripts and user-authored DAGs.

### SV-104B — deterministic planner and evaluator

- Use a built-in, versioned catalog covering exactly six Primary Mechanisms.
- Accept typed route candidates derived from verified decomposition evidence; never guess a mechanism from TaskBrief prose.
- Accept explicit Product Claims / No Product Claims evidence; never infer claim scope from Goal Track.
- Select one route, request input for zero candidates, and block with `primary_mechanism_ambiguous` for multiple candidates.
- Evaluate only the next unfinished step with stable priority: `blocked > awaiting_approval > awaiting_input > ready`.
- Bind approval evaluation to the complete ApprovalRequest handle and accept `ready` only
  from a unique, non-stale `VERIFIED_HUMAN` projection. The trusted adapter that creates
  that projection remains deferred.
- Keep evaluation pure and repeatable. Equal inputs must produce equal plan payloads, digests and decisions.
- Validate authoritative context before route cardinality: Task/Run lifecycle, catalog integrity,
  FactScope lineage and Goal Track compatibility, then every RouteCandidate scope. Only valid
  context may return missing, ambiguous or compiled route outcomes.

## Delivery TODO

- [x] Freeze first-batch scope and permission boundary.
- [x] Define test-first acceptance cases.
- [x] Implement closed planning domain values and canonical digest.
- [x] Implement the six-mechanism static catalog and pure planner.
- [x] Implement typed prerequisite snapshots and evaluator.
- [x] Bind TaskBrief, FactScope, catalog, artifact lineage and complete ApprovalRequest identity.
- [x] Reject cross-scope snapshots, conflicting projections, non-prefix completion and oversized plans.
- [x] Pass focused unit, architecture, Ruff and Mypy gates.
- [x] Pass the wider API regression suite.
- [ ] Refresh the capability graph and public-repository safety gates.

## Deferred tickets

The following are explicitly not part of SV-104A/B:

- Run/RunPlan repository writer and Run compare-and-swap;
- durable command-receipt replay and concurrent exactly-once proof;
- Artifact writer and runtime canonical artifact validation;
- verified actor authorization and HumanApproval writer;
- Tool dispatch, Job/Outbox/Celery integration or provider cost;
- public API, Mission Control write path, render, generation, publish, rights, commercial, deployment or production authority.

These require their own design and verification gates. Pure computational idempotency in this batch must not be reported as durable resume.

## Completion gates

1. Focused planning/orchestration unit tests pass.
2. Domain and application architecture tests prove there are no adapter, worker, broker or provider imports.
3. Ruff format/check and Mypy pass for the changed Python surface.
4. Full API tests and existing viral workflow/oracle checks remain green.
5. Documentation states the exact implemented boundary and does not claim persistence or execution.
