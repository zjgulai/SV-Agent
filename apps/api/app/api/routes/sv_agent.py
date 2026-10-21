from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.session import get_db_session
from app.api.problems import ApiProblem
from app.api.schemas.sv_agent import (
    EvidenceArtifactEdgeOutput,
    EvidenceArtifactGraphOutput,
    EvidenceArtifactNodeOutput,
    EvidenceArtifactWorkspaceOutput,
    EvidenceComparisonOutput,
    EvidencePlaneOutput,
    EvidenceSourceOutput,
    EvidenceSubjectOutput,
    EvidenceWindowOutput,
    EvidenceWorkspaceRunOutput,
    EvidenceWorkspaceTaskOutput,
    MissionArtifactOutput,
    MissionBlockerOutput,
    MissionCitationOutput,
    MissionControlOutput,
    MissionExplanationOutput,
    MissionNextSafeActionOutput,
    MissionPlanOutput,
    MissionPlanStepOutput,
    MissionRunOutput,
    MissionStageOutput,
    MissionTaskOutput,
    MissionToolRunOutput,
    PerformanceWindowOutput,
    TaskInboxItemOutput,
    TaskInboxOutput,
)
from app.application.sv_agent_evidence_workspace import EvidenceArtifactWorkspace
from app.application.sv_agent_mission_control import MissionControl
from app.application.sv_agent_task_inbox import TaskInbox
from app.domain.sv_agent.errors import JournalIntegrityError, TaskNotFound

router = APIRouter(prefix="/api/v1/sv-agent", tags=["sv-agent"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/tasks")
async def list_tasks(session: SessionDependency) -> TaskInboxOutput:
    try:
        projection = await TaskInbox(session).inspect()
    except JournalIntegrityError as exc:
        raise ApiProblem(
            status=500,
            code="JOURNAL_INTEGRITY_ERROR",
            title="Task journal integrity error",
            detail="The Task Inbox cannot be projected from the authoritative runtime journal.",
        ) from exc
    except SQLAlchemyError as exc:
        raise ApiProblem(
            status=503,
            code="DATABASE_UNAVAILABLE",
            title="Task database unavailable",
            detail="The authoritative Task store is unavailable.",
        ) from exc

    return TaskInboxOutput(
        schema_version=projection.schema_version,
        authority=projection.authority,
        ordering_policy_version=projection.ordering_policy_version,
        items=[
            TaskInboxItemOutput(
                task_id=item.task_id,
                task_revision=item.task_revision,
                goal_track=item.goal_track,
                subject=item.subject,
                decision_question=item.decision_question,
                active_run_id=item.active_run_id,
                active_run_revision=item.active_run_revision,
                run_state=item.run_state,
                pending_decision_count=item.pending_decision_count,
                pending_gate_kinds=list(item.pending_gate_kinds),
                lane=item.lane,
                ordering_reason=item.ordering_reason,
                priority_at=item.priority_at,
            )
            for item in projection.items
        ],
        truncated=projection.truncated,
    )


@router.get("/tasks/{task_id}/artifacts")
async def get_task_evidence_artifacts(
    task_id: UUID,
    session: SessionDependency,
) -> EvidenceArtifactWorkspaceOutput:
    try:
        projection = await EvidenceArtifactWorkspace(session).inspect(task_id)
    except TaskNotFound as exc:
        raise ApiProblem(
            status=404,
            code="TASK_NOT_FOUND",
            title="Task not found",
            detail="The requested Task does not exist in the authoritative Task store.",
        ) from exc
    except JournalIntegrityError as exc:
        raise ApiProblem(
            status=500,
            code="JOURNAL_INTEGRITY_ERROR",
            title="Task journal integrity error",
            detail=(
                "The evidence artifact workspace cannot be projected from the "
                "authoritative runtime journal."
            ),
        ) from exc
    except SQLAlchemyError as exc:
        raise ApiProblem(
            status=503,
            code="DATABASE_UNAVAILABLE",
            title="Task database unavailable",
            detail="The authoritative Task store is unavailable.",
        ) from exc

    task = projection.task
    run = projection.run
    return EvidenceArtifactWorkspaceOutput(
        schema_version=projection.schema_version,
        authority=projection.authority,
        task=EvidenceWorkspaceTaskOutput(
            task_id=task.task_id,
            task_revision=task.task_revision,
            subject=task.subject,
            performance_window=PerformanceWindowOutput(
                start=task.performance_start,
                end=task.performance_end,
                timezone=task.performance_timezone,
            ),
        ),
        run=(
            EvidenceWorkspaceRunOutput(
                run_id=run.run_id,
                run_revision=run.run_revision,
                state=run.state,
            )
            if run is not None
            else None
        ),
        graph=EvidenceArtifactGraphOutput(
            state=projection.graph.state,
            public_code=projection.graph.public_code,
            nodes=[
                EvidenceArtifactNodeOutput(
                    ref=node.ref,
                    artifact_type=node.artifact_type,
                    version=node.version,
                    status=node.status,
                    evidence_level=node.evidence_level,
                    proof_level=node.proof_level,
                    created_at=node.created_at,
                    is_conclusion=node.is_conclusion,
                    sources=[EvidenceSourceOutput(kind=source.kind) for source in node.sources],
                    subject=EvidenceSubjectOutput(
                        state=node.subject.state,
                        market=node.subject.market,
                        locale=node.subject.locale,
                        limitations=list(node.subject.limitations),
                    ),
                    window=(
                        EvidenceWindowOutput(
                            start=node.window.start,
                            end=node.window.end,
                            timezone=node.window.timezone,
                            basis=node.window.basis,
                        )
                        if node.window is not None
                        else None
                    ),
                    limitations=list(node.limitations),
                )
                for node in projection.graph.nodes
            ],
            edges=[
                EvidenceArtifactEdgeOutput(
                    source_ref=edge.source_ref,
                    target_ref=edge.target_ref,
                    kind=edge.kind,
                    verification_state=edge.verification_state,
                )
                for edge in projection.graph.edges
            ],
            limitations=list(projection.graph.limitations),
        ),
        evidence_planes=[
            EvidencePlaneOutput(
                kind=plane.kind,
                state=plane.state,
                public_code=plane.public_code,
                source=plane.source,
                subject=(
                    EvidenceSubjectOutput(
                        state=plane.subject.state,
                        market=plane.subject.market,
                        locale=plane.subject.locale,
                        limitations=list(plane.subject.limitations),
                    )
                    if plane.subject is not None
                    else None
                ),
                window=(
                    EvidenceWindowOutput(
                        start=plane.window.start,
                        end=plane.window.end,
                        timezone=plane.window.timezone,
                        basis=plane.window.basis,
                    )
                    if plane.window is not None
                    else None
                ),
                proof_level=plane.proof_level,
                limitations=list(plane.limitations),
            )
            for plane in projection.evidence_planes
        ],
        comparison=EvidenceComparisonOutput(
            state=projection.comparison.state,
            public_code=projection.comparison.public_code,
            script_ref=projection.comparison.script_ref,
            control_version_ref=projection.comparison.control_version_ref,
            variant_version_ref=projection.comparison.variant_version_ref,
            limitations=list(projection.comparison.limitations),
        ),
        explicit_non_effects=list(projection.explicit_non_effects),
    )


@router.get("/tasks/{task_id}")
async def get_task_mission_control(
    task_id: UUID,
    session: SessionDependency,
) -> MissionControlOutput:
    try:
        projection = await MissionControl(session).inspect(task_id)
    except TaskNotFound as exc:
        raise ApiProblem(
            status=404,
            code="TASK_NOT_FOUND",
            title="Task not found",
            detail="The requested Task does not exist in the authoritative Task store.",
        ) from exc
    except JournalIntegrityError as exc:
        raise ApiProblem(
            status=500,
            code="JOURNAL_INTEGRITY_ERROR",
            title="Task journal integrity error",
            detail="Mission Control cannot be projected from the authoritative runtime journal.",
        ) from exc
    except SQLAlchemyError as exc:
        raise ApiProblem(
            status=503,
            code="DATABASE_UNAVAILABLE",
            title="Task database unavailable",
            detail="The authoritative Task store is unavailable.",
        ) from exc

    task = projection.task
    run = projection.run
    plan = projection.plan
    artifact = projection.current_artifact
    return MissionControlOutput(
        schema_version=projection.schema_version,
        authority=projection.authority,
        task=MissionTaskOutput(
            task_id=task.task_id,
            task_revision=task.task_revision,
            goal_track=task.goal_track,
            decision_question=task.decision_question,
            subject=task.subject,
            platform=task.platform,
            market=task.market,
            language=task.language,
            performance_window=PerformanceWindowOutput(
                start=task.performance_start,
                end=task.performance_end,
                timezone=task.performance_timezone,
            ),
            stop_condition=task.stop_condition,
            initial_rights_state=task.initial_rights_state,
        ),
        run=(
            MissionRunOutput(
                run_id=run.run_id,
                run_revision=run.run_revision,
                task_revision=run.task_revision,
                state=run.state,
                primary_mechanism=run.primary_mechanism,
                creative_dimension=run.creative_dimension,
                updated_at=run.updated_at,
            )
            if run is not None
            else None
        ),
        stages=[
            MissionStageOutput(key=stage.key, label=stage.label, status=stage.status)
            for stage in projection.stages
        ],
        current_stage=projection.current_stage,
        plan=(
            MissionPlanOutput(
                ref=plan.ref,
                version=plan.version,
                run_revision=plan.run_revision,
                workflow_name=plan.workflow_name,
                workflow_version=plan.workflow_version,
                capability_catalog_version=plan.capability_catalog_version,
                steps=[
                    MissionPlanStepOutput(
                        step_id=step.step_id,
                        order=step.order,
                        capability_name=step.capability_name,
                        capability_version=step.capability_version,
                        execution_mode=step.execution_mode,
                    )
                    for step in plan.steps
                ],
                limitations=list(plan.limitations),
                created_at=plan.created_at,
            )
            if plan is not None
            else None
        ),
        blockers=[
            MissionBlockerOutput(
                code=blocker.code,
                message=blocker.message,
                source_ref=blocker.source_ref,
            )
            for blocker in projection.blockers
        ],
        next_safe_action=MissionNextSafeActionOutput(
            kind=projection.next_safe_action.kind,
            label=projection.next_safe_action.label,
            reason=projection.next_safe_action.reason,
            reason_code=projection.next_safe_action.reason_code,
            interaction_intent=projection.next_safe_action.interaction_intent,
            basis_refs=list(projection.next_safe_action.basis_refs),
            explicit_non_effects=list(projection.next_safe_action.explicit_non_effects),
            execution_available=projection.next_safe_action.execution_available,
        ),
        tool_runs=[
            MissionToolRunOutput(
                ref=tool.ref,
                tool_name=tool.tool_name,
                tool_version=tool.tool_version,
                intent_summary=tool.intent_summary,
                effect_class=tool.effect_class,
                status=tool.status,
                stable_error_code=tool.stable_error_code,
                recovery_action=tool.recovery_action,
                started_at=tool.started_at,
                finished_at=tool.finished_at,
                updated_at=tool.updated_at,
            )
            for tool in projection.tool_runs
        ],
        tool_runs_truncated=projection.tool_runs_truncated,
        current_artifact=(
            MissionArtifactOutput(
                ref=artifact.ref,
                artifact_type=artifact.artifact_type,
                version=artifact.version,
                status=artifact.status,
                evidence_level=artifact.evidence_level,
                proof_level=artifact.proof_level,
                created_at=artifact.created_at,
            )
            if artifact is not None
            else None
        ),
        explanation=MissionExplanationOutput(
            summary=projection.explanation.summary,
            citations=[
                MissionCitationOutput(kind=citation.kind, ref=citation.ref)
                for citation in projection.explanation.citations
            ],
        ),
    )
