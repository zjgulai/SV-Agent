from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvArtifactRecord,
    SvDecisionEventRecord,
    SvRunPlanRecord,
    SvRunRecord,
    SvRuntimeLineageLinkRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvToolRunRecord,
)
from app.application.sv_agent_mission_control import (
    MissionArtifact,
    MissionBlocker,
    MissionControl,
    MissionRun,
    StageKey,
    StageStatus,
    _next_action,
    _stages_for,
)
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.artifact_contracts import bind_artifact_digest
from app.domain.sv_agent.entities import (
    CreativeDimension,
    GoalTrack,
    PerformanceWindow,
    PrimaryMechanism,
    RightsState,
    RunState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import JournalIntegrityError, TaskNotFound
from app.domain.sv_agent.runtime_records import (
    ArtifactStatus,
    ArtifactType,
    EvidenceLevel,
    ProofLevel,
)

TASK_ID = UUID("25000000-0000-0000-0000-000000000001")


def _task() -> Task:
    return Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which baby reaction mechanism should Momcozy test?",
            subject="Momcozy baby reaction story",
            platform=TargetPlatform.TIKTOK,
            market="US",
            language="en-US",
            performance_window=PerformanceWindow(
                start=date(2026, 10, 1),
                end=date(2026, 10, 20),
                timezone="America/Los_Angeles",
            ),
            stop_condition="Stop before provider execution or publication.",
            initial_rights_state=RightsState.ANALYSIS_ONLY,
        ),
        id=TASK_ID,
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )


async def _persist_task(
    session: AsyncSession,
    task: Task,
    *,
    active_run: SvRunRecord | None = None,
) -> None:
    session.add(
        SvTaskRecord(
            id=task.id,
            current_revision=task.revision,
            active_run_id=active_run.id if active_run is not None else None,
            summary={"subject": task.brief.subject},
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    session.add(
        SvTaskRevisionRecord(
            task_id=task.id,
            revision=task.revision,
            goal_track=task.brief.goal_track.value,
            decision_question=task.brief.decision_question,
            subject=task.brief.subject,
            platform=task.brief.platform.value,
            market=task.brief.market,
            language=task.brief.language,
            performance_start=task.brief.performance_window.start,
            performance_end=task.brief.performance_window.end,
            performance_timezone=task.brief.performance_window.timezone,
            stop_condition=task.brief.stop_condition,
            initial_rights_state=task.brief.initial_rights_state.value,
            brief_digest=canonical_digest(task.brief),
            created_at=task.created_at,
        )
    )
    await session.flush()
    if active_run is not None:
        session.add(active_run)
        await session.flush()


def _canonical_replication_contract_payload(
    *,
    task_id: UUID,
    run_id: UUID,
    artifact_id: UUID,
    created_at: datetime,
    status: str = "awaiting_approval",
) -> dict[str, object]:
    def artifact_ref(artifact_type: str, index: int) -> dict[str, object]:
        return {
            "artifact_id": f"{artifact_type}-{index}",
            "artifact_type": artifact_type,
            "task_ref": str(task_id),
            "run_ref": str(run_id),
            "version": 1,
            "content_digest": f"{index:064x}",
        }

    replication_plan_ref = artifact_ref("replication_plan", 1)
    fact_map_ref = artifact_ref("fact_map", 2)
    decomposition_map_ref = artifact_ref("decomposition_map", 3)
    return bind_artifact_digest(
        {
            "schema_version": "sv.replication-contract.v1",
            "artifact_id": str(artifact_id),
            "artifact_type": "replication_contract",
            "task_ref": str(task_id),
            "run_ref": str(run_id),
            "version": 1,
            "status": status,
            "input_refs": [replication_plan_ref, fact_map_ref, decomposition_map_ref],
            "source_refs": [],
            "subject_binding": {
                "state": "not_applicable",
                "product_snapshot_id": None,
                "product_snapshot_digest": None,
                "market": None,
                "locale": None,
                "limitations": ["No product claims are in scope."],
            },
            "content_digest": "0" * 64,
            "evidence_level": "fact",
            "proof_level": "local",
            "limitations": ["Local evidence only."],
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
            "supersedes_artifact_id": None,
            "replication_plan_ref": replication_plan_ref,
            "fact_map_ref": fact_map_ref,
            "decomposition_map_ref": decomposition_map_ref,
            "primary_mechanism": "experience-pov",
            "selected_component": "experience_pov",
            "frozen_components": [],
            "claim_scope": "no_product_claims",
            "control_id": "control-001",
            "variant_id": "variant-001",
            "changed_dimension": "experience point of view",
            "frozen_configuration": {
                "language": "en-US",
                "market": "US",
                "platform": "tiktok",
                "duration_seconds": 20,
                "model": "document-only",
                "material_scope": ["target-assets-only"],
                "execution_budget": {
                    "max_variants": 1,
                    "max_iterations": 2,
                    "max_duration_seconds": 30,
                    "stop_on_violation": True,
                },
            },
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
            "stop_conditions": ["Stop on contract violation."],
            "acceptance_gates": ["Human approval is required."],
            "rights_state": "analysis_only",
            "approval_ref": "approval-001",
            "immutable": True,
        }
    )


def _run_plan_payload(
    *,
    task: Task,
    run_id: UUID,
    run_revision: int,
    brief_digest: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    input_refs = [
        {
            "kind": "task_brief",
            "ref": f"task-brief:{task.id}",
            "version": task.revision,
            "digest": brief_digest,
        },
        {
            "kind": "route_evidence",
            "ref": "decomposition_map:route-candidate",
            "version": 1,
            "digest": "1" * 64,
        },
        {
            "kind": "fact_scope_evidence",
            "ref": "fact-scope:no-product-claims",
            "version": 1,
            "digest": "2" * 64,
        },
        {
            "kind": "catalog",
            "ref": "workflow-catalog:static",
            "version": 1,
            "digest": "c" * 64,
        },
    ]
    return (
        {
            "schema_version": "sv-run-plan/v1",
            "task_id": str(task.id),
            "task_revision": task.revision,
            "run_id": str(run_id),
            "run_revision": run_revision,
            "version": 1,
            "workflow_name": "viral-replication.experience-pov",
            "workflow_version": "1.0.0",
            "capability_catalog_version": "1.0.0",
            "capability_catalog_digest": "c" * 64,
            "primary_mechanism": "experience-pov",
            "creative_dimension": "experience_pov",
            "steps": [
                {
                    "step_id": "inspect-reference",
                    "order": 1,
                    "capability_name": "planning.viral.reference-intake",
                    "capability_version": "1.0.0",
                    "execution_mode": "planning_only",
                    "guards": [],
                }
            ],
            "input_refs": input_refs,
            "limitations": ["Planning only."],
        },
        input_refs,
    )


async def _persist_artifact_with_lineage(
    session: AsyncSession,
    *,
    task: Task,
    run: SvRunRecord,
    artifact_id: UUID,
    payload: dict[str, object],
    created_at: datetime,
) -> None:
    payload_digest = canonical_digest(payload)
    session.add(
        SvArtifactRecord(
            artifact_id=artifact_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run.id,
            run_revision=run.revision,
            artifact_type="replication_contract",
            schema_version=str(payload.get("schema_version", "sv.replication-contract.v1")),
            status=str(payload.get("status", "awaiting_approval")),
            evidence_level=str(payload.get("evidence_level", "fact")),
            proof_level=str(payload.get("proof_level", "local")),
            payload=payload,
            payload_digest=payload_digest,
            input_refs=list(payload.get("input_refs", [])),
            created_at=created_at,
        )
    )
    verification_payload = {"verification": "exact-runtime-binding"}
    session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID(f"28500000-0000-0000-0000-{artifact_id.int % 10**12:012d}"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run.id,
            run_revision=run.revision,
            source_ref_type="run",
            source_ref_id=str(run.id),
            source_version=run.revision,
            source_digest="a" * 64,
            target_ref_type="replication_contract",
            target_ref_id=str(artifact_id),
            target_version=1,
            target_digest=payload_digest,
            relation_type="derived_from",
            verifier_name="mission-control-test",
            verifier_version="1.0.0",
            verification_payload=verification_payload,
            verification_digest=canonical_digest(verification_payload),
            created_at=created_at,
        )
    )
    await session.flush()


async def test_mission_control_projects_a_saved_task_without_inventing_a_run(
    db_session: AsyncSession,
) -> None:
    task = _task()
    await _persist_task(db_session, task)

    projection = await MissionControl(db_session).inspect(task.id)

    assert projection.schema_version == "sv-mission-control/v1"
    assert projection.authority == "postgresql"
    assert projection.task.task_id == task.id
    assert projection.task.stop_condition == task.brief.stop_condition
    assert projection.run is None
    assert projection.plan is None
    assert projection.current_artifact is None
    assert projection.tool_runs == ()
    assert projection.tool_runs_truncated is False
    assert len(projection.stages) == 7
    assert projection.stages[0].status is StageStatus.ACTIVE
    assert all(stage.status is StageStatus.WAITING for stage in projection.stages[1:])
    assert projection.current_stage == "reference_admission"
    assert [blocker.code for blocker in projection.blockers] == ["RUN_NOT_STARTED"]
    assert projection.next_safe_action.interaction_intent == "request_plan"
    assert projection.next_safe_action.execution_available is False
    assert projection.explanation.citations[0].ref == f"task:{task.id}:r1"


async def test_mission_control_returns_task_not_found(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(TaskNotFound):
        await MissionControl(db_session).inspect(TASK_ID)


async def test_mission_control_projects_only_current_bounded_authoritative_state(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000001")
    now = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=3,
        state=RunState.AWAITING_APPROVAL.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)

    plan_input_refs = [
        {
            "kind": "task_brief",
            "ref": f"task-brief:{task.id}",
            "version": task.revision,
            "digest": canonical_digest(task.brief),
        },
        {
            "kind": "route_evidence",
            "ref": "decomposition_map:route-candidate",
            "version": 1,
            "digest": "1" * 64,
        },
        {
            "kind": "fact_scope_evidence",
            "ref": "fact-scope:no-product-claims",
            "version": 1,
            "digest": "2" * 64,
        },
        {
            "kind": "catalog",
            "ref": "workflow-catalog:static",
            "version": 1,
            "digest": "c" * 64,
        },
    ]
    plan_payload = {
        "schema_version": "sv-run-plan/v1",
        "task_id": str(task.id),
        "task_revision": task.revision,
        "run_id": str(run_id),
        "run_revision": 3,
        "version": 2,
        "workflow_name": "viral-replication.experience-pov",
        "workflow_version": "1.0.0",
        "capability_catalog_version": "1.0.0",
        "capability_catalog_digest": "c" * 64,
        "primary_mechanism": "experience-pov",
        "creative_dimension": "experience_pov",
        "steps": [
            {
                "step_id": "freeze-contract",
                "order": 1,
                "capability_name": "planning.viral.experience-pov",
                "capability_version": "1.0.0",
                "execution_mode": "planning_only",
                "guards": [],
            }
        ],
        "input_refs": plan_input_refs,
        "limitations": ["No render, publish, rights, or commercial approval."],
    }
    db_session.add(
        SvRunPlanRecord(
            id=UUID("27000000-0000-0000-0000-000000000001"),
            run_id=run_id,
            version=2,
            task_id=task.id,
            task_revision=task.revision,
            run_revision=3,
            workflow_name="viral-replication.experience-pov",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            plan_payload=plan_payload,
            plan_digest=canonical_digest(plan_payload),
            input_refs=plan_input_refs,
            created_at=now,
        )
    )
    artifact_id = UUID("28000000-0000-0000-0000-000000000001")
    artifact_payload = _canonical_replication_contract_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=artifact_id,
        created_at=now,
    )
    db_session.add(
        SvArtifactRecord(
            artifact_id=artifact_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=3,
            artifact_type="replication_contract",
            schema_version=str(artifact_payload["schema_version"]),
            status="awaiting_approval",
            evidence_level="fact",
            proof_level="local",
            payload=artifact_payload,
            payload_digest=canonical_digest(artifact_payload),
            input_refs=list(artifact_payload["input_refs"]),
            created_at=now,
        )
    )
    lineage_payload = {"verification": "exact-runtime-binding"}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("28500000-0000-0000-0000-000000000001"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=3,
            source_ref_type="run_plan",
            source_ref_id="27000000-0000-0000-0000-000000000001",
            source_version=2,
            source_digest=canonical_digest(plan_payload),
            target_ref_type="replication_contract",
            target_ref_id=str(artifact_id),
            target_version=1,
            target_digest=canonical_digest(artifact_payload),
            relation_type="derived_from",
            verifier_name="mission-control-test",
            verifier_version="1.0.0",
            verification_payload=lineage_payload,
            verification_digest=canonical_digest(lineage_payload),
            created_at=now,
        )
    )
    approval_id = UUID("29000000-0000-0000-0000-000000000001")
    db_session.add(
        SvApprovalRequestRecord(
            id=approval_id,
            request_version=1,
            request_digest="a" * 64,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=3,
            gate_kind="replication_contract",
            artifact_type="replication_contract",
            artifact_id=str(artifact_id),
            artifact_version=1,
            artifact_digest=canonical_digest(artifact_payload),
            precondition_digest="b" * 64,
            predicted_effects=[],
            explicit_non_effects=[],
            evidence_summary={},
            limitations=[],
            stale_if=[],
            created_at=now,
        )
    )
    for offset in range(22):
        updated_at = now.replace(minute=offset)
        db_session.add(
            SvToolRunRecord(
                id=UUID(f"30000000-0000-0000-0000-{offset:012d}"),
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=3,
                revision=1,
                tool_name="product_truth.inspect",
                tool_version="1.0.0",
                intent_summary=f"Inspect evidence {offset}",
                input_digest=f"{offset:064x}",
                effect_class="read",
                approval_request_id=None,
                approval_request_version=None,
                idempotency_key=None,
                attempt_token=1,
                status="completed",
                artifact_refs=[],
                stable_error_code=None,
                recovery_action=None,
                started_at=updated_at,
                finished_at=updated_at,
                created_at=updated_at,
                updated_at=updated_at,
            )
        )
    await db_session.flush()

    projection = await MissionControl(db_session).inspect(task.id)

    assert projection.run is not None
    assert projection.run.run_id == run_id
    assert projection.run.state is RunState.AWAITING_APPROVAL
    assert projection.plan is not None
    assert projection.plan.ref == "run-plan:27000000-0000-0000-0000-000000000001:v2"
    assert projection.plan.steps[0].capability_name == "planning.viral.experience-pov"
    assert projection.plan.limitations == ("No render, publish, rights, or commercial approval.",)
    assert projection.current_artifact is not None
    assert projection.current_artifact.ref == f"artifact:{artifact_id}:v1"
    assert projection.current_stage == "fact_and_contract"
    assert [stage.status for stage in projection.stages] == [
        StageStatus.UNKNOWN,
        StageStatus.UNKNOWN,
        StageStatus.UNKNOWN,
        StageStatus.BLOCKED,
        StageStatus.UNKNOWN,
        StageStatus.UNKNOWN,
        StageStatus.UNKNOWN,
    ]
    assert projection.blockers[0].code == "APPROVAL_REQUIRED"
    assert projection.blockers[0].source_ref == f"approval:{approval_id}:v1"
    assert projection.next_safe_action.kind == "open_approval"
    assert projection.next_safe_action.interaction_intent is None
    assert projection.next_safe_action.execution_available is False
    assert len(projection.tool_runs) == 20
    assert projection.tool_runs_truncated is True
    assert projection.tool_runs[0].intent_summary == "Inspect evidence 21"
    assert projection.tool_runs[-1].intent_summary == "Inspect evidence 2"
    assert {citation.kind for citation in projection.explanation.citations} >= {
        "artifact",
        "plan",
    }


async def test_mission_control_fails_closed_on_plan_digest_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000002")
    now = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=None,
        creative_dimension=None,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    payload = {"schema_version": "sv-run-plan/v1", "steps": []}
    db_session.add(
        SvRunPlanRecord(
            id=UUID("27000000-0000-0000-0000-000000000002"),
            run_id=run_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_revision=1,
            workflow_name="viral-replication.pending",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            plan_payload=payload,
            plan_digest="f" * 64,
            input_refs=[],
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(JournalIntegrityError, match="mission_control_plan_digest_mismatch"):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_fails_closed_on_plan_task_brief_digest_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000012")
    now = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    payload, input_refs = _run_plan_payload(
        task=task,
        run_id=run_id,
        run_revision=1,
        brief_digest="f" * 64,
    )
    db_session.add(
        SvRunPlanRecord(
            id=UUID("27000000-0000-0000-0000-000000000012"),
            run_id=run_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_revision=1,
            workflow_name="viral-replication.experience-pov",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            plan_payload=payload,
            plan_digest=canonical_digest(payload),
            input_refs=input_refs,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="mission_control_plan_brief_digest_mismatch",
    ):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_does_not_promote_ambiguous_plan_or_artifact_frontiers(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000003")
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=None,
        creative_dimension=None,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)

    for version in (1, 2):
        plan_id = UUID(f"27000000-0000-0000-0000-{version + 10:012d}")
        plan_payload = {
            "schema_version": "sv-run-plan/v1",
            "task_id": str(task.id),
            "task_revision": task.revision,
            "run_id": str(run_id),
            "run_revision": 1,
            "version": version,
            "workflow_name": "viral-replication.reference-intake",
            "workflow_version": "1.0.0",
            "capability_catalog_version": "1.0.0",
            "steps": [],
            "limitations": ["Planning only."],
        }
        db_session.add(
            SvRunPlanRecord(
                id=plan_id,
                run_id=run_id,
                version=version,
                task_id=task.id,
                task_revision=task.revision,
                run_revision=1,
                workflow_name="viral-replication.reference-intake",
                workflow_version="1.0.0",
                capability_catalog_version="1.0.0",
                plan_payload=plan_payload,
                plan_digest=canonical_digest(plan_payload),
                input_refs=[],
                created_at=now,
            )
        )

        artifact_id = UUID(f"28000000-0000-0000-0000-{version + 10:012d}")
        artifact_payload = {
            "schema_version": "reference-bundle/v1",
            "candidate": version,
        }
        artifact_digest = canonical_digest(artifact_payload)
        db_session.add(
            SvArtifactRecord(
                artifact_id=artifact_id,
                version=1,
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=1,
                artifact_type="reference_bundle",
                schema_version="reference-bundle/v1",
                status="validated",
                evidence_level="fact",
                proof_level="local",
                payload=artifact_payload,
                payload_digest=artifact_digest,
                input_refs=[],
                created_at=now,
            )
        )
        if version == 1:
            verification_payload = {"candidate": version, "verified": True}
            db_session.add(
                SvRuntimeLineageLinkRecord(
                    id=UUID(f"28500000-0000-0000-0000-{version + 10:012d}"),
                    task_id=task.id,
                    task_revision=task.revision,
                    run_id=run_id,
                    run_revision=1,
                    source_ref_type="run_plan",
                    source_ref_id=str(plan_id),
                    source_version=version,
                    source_digest=canonical_digest(plan_payload),
                    target_ref_type="reference_bundle",
                    target_ref_id=str(artifact_id),
                    target_version=1,
                    target_digest=artifact_digest,
                    relation_type="derived_from",
                    verifier_name="mission-control-test",
                    verifier_version="1.0.0",
                    verification_payload=verification_payload,
                    verification_digest=canonical_digest(verification_payload),
                    created_at=now,
                )
            )
    await db_session.flush()

    projection = await MissionControl(db_session).inspect(task.id)

    assert projection.plan is None
    assert projection.current_artifact is None
    assert {blocker.code for blocker in projection.blockers} >= {
        "PLAN_FRONTIER_AMBIGUOUS",
        "ARTIFACT_FRONTIER_AMBIGUOUS",
    }
    assert projection.next_safe_action.kind == "refresh_evidence"
    assert projection.next_safe_action.execution_available is False


async def test_mission_control_keeps_an_unverified_artifact_as_unavailable(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000004")
    now = datetime(2026, 10, 21, 10, 30, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=None,
        creative_dimension=None,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    payload = {"schema_version": "reference-bundle/v1"}
    db_session.add(
        SvArtifactRecord(
            artifact_id=UUID("28000000-0000-0000-0000-000000000020"),
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            artifact_type="reference_bundle",
            schema_version="reference-bundle/v1",
            status="validated",
            evidence_level="fact",
            proof_level="local",
            payload=payload,
            payload_digest=canonical_digest(payload),
            input_refs=[],
            created_at=now,
        )
    )
    await db_session.flush()

    projection = await MissionControl(db_session).inspect(task.id)

    assert projection.current_artifact is None
    assert "ARTIFACT_FRONTIER_UNVERIFIED" in {blocker.code for blocker in projection.blockers}
    assert projection.next_safe_action.kind == "refresh_evidence"


async def test_mission_control_rejects_a_noncanonical_current_artifact(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000013")
    now = datetime(2026, 10, 21, 10, 35, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    await _persist_artifact_with_lineage(
        db_session,
        task=task,
        run=run_record,
        artifact_id=UUID("28000000-0000-0000-0000-000000000071"),
        payload={"schema_version": "sv.replication-contract.v1"},
        created_at=now,
    )

    with pytest.raises(
        JournalIntegrityError,
        match="mission_control_artifact_schema_invalid",
    ):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_rejects_current_artifact_content_digest_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000014")
    artifact_id = UUID("28000000-0000-0000-0000-000000000072")
    now = datetime(2026, 10, 21, 10, 36, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    payload = _canonical_replication_contract_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=artifact_id,
        created_at=now,
    )
    payload["content_digest"] = "f" * 64
    await _persist_artifact_with_lineage(
        db_session,
        task=task,
        run=run_record,
        artifact_id=artifact_id,
        payload=payload,
        created_at=now,
    )

    with pytest.raises(
        JournalIntegrityError,
        match="mission_control_artifact_content_digest_mismatch",
    ):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_rejects_current_artifact_row_scope_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000015")
    artifact_id = UUID("28000000-0000-0000-0000-000000000073")
    now = datetime(2026, 10, 21, 10, 37, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    payload = _canonical_replication_contract_payload(
        task_id=UUID("25000000-0000-0000-0000-000000000099"),
        run_id=run_id,
        artifact_id=artifact_id,
        created_at=now,
    )
    await _persist_artifact_with_lineage(
        db_session,
        task=task,
        run=run_record,
        artifact_id=artifact_id,
        payload=payload,
        created_at=now,
    )

    with pytest.raises(
        JournalIntegrityError,
        match="mission_control_artifact_envelope_drift",
    ):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_fails_closed_on_lineage_verification_digest_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000011")
    now = datetime(2026, 10, 21, 10, 45, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=None,
        creative_dimension=None,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    artifact_id = UUID("28000000-0000-0000-0000-000000000060")
    artifact_payload = {"schema_version": "reference-bundle/v1"}
    artifact_digest = canonical_digest(artifact_payload)
    db_session.add(
        SvArtifactRecord(
            artifact_id=artifact_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            artifact_type="reference_bundle",
            schema_version="reference-bundle/v1",
            status="validated",
            evidence_level="fact",
            proof_level="local",
            payload=artifact_payload,
            payload_digest=artifact_digest,
            input_refs=[],
            created_at=now,
        )
    )
    verification_payload = {"verified": True}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("28500000-0000-0000-0000-000000000060"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            source_ref_type="run",
            source_ref_id=str(run_id),
            source_version=1,
            source_digest="a" * 64,
            target_ref_type="reference_bundle",
            target_ref_id=str(artifact_id),
            target_version=1,
            target_digest=artifact_digest,
            relation_type="derived_from",
            verifier_name="mission-control-test",
            verifier_version="1.0.0",
            verification_payload=verification_payload,
            verification_digest="f" * 64,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="mission_control_lineage_verification_digest_mismatch",
    ):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_never_advances_when_current_frontiers_are_unavailable(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000005")
    now = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.RUNNABLE.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)

    projection = await MissionControl(db_session).inspect(task.id)

    assert {blocker.code for blocker in projection.blockers} >= {
        "PLAN_FRONTIER_UNAVAILABLE",
        "ARTIFACT_FRONTIER_UNAVAILABLE",
    }
    assert projection.next_safe_action.kind == "refresh_evidence"
    assert projection.next_safe_action.interaction_intent == "request_evidence"
    assert projection.next_safe_action.execution_available is False


async def test_mission_control_rejects_closed_plan_payload_pollution(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000006")
    now = datetime(2026, 10, 21, 11, 30, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.PLANNING.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    input_refs = [
        {
            "kind": "task_brief",
            "ref": f"task-brief:{task.id}",
            "version": task.revision,
            "digest": canonical_digest(task.brief),
        },
        {
            "kind": "route_evidence",
            "ref": "decomposition_map:route-candidate",
            "version": 1,
            "digest": "1" * 64,
        },
        {
            "kind": "fact_scope_evidence",
            "ref": "fact-scope:no-product-claims",
            "version": 1,
            "digest": "2" * 64,
        },
        {
            "kind": "catalog",
            "ref": "workflow-catalog:static",
            "version": 1,
            "digest": "c" * 64,
        },
    ]
    payload = {
        "schema_version": "sv-run-plan/v1",
        "task_id": str(task.id),
        "task_revision": task.revision,
        "run_id": str(run_id),
        "run_revision": 1,
        "version": 1,
        "workflow_name": "viral-replication.experience-pov",
        "workflow_version": "1.0.0",
        "capability_catalog_version": "1.0.0",
        "capability_catalog_digest": "c" * 64,
        "primary_mechanism": "experience-pov",
        "creative_dimension": "experience_pov",
        "steps": [
            {
                "step_id": "inspect-reference",
                "order": 1,
                "capability_name": "planning.viral.reference-intake",
                "capability_version": "1.0.0",
                "execution_mode": "planning_only",
                "guards": [],
            }
        ],
        "input_refs": input_refs,
        "limitations": ["Planning only."],
        "private_reasoning": "must never be tolerated or exposed",
    }
    db_session.add(
        SvRunPlanRecord(
            id=UUID("27000000-0000-0000-0000-000000000030"),
            run_id=run_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_revision=1,
            workflow_name="viral-replication.experience-pov",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            plan_payload=payload,
            plan_digest=canonical_digest(payload),
            input_refs=input_refs,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(JournalIntegrityError, match="mission_control_plan_payload_invalid"):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_fails_closed_on_approval_decision_binding_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000016")
    artifact_id = UUID("28000000-0000-0000-0000-000000000074")
    approval_id = UUID("29000000-0000-0000-0000-000000000999")
    now = datetime(2026, 10, 21, 11, 45, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.AWAITING_APPROVAL.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    artifact_payload = _canonical_replication_contract_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=artifact_id,
        created_at=now,
    )
    await _persist_artifact_with_lineage(
        db_session,
        task=task,
        run=run_record,
        artifact_id=artifact_id,
        payload=artifact_payload,
        created_at=now,
    )
    artifact_digest = canonical_digest(artifact_payload)
    for offset in range(21):
        db_session.add(
            SvApprovalRequestRecord(
                id=UUID(f"29000000-0000-0000-0000-{offset + 100:012d}"),
                request_version=1,
                request_digest=f"{offset + 1:064x}",
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=1,
                gate_kind="replication_contract",
                artifact_type="replication_contract",
                artifact_id=str(artifact_id),
                artifact_version=1,
                artifact_digest=artifact_digest,
                precondition_digest="b" * 64,
                predicted_effects=[],
                explicit_non_effects=[],
                evidence_summary={},
                limitations=[],
                stale_if=[],
                created_at=now,
            )
        )
    db_session.add(
        SvApprovalRequestRecord(
            id=approval_id,
            request_version=1,
            request_digest="a" * 64,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            gate_kind="replication_contract",
            artifact_type="replication_contract",
            artifact_id=str(artifact_id),
            artifact_version=1,
            artifact_digest=artifact_digest,
            precondition_digest="b" * 64,
            predicted_effects=[],
            explicit_non_effects=[],
            evidence_summary={},
            limitations=[],
            stale_if=[],
            created_at=now,
        )
    )
    decision_payload = {
        "approval_request_id": str(approval_id),
        "decision": "approve",
    }
    db_session.add(
        SvDecisionEventRecord(
            id=UUID("24000000-0000-0000-0000-000000000999"),
            event_type="human_decision.recorded.v1",
            approval_request_id=approval_id,
            approval_request_version=1,
            request_digest="f" * 64,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            decision="approve",
            rationale="Mismatched request digest.",
            payload=decision_payload,
            payload_digest=canonical_digest(decision_payload),
            decided_by_kind="human",
            decided_by_ref="local-reviewer",
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="mission_control_approval_decision_binding_mismatch",
    ):
        await MissionControl(db_session).inspect(task.id)


async def test_mission_control_bounds_pending_approvals_with_stable_truncation(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000007")
    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.AWAITING_APPROVAL.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    artifact_id = UUID("28000000-0000-0000-0000-000000000040")
    artifact_payload = _canonical_replication_contract_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=artifact_id,
        created_at=now,
    )
    artifact_digest = canonical_digest(artifact_payload)
    db_session.add(
        SvArtifactRecord(
            artifact_id=artifact_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            artifact_type="replication_contract",
            schema_version=str(artifact_payload["schema_version"]),
            status="awaiting_approval",
            evidence_level="fact",
            proof_level="local",
            payload=artifact_payload,
            payload_digest=artifact_digest,
            input_refs=list(artifact_payload["input_refs"]),
            created_at=now,
        )
    )
    verification_payload = {"verified": True}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("28500000-0000-0000-0000-000000000040"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            source_ref_type="run",
            source_ref_id=str(run_id),
            source_version=1,
            source_digest="4" * 64,
            target_ref_type="replication_contract",
            target_ref_id=str(artifact_id),
            target_version=1,
            target_digest=artifact_digest,
            relation_type="derived_from",
            verifier_name="mission-control-test",
            verifier_version="1.0.0",
            verification_payload=verification_payload,
            verification_digest=canonical_digest(verification_payload),
            created_at=now,
        )
    )
    for offset in range(21):
        approval_id = UUID(f"29000000-0000-0000-0000-{offset + 100:012d}")
        db_session.add(
            SvApprovalRequestRecord(
                id=approval_id,
                request_version=1,
                request_digest=f"{offset + 1:064x}",
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=1,
                gate_kind="replication_contract",
                artifact_type="replication_contract",
                artifact_id=str(artifact_id),
                artifact_version=1,
                artifact_digest=artifact_digest,
                precondition_digest="5" * 64,
                predicted_effects=[],
                explicit_non_effects=[],
                evidence_summary={},
                limitations=[],
                stale_if=[],
                created_at=now,
            )
        )
    await db_session.flush()

    projection = await MissionControl(db_session).inspect(task.id)

    assert "APPROVAL_SET_TRUNCATED" in {blocker.code for blocker in projection.blockers}
    approval_refs = [
        citation.ref for citation in projection.explanation.citations if citation.kind == "approval"
    ]
    assert len(approval_refs) == 20
    assert approval_refs[0].endswith("000000000100:v1")
    assert approval_refs[-1].endswith("000000000119:v1")
    assert projection.next_safe_action.kind == "refresh_evidence"


async def test_mission_control_does_not_open_an_approval_for_another_artifact(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("26000000-0000-0000-0000-000000000008")
    now = datetime(2026, 10, 21, 12, 30, tzinfo=UTC)
    run_record = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state=RunState.AWAITING_APPROVAL.value,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV.value,
        creative_dimension=CreativeDimension.EXPERIENCE_POV.value,
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run_record)
    artifact_id = UUID("28000000-0000-0000-0000-000000000050")
    artifact_payload = _canonical_replication_contract_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=artifact_id,
        created_at=now,
    )
    artifact_digest = canonical_digest(artifact_payload)
    db_session.add(
        SvArtifactRecord(
            artifact_id=artifact_id,
            version=1,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            artifact_type="replication_contract",
            schema_version=str(artifact_payload["schema_version"]),
            status="awaiting_approval",
            evidence_level="fact",
            proof_level="local",
            payload=artifact_payload,
            payload_digest=artifact_digest,
            input_refs=list(artifact_payload["input_refs"]),
            created_at=now,
        )
    )
    verification_payload = {"verified": True}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("28500000-0000-0000-0000-000000000050"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            source_ref_type="run",
            source_ref_id=str(run_id),
            source_version=1,
            source_digest="6" * 64,
            target_ref_type="replication_contract",
            target_ref_id=str(artifact_id),
            target_version=1,
            target_digest=artifact_digest,
            relation_type="derived_from",
            verifier_name="mission-control-test",
            verifier_version="1.0.0",
            verification_payload=verification_payload,
            verification_digest=canonical_digest(verification_payload),
            created_at=now,
        )
    )
    db_session.add(
        SvApprovalRequestRecord(
            id=UUID("29000000-0000-0000-0000-000000000050"),
            request_version=1,
            request_digest="7" * 64,
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            gate_kind="replication_contract",
            artifact_type="replication_contract",
            artifact_id="another-artifact",
            artifact_version=1,
            artifact_digest="8" * 64,
            precondition_digest="9" * 64,
            predicted_effects=[],
            explicit_non_effects=[],
            evidence_summary={},
            limitations=[],
            stale_if=[],
            created_at=now,
        )
    )
    await db_session.flush()

    projection = await MissionControl(db_session).inspect(task.id)

    blocker_codes = {blocker.code for blocker in projection.blockers}
    assert "APPROVAL_FRONTIER_INCONSISTENT" in blocker_codes
    assert "APPROVAL_REQUIRED" not in blocker_codes
    assert all(citation.kind != "approval" for citation in projection.explanation.citations)
    assert projection.next_safe_action.kind == "refresh_evidence"


@pytest.mark.parametrize(
    ("blocker", "expected_kind", "expected_reason_code"),
    (
        (
            MissionBlocker(
                code="REFERENCE_RIGHTS_BLOCKED",
                message="Rights do not allow progress.",
                source_ref="task:blocked:r1",
            ),
            "preview_request_evidence",
            "BLOCKER_RESOLUTION_REQUIRED",
        ),
        (
            MissionBlocker(
                code="PROVIDER_TIMEOUT",
                message="The read ToolRun failed.",
                source_ref="tool-run:failed:r1",
            ),
            "recovery_unavailable",
            "RECOVERY_RECEIPT_UNAVAILABLE",
        ),
    ),
)
def test_next_safe_action_never_advances_through_an_unresolved_blocker(
    blocker: MissionBlocker,
    expected_kind: str,
    expected_reason_code: str,
) -> None:
    run = MissionRun(
        run_id=UUID("26000000-0000-0000-0000-000000000009"),
        run_revision=1,
        task_revision=1,
        state=RunState.RUNNABLE,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV,
        creative_dimension=CreativeDimension.EXPERIENCE_POV,
        updated_at=datetime(2026, 10, 21, 13, 0, tzinfo=UTC),
    )

    action = _next_action(run, (blocker,), ("run:current:r1",))

    assert action.kind == expected_kind
    assert action.reason_code == expected_reason_code
    assert action.execution_available is False
    assert action.kind != "preview_advance"


def test_approved_artifact_does_not_activate_an_unproven_next_stage() -> None:
    now = datetime(2026, 10, 21, 13, 30, tzinfo=UTC)
    run = MissionRun(
        run_id=UUID("26000000-0000-0000-0000-000000000010"),
        run_revision=1,
        task_revision=1,
        state=RunState.RUNNING,
        primary_mechanism=PrimaryMechanism.EXPERIENCE_POV,
        creative_dimension=CreativeDimension.EXPERIENCE_POV,
        updated_at=now,
    )
    artifact = MissionArtifact(
        ref="artifact:adaptation-package:v1",
        artifact_type=ArtifactType.ADAPTATION_PACKAGE,
        version=1,
        status=ArtifactStatus.APPROVED,
        evidence_level=EvidenceLevel.FACT,
        proof_level=ProofLevel.LOCAL,
        created_at=now,
    )

    stages, current_stage = _stages_for(run, None, artifact, [])

    assert current_stage is StageKey.ADAPTATION
    assert stages[4].status is StageStatus.COMPLETED
    assert stages[5].key is StageKey.SCRIPT_AND_STORYBOARD
    assert stages[5].status is StageStatus.UNKNOWN
