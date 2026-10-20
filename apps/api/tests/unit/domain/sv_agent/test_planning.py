import json
from uuid import UUID

import pytest

from app.domain.sv_agent.entities import CreativeDimension, PrimaryMechanism
from app.domain.sv_agent.errors import InvalidRunPlan
from app.domain.sv_agent.planning import (
    MAX_RUN_PLAN_PAYLOAD_BYTES,
    ArtifactAvailableGuard,
    ArtifactHandle,
    CapabilityExecutionMode,
    FactScope,
    FactScopeEvidence,
    FactScopeSatisfiedGuard,
    FactSubjectBinding,
    MediaMode,
    MediaModeGuard,
    PlanInputKind,
    PlanInputRef,
    RouteCandidate,
    RouteIsGuard,
    RunPlan,
    RunPlanStep,
)
from app.domain.sv_agent.runtime_records import ArtifactType

TASK_ID = UUID("00000000-0000-0000-0000-000000000101")
RUN_ID = UUID("00000000-0000-0000-0000-000000000201")
DIGEST = "a" * 64
CATALOG_DIGEST = "c" * 64


def _artifact_handle(*, digest: str = DIGEST, task_revision: int = 1) -> ArtifactHandle:
    return ArtifactHandle(
        artifact_type=ArtifactType.DECOMPOSITION_MAP,
        artifact_id="dm-001",
        version=1,
        digest=digest,
        task_id=TASK_ID,
        task_revision=task_revision,
        run_id=RUN_ID,
        run_revision=2,
        lineage_verified=True,
    )


def _fact_scope_evidence(*, task_revision: int = 1) -> FactScopeEvidence:
    return FactScopeEvidence(
        scope=FactScope.PRODUCT_CLAIMS,
        ref="fact-map:fm-001",
        version=1,
        digest="b" * 64,
        task_id=TASK_ID,
        task_revision=task_revision,
        run_id=RUN_ID,
        run_revision=2,
        lineage_verified=True,
        subject_binding=FactSubjectBinding.PRODUCT,
        claim_mapping_count=1,
        eligible_fact_count=1,
    )


def _input_refs(
    *,
    digest: str = DIGEST,
    task_revision: int = 1,
    catalog_digest: str = CATALOG_DIGEST,
    task_ref: str | None = None,
) -> tuple[PlanInputRef, ...]:
    return (
        PlanInputRef(
            kind=PlanInputKind.TASK_BRIEF,
            ref=task_ref or f"task-brief:{TASK_ID}",
            version=task_revision,
            digest="e" * 64,
        ),
        PlanInputRef(
            kind=PlanInputKind.ROUTE_EVIDENCE,
            ref="decomposition_map:dm-001",
            version=1,
            digest=digest,
        ),
        PlanInputRef(
            kind=PlanInputKind.FACT_SCOPE_EVIDENCE,
            ref="fact-map:fm-001",
            version=1,
            digest="b" * 64,
        ),
        PlanInputRef(
            kind=PlanInputKind.CATALOG,
            ref="workflow-catalog:static",
            version=1,
            digest=catalog_digest,
        ),
    )


def _step(
    step_id: str = "inspect-route",
    order: int = 1,
    *,
    task_revision: int = 1,
    digest: str = DIGEST,
) -> RunPlanStep:
    return RunPlanStep(
        step_id=step_id,
        order=order,
        capability_name="planning.viral.attention-grammar",
        capability_version="1.0.0",
        execution_mode=CapabilityExecutionMode.PLANNING_ONLY,
        guards=(
            ArtifactAvailableGuard(
                handle=_artifact_handle(digest=digest, task_revision=task_revision)
            ),
            RouteIsGuard(
                primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
                creative_dimension=CreativeDimension.HOOK_TRIGGER,
            ),
            FactScopeSatisfiedGuard(evidence=_fact_scope_evidence(task_revision=task_revision)),
            MediaModeGuard(expected_mode=MediaMode.ANALYSIS_ONLY),
        ),
    )


def _plan(
    *,
    task_revision: int = 1,
    digest: str = DIGEST,
    catalog_digest: str = CATALOG_DIGEST,
    limitations: tuple[str, ...] = ("No render, publish, rights, or commercial approval.",),
) -> RunPlan:
    return RunPlan.create(
        task_id=TASK_ID,
        task_revision=task_revision,
        run_id=RUN_ID,
        run_revision=3,
        version=1,
        workflow_name="viral-replication.attention-grammar",
        workflow_version="1.0.0",
        capability_catalog_version="1.0.0",
        capability_catalog_digest=catalog_digest,
        primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
        creative_dimension=CreativeDimension.HOOK_TRIGGER,
        steps=(_step(task_revision=task_revision, digest=digest),),
        input_refs=_input_refs(
            digest=digest,
            task_revision=task_revision,
            catalog_digest=catalog_digest,
        ),
        limitations=limitations,
    )


def test_run_plan_digest_is_stable_and_binds_catalog() -> None:
    first = _plan()
    second = _plan()

    assert first.to_payload() == second.to_payload()
    assert first.plan_digest == second.plan_digest
    assert len(first.plan_digest) == 64
    assert _plan(catalog_digest="d" * 64).plan_digest != first.plan_digest


def test_run_plan_digest_changes_with_task_revision_or_evidence() -> None:
    baseline = _plan()

    assert _plan(task_revision=2).plan_digest != baseline.plan_digest
    assert _plan(digest="b" * 64).plan_digest != baseline.plan_digest


@pytest.mark.parametrize(
    "steps",
    (
        (_step("one", 1), _step("one", 2)),
        (_step("one", 1), _step("two", 3)),
    ),
)
def test_run_plan_rejects_duplicate_or_non_contiguous_steps(
    steps: tuple[RunPlanStep, ...],
) -> None:
    with pytest.raises(InvalidRunPlan):
        RunPlan.create(
            task_id=TASK_ID,
            task_revision=1,
            run_id=RUN_ID,
            run_revision=1,
            version=1,
            workflow_name="viral-replication.attention-grammar",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            capability_catalog_digest=CATALOG_DIGEST,
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
            creative_dimension=CreativeDimension.HOOK_TRIGGER,
            steps=steps,
            input_refs=_input_refs(),
            limitations=("local-only",),
        )


def test_run_plan_fails_fast_when_payload_exceeds_database_limit() -> None:
    with pytest.raises(InvalidRunPlan, match="run_plan_payload_too_large"):
        _plan(limitations=("x" * MAX_RUN_PLAN_PAYLOAD_BYTES,))


def test_run_plan_uses_conservative_jsonb_text_size_at_the_boundary() -> None:
    baseline = _plan()
    payload = baseline.to_payload()
    compact_size = len(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    jsonb_style_size = len(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    original_length = len(baseline.limitations[0])
    filler_length = MAX_RUN_PLAN_PAYLOAD_BYTES - compact_size + original_length

    assert jsonb_style_size > compact_size
    with pytest.raises(InvalidRunPlan, match="run_plan_payload_too_large"):
        _plan(limitations=("x" * filler_length,))


def test_run_plan_rejects_incomplete_inputs_and_route_axis_drift() -> None:
    with pytest.raises(InvalidRunPlan, match="run_plan_input_kinds_invalid"):
        RunPlan.create(
            task_id=TASK_ID,
            task_revision=1,
            run_id=RUN_ID,
            run_revision=3,
            version=1,
            workflow_name="viral-replication.attention-grammar",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            capability_catalog_digest=CATALOG_DIGEST,
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
            creative_dimension=CreativeDimension.HOOK_TRIGGER,
            steps=(_step(),),
            input_refs=(_input_refs()[1],),
            limitations=("local-only",),
        )


def test_run_plan_rejects_task_brief_ref_from_another_task() -> None:
    other_task_id = UUID("00000000-0000-0000-0000-000000000999")
    with pytest.raises(InvalidRunPlan, match="run_plan_task_brief_ref_invalid"):
        RunPlan.create(
            task_id=TASK_ID,
            task_revision=1,
            run_id=RUN_ID,
            run_revision=3,
            version=1,
            workflow_name="viral-replication.attention-grammar",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            capability_catalog_digest=CATALOG_DIGEST,
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
            creative_dimension=CreativeDimension.HOOK_TRIGGER,
            steps=(_step(),),
            input_refs=_input_refs(task_ref=f"task-brief:{other_task_id}"),
            limitations=("local-only",),
        )

    drifted = _step()
    drifted = RunPlanStep(
        step_id=drifted.step_id,
        order=drifted.order,
        capability_name=drifted.capability_name,
        capability_version=drifted.capability_version,
        execution_mode=drifted.execution_mode,
        guards=(
            drifted.guards[0],
            RouteIsGuard(
                primary_mechanism=PrimaryMechanism.TREND_NATIVE,
                creative_dimension=CreativeDimension.TEMPLATE_GRAMMAR,
            ),
            *drifted.guards[2:],
        ),
    )
    with pytest.raises(InvalidRunPlan, match="run_plan_route_guard_mismatch"):
        RunPlan.create(
            task_id=TASK_ID,
            task_revision=1,
            run_id=RUN_ID,
            run_revision=3,
            version=1,
            workflow_name="viral-replication.attention-grammar",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            capability_catalog_digest=CATALOG_DIGEST,
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
            creative_dimension=CreativeDimension.HOOK_TRIGGER,
            steps=(drifted,),
            input_refs=_input_refs(),
            limitations=("local-only",),
        )


def test_route_candidate_requires_verified_decomposition_lineage() -> None:
    with pytest.raises(InvalidRunPlan, match="route_evidence_invalid"):
        RouteCandidate(
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
            creative_dimension=CreativeDimension.HOOK_TRIGGER,
            evidence=ArtifactHandle(
                artifact_type=ArtifactType.FACT_MAP,
                artifact_id="fm-001",
                version=1,
                digest=DIGEST,
                task_id=TASK_ID,
                task_revision=1,
                run_id=RUN_ID,
                run_revision=2,
                lineage_verified=False,
            ),
        )


def test_plan_input_ref_rejects_invalid_digest_and_blank_reference() -> None:
    with pytest.raises(InvalidRunPlan, match="plan_input_ref_invalid"):
        PlanInputRef(
            kind=PlanInputKind.ROUTE_EVIDENCE,
            ref=" ",
            version=1,
            digest="not-a-digest",
        )
