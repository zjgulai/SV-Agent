from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal, TypeGuard
from uuid import UUID

from sqlalchemy import exists, select
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
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.artifact_contracts import ArtifactValidationError, validate_artifact
from app.domain.sv_agent.entities import (
    CreativeDimension,
    GoalTrack,
    PerformanceWindow,
    PrimaryMechanism,
    RightsState,
    RunState,
    TargetPlatform,
    TaskBrief,
)
from app.domain.sv_agent.errors import JournalIntegrityError, TaskNotFound
from app.domain.sv_agent.runtime_records import (
    ApprovalGateKind,
    ArtifactStatus,
    ArtifactType,
    EffectClass,
    EvidenceLevel,
    ProofLevel,
    ToolRunStatus,
)

_MAX_TOOL_RUNS = 20
_MAX_PENDING_APPROVALS = 20
_MAX_ARTIFACT_LINEAGE_LINKS = 20
_NON_EFFECTS = (
    "does_not_write_postgresql",
    "does_not_dispatch_tool",
    "does_not_call_provider",
    "does_not_decide_approval",
    "does_not_render_or_publish",
)


class StageKey(StrEnum):
    REFERENCE_ADMISSION = "reference_admission"
    CONTENT_DECOMPOSITION = "content_decomposition"
    MECHANISM_SELECTION = "mechanism_selection"
    FACT_AND_CONTRACT = "fact_and_contract"
    ADAPTATION = "adaptation"
    SCRIPT_AND_STORYBOARD = "script_and_storyboard"
    MEDIA_INTEGRITY_AND_FINDING = "media_integrity_and_finding"


class StageStatus(StrEnum):
    COMPLETED = "completed"
    ACTIVE = "active"
    WAITING = "waiting"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MissionTask:
    task_id: UUID
    task_revision: int
    goal_track: GoalTrack
    decision_question: str
    subject: str
    platform: TargetPlatform
    market: str
    language: str
    performance_start: date
    performance_end: date
    performance_timezone: str
    stop_condition: str
    initial_rights_state: RightsState


@dataclass(frozen=True, slots=True)
class MissionRun:
    run_id: UUID
    run_revision: int
    task_revision: int
    state: RunState
    primary_mechanism: PrimaryMechanism | None
    creative_dimension: CreativeDimension | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MissionStage:
    key: StageKey
    label: str
    status: StageStatus


@dataclass(frozen=True, slots=True)
class MissionPlanStep:
    step_id: str
    order: int
    capability_name: str
    capability_version: str
    execution_mode: Literal["planning_only"]


@dataclass(frozen=True, slots=True)
class MissionPlan:
    ref: str
    version: int
    run_revision: int
    workflow_name: str
    workflow_version: str
    capability_catalog_version: str
    steps: tuple[MissionPlanStep, ...]
    limitations: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class MissionBlocker:
    code: str
    message: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class MissionNextSafeAction:
    kind: str
    label: str
    reason: str
    reason_code: str
    interaction_intent: str | None
    basis_refs: tuple[str, ...]
    explicit_non_effects: tuple[str, ...] = _NON_EFFECTS
    execution_available: Literal[False] = False


@dataclass(frozen=True, slots=True)
class MissionToolRun:
    ref: str
    tool_name: str
    tool_version: str
    intent_summary: str
    effect_class: EffectClass
    status: ToolRunStatus
    stable_error_code: str | None
    recovery_action: str | None
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MissionArtifact:
    ref: str
    artifact_type: ArtifactType
    version: int
    status: ArtifactStatus
    evidence_level: EvidenceLevel
    proof_level: ProofLevel
    created_at: datetime


@dataclass(frozen=True, slots=True)
class _ArtifactFrontier:
    projection: MissionArtifact
    artifact_id: UUID
    payload_digest: str


@dataclass(frozen=True, slots=True)
class MissionCitation:
    kind: str
    ref: str


@dataclass(frozen=True, slots=True)
class MissionExplanation:
    summary: str
    citations: tuple[MissionCitation, ...]


@dataclass(frozen=True, slots=True)
class MissionControlProjection:
    schema_version: Literal["sv-mission-control/v1"]
    authority: Literal["postgresql"]
    task: MissionTask
    run: MissionRun | None
    stages: tuple[MissionStage, ...]
    current_stage: StageKey
    plan: MissionPlan | None
    blockers: tuple[MissionBlocker, ...]
    next_safe_action: MissionNextSafeAction
    tool_runs: tuple[MissionToolRun, ...]
    tool_runs_truncated: bool
    current_artifact: MissionArtifact | None
    explanation: MissionExplanation


_STAGE_LABELS: tuple[tuple[StageKey, str], ...] = (
    (StageKey.REFERENCE_ADMISSION, "确认参考来源与可使用范围"),
    (StageKey.CONTENT_DECOMPOSITION, "拆解内容、节奏与互动结构"),
    (StageKey.MECHANISM_SELECTION, "选择唯一主机制"),
    (StageKey.FACT_AND_CONTRACT, "绑定事实并冻结复刻合同"),
    (StageKey.ADAPTATION, "形成目标表达适配包"),
    (StageKey.SCRIPT_AND_STORYBOARD, "编译 Script 与 Storyboard"),
    (StageKey.MEDIA_INTEGRITY_AND_FINDING, "审查媒体完整性并形成结论"),
)

_PLAN_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "task_id",
        "task_revision",
        "run_id",
        "run_revision",
        "version",
        "workflow_name",
        "workflow_version",
        "capability_catalog_version",
        "capability_catalog_digest",
        "primary_mechanism",
        "creative_dimension",
        "steps",
        "input_refs",
        "limitations",
    }
)
_PLAN_STEP_KEYS = frozenset(
    {
        "step_id",
        "order",
        "capability_name",
        "capability_version",
        "execution_mode",
        "guards",
    }
)
_PLAN_INPUT_REF_KEYS = frozenset({"kind", "ref", "version", "digest"})
_PLAN_INPUT_KINDS = frozenset({"task_brief", "route_evidence", "fact_scope_evidence", "catalog"})

_ARTIFACT_STAGE: dict[ArtifactType, StageKey] = {
    ArtifactType.REFERENCE_BUNDLE: StageKey.REFERENCE_ADMISSION,
    ArtifactType.DECOMPOSITION_MAP: StageKey.CONTENT_DECOMPOSITION,
    ArtifactType.PATTERN_HYPOTHESIS: StageKey.MECHANISM_SELECTION,
    ArtifactType.REPLICATION_PLAN: StageKey.MECHANISM_SELECTION,
    ArtifactType.FACT_MAP: StageKey.FACT_AND_CONTRACT,
    ArtifactType.REPLICATION_CONTRACT: StageKey.FACT_AND_CONTRACT,
    ArtifactType.ADAPTATION_PACKAGE: StageKey.ADAPTATION,
    ArtifactType.MEDIA_INTEGRITY_RECORD: StageKey.MEDIA_INTEGRITY_AND_FINDING,
    ArtifactType.REPLICATION_FINDING: StageKey.MEDIA_INTEGRITY_AND_FINDING,
}


class MissionControl:
    """Read-only projection of one authoritative SV-Agent Task workspace."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect(self, task_id: UUID) -> MissionControlProjection:
        task_record, revision_record = await self._load_task(task_id)
        brief = _brief_from_record(revision_record)
        if canonical_digest(brief) != revision_record.brief_digest:
            raise JournalIntegrityError("mission_control_brief_digest_mismatch")
        task_projection = _mission_task(task_record, brief)
        task_ref = f"task:{task_record.id}:r{task_record.current_revision}"

        if task_record.active_run_id is None:
            stages, current_stage = _stages_without_run()
            blocker = MissionBlocker(
                code="RUN_NOT_STARTED",
                message="No authoritative Run has been started for this Task.",
                source_ref=task_ref,
            )
            return MissionControlProjection(
                schema_version="sv-mission-control/v1",
                authority="postgresql",
                task=task_projection,
                run=None,
                stages=stages,
                current_stage=current_stage,
                plan=None,
                blockers=(blocker,),
                next_safe_action=_next_action(None, (blocker,), (task_ref,)),
                tool_runs=(),
                tool_runs_truncated=False,
                current_artifact=None,
                explanation=MissionExplanation(
                    summary="The Task is saved, but no authoritative Run exists yet.",
                    citations=(MissionCitation(kind="task", ref=task_ref),),
                ),
            )

        run_record = await self._session.get(SvRunRecord, task_record.active_run_id)
        if (
            run_record is None
            or run_record.task_id != task_record.id
            or run_record.task_revision != task_record.current_revision
        ):
            raise JournalIntegrityError("mission_control_active_run_scope_invalid")
        run_projection = _mission_run(run_record)
        run_ref = f"run:{run_record.id}:r{run_record.revision}"

        plan, plan_blocker = await self._load_plan(
            task_record,
            run_record,
            revision_record.brief_digest,
        )
        artifact_frontier, artifact_blocker = await self._load_artifact(task_record, run_record)
        artifact = artifact_frontier.projection if artifact_frontier is not None else None
        tool_runs, tool_runs_truncated = await self._load_tool_runs(task_record, run_record)
        (
            approvals,
            approvals_truncated,
            approval_frontier_inconsistent,
        ) = await self._load_pending_approvals(
            task_record,
            run_record,
            artifact_frontier,
        )
        await self._assert_snapshot_unchanged(task_record, run_record)

        blockers = [item for item in (plan_blocker, artifact_blocker) if item is not None]
        blockers.extend(
            _state_blockers(
                brief,
                run_projection,
                task_ref,
                run_ref,
                approvals,
                approvals_truncated,
                approval_frontier_inconsistent,
                tool_runs,
            )
        )
        stages, current_stage = _stages_for(run_projection, plan, artifact, blockers)

        citations = [
            MissionCitation(kind="task", ref=task_ref),
            MissionCitation(kind="run", ref=run_ref),
        ]
        if plan is not None:
            citations.append(MissionCitation(kind="plan", ref=plan.ref))
        if artifact is not None:
            citations.append(MissionCitation(kind="artifact", ref=artifact.ref))
        citations.extend(
            MissionCitation(
                kind="approval",
                ref=f"approval:{approval.id}:v{approval.request_version}",
            )
            for approval in approvals
        )
        evidence_statement = (
            f"The unique verified artifact frontier is {artifact.ref}."
            if artifact is not None
            else "No unique verified artifact frontier is available."
        )
        basis_refs = tuple(citation.ref for citation in citations)
        return MissionControlProjection(
            schema_version="sv-mission-control/v1",
            authority="postgresql",
            task=task_projection,
            run=run_projection,
            stages=stages,
            current_stage=current_stage,
            plan=plan,
            blockers=tuple(blockers),
            next_safe_action=_next_action(run_projection, tuple(blockers), basis_refs),
            tool_runs=tool_runs,
            tool_runs_truncated=tool_runs_truncated,
            current_artifact=artifact,
            explanation=MissionExplanation(
                summary=f"Run state is {run_projection.state.value}. {evidence_statement}",
                citations=tuple(citations),
            ),
        )

    async def _load_task(self, task_id: UUID) -> tuple[SvTaskRecord, SvTaskRevisionRecord]:
        row = (
            await self._session.execute(
                select(SvTaskRecord, SvTaskRevisionRecord)
                .join(
                    SvTaskRevisionRecord,
                    (SvTaskRevisionRecord.task_id == SvTaskRecord.id)
                    & (SvTaskRevisionRecord.revision == SvTaskRecord.current_revision),
                )
                .where(SvTaskRecord.id == task_id)
            )
        ).one_or_none()
        if row is not None:
            return row[0], row[1]
        if await self._session.get(SvTaskRecord, task_id) is None:
            raise TaskNotFound("task_not_found")
        raise JournalIntegrityError("mission_control_task_revision_missing")

    async def _load_plan(
        self,
        task: SvTaskRecord,
        run: SvRunRecord,
        brief_digest: str,
    ) -> tuple[MissionPlan | None, MissionBlocker | None]:
        rows = (
            await self._session.scalars(
                select(SvRunPlanRecord)
                .where(
                    SvRunPlanRecord.task_id == task.id,
                    SvRunPlanRecord.task_revision == task.current_revision,
                    SvRunPlanRecord.run_id == run.id,
                    SvRunPlanRecord.run_revision == run.revision,
                )
                .order_by(SvRunPlanRecord.version, SvRunPlanRecord.id)
                .limit(2)
            )
        ).all()
        run_ref = f"run:{run.id}:r{run.revision}"
        if len(rows) > 1:
            return None, MissionBlocker(
                "PLAN_FRONTIER_AMBIGUOUS",
                "More than one RunPlan is bound to the current Run revision.",
                run_ref,
            )
        if not rows:
            return None, MissionBlocker(
                "PLAN_FRONTIER_UNAVAILABLE",
                "No RunPlan is bound to the current Run revision.",
                run_ref,
            )
        return _parse_plan(rows[0], task, run, brief_digest), None

    async def _load_artifact(
        self, task: SvTaskRecord, run: SvRunRecord
    ) -> tuple[_ArtifactFrontier | None, MissionBlocker | None]:
        candidates = (
            await self._session.scalars(
                select(SvArtifactRecord)
                .where(
                    SvArtifactRecord.task_id == task.id,
                    SvArtifactRecord.task_revision == task.current_revision,
                    SvArtifactRecord.run_id == run.id,
                    SvArtifactRecord.run_revision == run.revision,
                    SvArtifactRecord.status.not_in(
                        (ArtifactStatus.STALE.value, ArtifactStatus.SUPERSEDED.value)
                    ),
                )
                .order_by(SvArtifactRecord.artifact_id, SvArtifactRecord.version)
                .limit(2)
            )
        ).all()
        run_ref = f"run:{run.id}:r{run.revision}"
        if len(candidates) > 1:
            return None, MissionBlocker(
                "ARTIFACT_FRONTIER_AMBIGUOUS",
                "More than one artifact can be the current frontier.",
                run_ref,
            )
        if not candidates:
            return None, MissionBlocker(
                "ARTIFACT_FRONTIER_UNAVAILABLE",
                "No artifact is bound to the current Run revision.",
                run_ref,
            )
        record = candidates[0]
        lineage_links = (
            await self._session.scalars(
                select(SvRuntimeLineageLinkRecord)
                .where(
                    SvRuntimeLineageLinkRecord.task_id == task.id,
                    SvRuntimeLineageLinkRecord.task_revision == task.current_revision,
                    SvRuntimeLineageLinkRecord.run_id == run.id,
                    SvRuntimeLineageLinkRecord.run_revision == run.revision,
                    SvRuntimeLineageLinkRecord.target_ref_type == record.artifact_type,
                    SvRuntimeLineageLinkRecord.target_ref_id == str(record.artifact_id),
                    SvRuntimeLineageLinkRecord.target_version == record.version,
                    SvRuntimeLineageLinkRecord.target_digest == record.payload_digest,
                )
                .order_by(
                    SvRuntimeLineageLinkRecord.created_at,
                    SvRuntimeLineageLinkRecord.id,
                )
                .limit(_MAX_ARTIFACT_LINEAGE_LINKS + 1)
            )
        ).all()
        if len(lineage_links) > _MAX_ARTIFACT_LINEAGE_LINKS:
            raise JournalIntegrityError("mission_control_lineage_set_unbounded")
        if not lineage_links:
            return None, MissionBlocker(
                "ARTIFACT_FRONTIER_UNVERIFIED",
                "No unique runtime-lineage-verified artifact frontier is available.",
                run_ref,
            )
        if any(
            canonical_digest(link.verification_payload) != link.verification_digest
            for link in lineage_links
        ):
            raise JournalIntegrityError("mission_control_lineage_verification_digest_mismatch")
        return (
            _ArtifactFrontier(
                projection=_parse_artifact(record, task=task, run=run),
                artifact_id=record.artifact_id,
                payload_digest=record.payload_digest,
            ),
            None,
        )

    async def _load_tool_runs(
        self, task: SvTaskRecord, run: SvRunRecord
    ) -> tuple[tuple[MissionToolRun, ...], bool]:
        rows = (
            await self._session.scalars(
                select(SvToolRunRecord)
                .where(
                    SvToolRunRecord.task_id == task.id,
                    SvToolRunRecord.task_revision == task.current_revision,
                    SvToolRunRecord.run_id == run.id,
                    SvToolRunRecord.run_revision == run.revision,
                )
                .order_by(SvToolRunRecord.updated_at.desc(), SvToolRunRecord.id.desc())
                .limit(_MAX_TOOL_RUNS + 1)
            )
        ).all()
        truncated = len(rows) > _MAX_TOOL_RUNS
        try:
            projected = tuple(
                MissionToolRun(
                    ref=f"tool-run:{row.id}:r{row.revision}",
                    tool_name=row.tool_name,
                    tool_version=row.tool_version,
                    intent_summary=row.intent_summary,
                    effect_class=EffectClass(row.effect_class),
                    status=ToolRunStatus(row.status),
                    stable_error_code=row.stable_error_code,
                    recovery_action=row.recovery_action,
                    started_at=row.started_at,
                    finished_at=row.finished_at,
                    updated_at=row.updated_at,
                )
                for row in rows[:_MAX_TOOL_RUNS]
            )
        except ValueError as exc:
            raise JournalIntegrityError("mission_control_tool_run_invalid") from exc
        return projected, truncated

    async def _load_pending_approvals(
        self,
        task: SvTaskRecord,
        run: SvRunRecord,
        artifact: _ArtifactFrontier | None,
    ) -> tuple[tuple[SvApprovalRequestRecord, ...], bool, bool]:
        decision_for_request = exists(
            select(SvDecisionEventRecord.id).where(
                SvDecisionEventRecord.approval_request_id == SvApprovalRequestRecord.id,
                SvDecisionEventRecord.approval_request_version
                == SvApprovalRequestRecord.request_version,
            )
        ).correlate(SvApprovalRequestRecord)
        matching_decision = exists(
            select(SvDecisionEventRecord.id).where(
                SvDecisionEventRecord.approval_request_id == SvApprovalRequestRecord.id,
                SvDecisionEventRecord.approval_request_version
                == SvApprovalRequestRecord.request_version,
                SvDecisionEventRecord.request_digest == SvApprovalRequestRecord.request_digest,
                SvDecisionEventRecord.task_id == SvApprovalRequestRecord.task_id,
                SvDecisionEventRecord.task_revision == SvApprovalRequestRecord.task_revision,
                SvDecisionEventRecord.run_id == SvApprovalRequestRecord.run_id,
                SvDecisionEventRecord.run_revision == SvApprovalRequestRecord.run_revision,
            )
        ).correlate(SvApprovalRequestRecord)
        decision_binding_drift = await self._session.scalar(
            select(
                exists(
                    select(SvApprovalRequestRecord.id).where(
                        SvApprovalRequestRecord.task_id == task.id,
                        SvApprovalRequestRecord.task_revision == task.current_revision,
                        SvApprovalRequestRecord.run_id == run.id,
                        SvApprovalRequestRecord.run_revision == run.revision,
                        decision_for_request,
                        ~matching_decision,
                    )
                )
            )
        )
        if decision_binding_drift:
            raise JournalIntegrityError("mission_control_approval_decision_binding_mismatch")
        rows = (
            await self._session.scalars(
                select(SvApprovalRequestRecord)
                .where(
                    SvApprovalRequestRecord.task_id == task.id,
                    SvApprovalRequestRecord.task_revision == task.current_revision,
                    SvApprovalRequestRecord.run_id == run.id,
                    SvApprovalRequestRecord.run_revision == run.revision,
                    ~matching_decision,
                )
                .order_by(
                    SvApprovalRequestRecord.created_at,
                    SvApprovalRequestRecord.id,
                    SvApprovalRequestRecord.request_version,
                )
                .limit(_MAX_PENDING_APPROVALS + 1)
            )
        ).all()
        truncated = len(rows) > _MAX_PENDING_APPROVALS
        bounded = rows[:_MAX_PENDING_APPROVALS]
        if artifact is None:
            return (), truncated, bool(bounded)
        approvals = tuple(
            row
            for row in bounded
            if row.artifact_type == artifact.projection.artifact_type.value
            and row.artifact_id == str(artifact.artifact_id)
            and row.artifact_version == artifact.projection.version
            and row.artifact_digest == artifact.payload_digest
        )
        return approvals, truncated, len(approvals) != len(bounded)

    async def _assert_snapshot_unchanged(self, task: SvTaskRecord, run: SvRunRecord) -> None:
        row = (
            await self._session.execute(
                select(
                    SvTaskRecord.current_revision,
                    SvTaskRecord.active_run_id,
                    SvTaskRecord.updated_at,
                    SvRunRecord.revision,
                    SvRunRecord.state,
                    SvRunRecord.updated_at,
                )
                .join(SvRunRecord, SvRunRecord.id == SvTaskRecord.active_run_id)
                .where(SvTaskRecord.id == task.id, SvRunRecord.id == run.id)
            )
        ).one_or_none()
        if row is None or tuple(row) != (
            task.current_revision,
            task.active_run_id,
            task.updated_at,
            run.revision,
            run.state,
            run.updated_at,
        ):
            raise JournalIntegrityError("mission_control_snapshot_changed")


def _mission_task(record: SvTaskRecord, brief: TaskBrief) -> MissionTask:
    return MissionTask(
        task_id=record.id,
        task_revision=record.current_revision,
        goal_track=brief.goal_track,
        decision_question=brief.decision_question,
        subject=brief.subject,
        platform=brief.platform,
        market=brief.market,
        language=brief.language,
        performance_start=brief.performance_window.start,
        performance_end=brief.performance_window.end,
        performance_timezone=brief.performance_window.timezone,
        stop_condition=brief.stop_condition,
        initial_rights_state=brief.initial_rights_state,
    )


def _mission_run(record: SvRunRecord) -> MissionRun:
    try:
        mechanism = (
            PrimaryMechanism(record.primary_mechanism)
            if record.primary_mechanism is not None
            else None
        )
        dimension = (
            CreativeDimension(record.creative_dimension)
            if record.creative_dimension is not None
            else None
        )
        if (mechanism is None) != (dimension is None):
            raise ValueError("axis incomplete")
        return MissionRun(
            run_id=record.id,
            run_revision=record.revision,
            task_revision=record.task_revision,
            state=RunState(record.state),
            primary_mechanism=mechanism,
            creative_dimension=dimension,
            updated_at=record.updated_at,
        )
    except ValueError as exc:
        raise JournalIntegrityError("mission_control_run_invalid") from exc


def _validate_plan_input_refs(
    raw_input_refs: list[Any],
    *,
    task: SvTaskRecord,
    brief_digest: str,
    catalog_digest: Any,
) -> None:
    if not _digest(catalog_digest) or len(raw_input_refs) != len(_PLAN_INPUT_KINDS):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    by_kind: dict[str, dict[str, Any]] = {}
    for item in raw_input_refs:
        if not isinstance(item, dict) or frozenset(item) != _PLAN_INPUT_REF_KEYS:
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        kind = item.get("kind")
        ref = item.get("ref")
        version = item.get("version")
        digest = item.get("digest")
        if (
            kind not in _PLAN_INPUT_KINDS
            or kind in by_kind
            or not _text(ref)
            or not _positive_int(version)
            or not _digest(digest)
        ):
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        by_kind[kind] = item
    task_brief = by_kind["task_brief"]
    catalog = by_kind["catalog"]
    if (
        task_brief["ref"] != f"task-brief:{task.id}"
        or task_brief["version"] != task.current_revision
        or catalog["ref"] != "workflow-catalog:static"
        or catalog["digest"] != catalog_digest
    ):
        raise JournalIntegrityError("mission_control_plan_scope_invalid")
    if task_brief["digest"] != brief_digest:
        raise JournalIntegrityError("mission_control_plan_brief_digest_mismatch")


def _validate_plan_guard(
    guard: Any,
    *,
    task: SvTaskRecord,
    run: SvRunRecord,
) -> None:
    if not isinstance(guard, dict) or not _text(guard.get("kind")):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    kind = guard["kind"]
    if kind == "route_is":
        if frozenset(guard) != {
            "kind",
            "primary_mechanism",
            "creative_dimension",
        } or (
            guard.get("primary_mechanism") != run.primary_mechanism
            or guard.get("creative_dimension") != run.creative_dimension
        ):
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        return
    if kind == "media_mode":
        if frozenset(guard) != {"kind", "mode"} or guard.get("mode") not in {
            "analysis_only",
            "controlled_media",
        }:
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        return
    if kind == "artifact_available":
        if frozenset(guard) != {"kind", "handle"}:
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        _validate_artifact_handle(guard.get("handle"), task=task, run=run)
        return
    if kind == "approval_granted":
        if frozenset(guard) != {"kind", "handle"}:
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        _validate_approval_handle(guard.get("handle"), task=task, run=run)
        return
    if kind == "fact_scope_satisfied":
        if frozenset(guard) != {"kind", "evidence"}:
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        _validate_fact_scope_evidence(guard.get("evidence"), task=task, run=run)
        return
    raise JournalIntegrityError("mission_control_plan_payload_invalid")


def _validate_artifact_handle(
    handle: Any,
    *,
    task: SvTaskRecord,
    run: SvRunRecord,
) -> None:
    keys = {
        "artifact_type",
        "artifact_id",
        "version",
        "digest",
        "task_id",
        "task_revision",
        "run_id",
        "run_revision",
        "lineage_verified",
    }
    if not isinstance(handle, dict) or frozenset(handle) != keys:
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    artifact_type = handle.get("artifact_type")
    if not isinstance(artifact_type, str):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    try:
        ArtifactType(artifact_type)
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("mission_control_plan_payload_invalid") from exc
    if (
        not _text(handle.get("artifact_id"))
        or not _positive_int(handle.get("version"))
        or not _digest(handle.get("digest"))
        or handle.get("task_id") != str(task.id)
        or handle.get("task_revision") != task.current_revision
        or handle.get("run_id") != str(run.id)
        or not _positive_int(handle.get("run_revision"))
        or handle["run_revision"] > run.revision
        or handle.get("lineage_verified") is not True
    ):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")


def _validate_approval_handle(
    handle: Any,
    *,
    task: SvTaskRecord,
    run: SvRunRecord,
) -> None:
    keys = {
        "approval_request_id",
        "request_version",
        "request_digest",
        "task_id",
        "task_revision",
        "run_id",
        "run_revision",
        "gate_kind",
        "artifact_type",
        "artifact_id",
        "artifact_version",
        "artifact_digest",
        "precondition_digest",
    }
    if not isinstance(handle, dict) or frozenset(handle) != keys:
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    gate_kind = handle.get("gate_kind")
    artifact_type = handle.get("artifact_type")
    if not isinstance(gate_kind, str) or not isinstance(artifact_type, str):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    try:
        UUID(str(handle.get("approval_request_id")))
        ApprovalGateKind(gate_kind)
        ArtifactType(artifact_type)
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("mission_control_plan_payload_invalid") from exc
    if (
        not _positive_int(handle.get("request_version"))
        or not _digest(handle.get("request_digest"))
        or handle.get("task_id") != str(task.id)
        or handle.get("task_revision") != task.current_revision
        or handle.get("run_id") != str(run.id)
        or handle.get("run_revision") != run.revision
        or not _text(handle.get("artifact_id"))
        or not _positive_int(handle.get("artifact_version"))
        or not _digest(handle.get("artifact_digest"))
        or not _digest(handle.get("precondition_digest"))
    ):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")


def _validate_fact_scope_evidence(
    evidence: Any,
    *,
    task: SvTaskRecord,
    run: SvRunRecord,
) -> None:
    keys = {
        "scope",
        "ref",
        "version",
        "digest",
        "task_id",
        "task_revision",
        "run_id",
        "run_revision",
        "lineage_verified",
        "subject_binding",
        "claim_mapping_count",
        "eligible_fact_count",
    }
    if not isinstance(evidence, dict) or frozenset(evidence) != keys:
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    counts_valid = all(
        isinstance(evidence.get(key), int)
        and not isinstance(evidence.get(key), bool)
        and evidence[key] >= 0
        for key in ("claim_mapping_count", "eligible_fact_count")
    )
    if (
        evidence.get("scope") not in {"product_claims", "no_product_claims"}
        or not _text(evidence.get("ref"))
        or not _positive_int(evidence.get("version"))
        or not _digest(evidence.get("digest"))
        or evidence.get("task_id") != str(task.id)
        or evidence.get("task_revision") != task.current_revision
        or evidence.get("run_id") != str(run.id)
        or not _positive_int(evidence.get("run_revision"))
        or evidence["run_revision"] > run.revision
        or evidence.get("lineage_verified") is not True
        or evidence.get("subject_binding") not in {"product", "not_applicable"}
        or not counts_valid
    ):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    if evidence["scope"] == "no_product_claims" and (
        evidence["subject_binding"] != "not_applicable"
        or evidence["claim_mapping_count"] != 0
        or evidence["eligible_fact_count"] != 0
    ):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    if evidence["scope"] == "product_claims" and (
        evidence["subject_binding"] != "product"
        or evidence["claim_mapping_count"] < 1
        or evidence["eligible_fact_count"] < 1
    ):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")


def _parse_plan(
    record: SvRunPlanRecord,
    task: SvTaskRecord,
    run: SvRunRecord,
    brief_digest: str,
) -> MissionPlan:
    payload = record.plan_payload
    if not isinstance(payload, dict):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    if canonical_digest(payload) != record.plan_digest:
        raise JournalIntegrityError("mission_control_plan_digest_mismatch")
    if frozenset(payload) != _PLAN_PAYLOAD_KEYS:
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    expected = {
        "schema_version": "sv-run-plan/v1",
        "task_id": str(task.id),
        "task_revision": task.current_revision,
        "run_id": str(run.id),
        "run_revision": run.revision,
        "version": record.version,
        "workflow_name": record.workflow_name,
        "workflow_version": record.workflow_version,
        "capability_catalog_version": record.capability_catalog_version,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise JournalIntegrityError("mission_control_plan_scope_invalid")
    if (
        run.primary_mechanism is None
        or run.creative_dimension is None
        or payload.get("primary_mechanism") != run.primary_mechanism
        or payload.get("creative_dimension") != run.creative_dimension
    ):
        raise JournalIntegrityError("mission_control_plan_axis_invalid")
    raw_steps = payload.get("steps")
    raw_input_refs = payload.get("input_refs")
    raw_limitations = payload.get("limitations")
    if (
        not isinstance(raw_steps, list)
        or not raw_steps
        or not isinstance(raw_input_refs, list)
        or not isinstance(raw_limitations, list)
    ):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    if raw_input_refs != record.input_refs:
        raise JournalIntegrityError("mission_control_plan_row_mismatch")
    _validate_plan_input_refs(
        raw_input_refs,
        task=task,
        brief_digest=brief_digest,
        catalog_digest=payload.get("capability_catalog_digest"),
    )
    steps: list[MissionPlanStep] = []
    for item in raw_steps:
        if not isinstance(item, dict) or frozenset(item) != _PLAN_STEP_KEYS:
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        step_id = item.get("step_id")
        order = item.get("order")
        capability_name = item.get("capability_name")
        capability_version = item.get("capability_version")
        execution_mode = item.get("execution_mode")
        guards = item.get("guards")
        if (
            not _text(step_id)
            or not isinstance(order, int)
            or order < 1
            or not _text(capability_name)
            or not _text(capability_version)
            or execution_mode != "planning_only"
            or not isinstance(guards, list)
        ):
            raise JournalIntegrityError("mission_control_plan_payload_invalid")
        for guard in guards:
            _validate_plan_guard(guard, task=task, run=run)
        steps.append(
            MissionPlanStep(
                step_id=step_id,
                order=order,
                capability_name=capability_name,
                capability_version=capability_version,
                execution_mode="planning_only",
            )
        )
    if tuple(step.order for step in steps) != tuple(range(1, len(steps) + 1)):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    if len({step.step_id for step in steps}) != len(steps):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    if not raw_limitations or not all(_text(item) for item in raw_limitations):
        raise JournalIntegrityError("mission_control_plan_payload_invalid")
    return MissionPlan(
        ref=f"run-plan:{record.id}:v{record.version}",
        version=record.version,
        run_revision=record.run_revision,
        workflow_name=record.workflow_name,
        workflow_version=record.workflow_version,
        capability_catalog_version=record.capability_catalog_version,
        steps=tuple(steps),
        limitations=tuple(raw_limitations),
        created_at=record.created_at,
    )


def _parse_artifact(
    record: SvArtifactRecord,
    *,
    task: SvTaskRecord,
    run: SvRunRecord,
) -> MissionArtifact:
    if canonical_digest(record.payload) != record.payload_digest:
        raise JournalIntegrityError("mission_control_artifact_digest_mismatch")
    try:
        payload = validate_artifact(record.payload, expected_type=record.artifact_type)
    except ArtifactValidationError as exc:
        code = (
            "mission_control_artifact_content_digest_mismatch"
            if exc.code == "ARTIFACT_DIGEST_MISMATCH"
            else "mission_control_artifact_schema_invalid"
        )
        raise JournalIntegrityError(code) from exc
    created_at = payload.get("created_at")
    try:
        payload_created_at = datetime.fromisoformat(str(created_at))
    except ValueError as exc:
        raise JournalIntegrityError("mission_control_artifact_envelope_drift") from exc
    if (
        record.task_id != task.id
        or record.task_revision != task.current_revision
        or record.run_id != run.id
        or record.run_revision != run.revision
        or payload.get("schema_version") != record.schema_version
        or payload.get("artifact_id") != str(record.artifact_id)
        or payload.get("artifact_type") != record.artifact_type
        or payload.get("task_ref") != str(task.id)
        or payload.get("run_ref") != str(run.id)
        or payload.get("version") != record.version
        or payload.get("status") != record.status
        or payload.get("evidence_level") != record.evidence_level
        or payload.get("proof_level") != record.proof_level
        or payload.get("input_refs") != record.input_refs
        or payload_created_at != record.created_at
    ):
        raise JournalIntegrityError("mission_control_artifact_envelope_drift")
    try:
        return MissionArtifact(
            ref=f"artifact:{record.artifact_id}:v{record.version}",
            artifact_type=ArtifactType(record.artifact_type),
            version=record.version,
            status=ArtifactStatus(record.status),
            evidence_level=EvidenceLevel(record.evidence_level),
            proof_level=ProofLevel(record.proof_level),
            created_at=record.created_at,
        )
    except ValueError as exc:
        raise JournalIntegrityError("mission_control_artifact_invalid") from exc


def _stages_without_run() -> tuple[tuple[MissionStage, ...], StageKey]:
    return (
        tuple(
            MissionStage(
                key=key,
                label=label,
                status=StageStatus.ACTIVE if index == 0 else StageStatus.WAITING,
            )
            for index, (key, label) in enumerate(_STAGE_LABELS)
        ),
        StageKey.REFERENCE_ADMISSION,
    )


def _stages_for(
    run: MissionRun,
    plan: MissionPlan | None,
    artifact: MissionArtifact | None,
    blockers: list[MissionBlocker],
) -> tuple[tuple[MissionStage, ...], StageKey]:
    if artifact is not None:
        current = _ARTIFACT_STAGE[artifact.artifact_type]
    elif plan is not None or run.primary_mechanism is not None:
        current = StageKey.MECHANISM_SELECTION
    else:
        current = StageKey.REFERENCE_ADMISSION
    index = tuple(key for key, _ in _STAGE_LABELS).index(current)
    current_blocked = bool(blockers) or run.state in {
        RunState.AWAITING_APPROVAL,
        RunState.BLOCKED,
        RunState.FAILED,
    }
    artifact_completed = artifact is not None and artifact.status in {
        ArtifactStatus.APPROVED,
        ArtifactStatus.FINAL_WITH_LIMITS,
    }
    statuses = [StageStatus.UNKNOWN] * len(_STAGE_LABELS)
    statuses[index] = (
        StageStatus.BLOCKED
        if current_blocked
        else StageStatus.COMPLETED
        if artifact_completed
        else StageStatus.ACTIVE
    )
    return (
        tuple(
            MissionStage(key=key, label=label, status=statuses[position])
            for position, (key, label) in enumerate(_STAGE_LABELS)
        ),
        current,
    )


def _state_blockers(
    brief: TaskBrief,
    run: MissionRun,
    task_ref: str,
    run_ref: str,
    approvals: tuple[SvApprovalRequestRecord, ...],
    approvals_truncated: bool,
    approval_frontier_inconsistent: bool,
    tool_runs: tuple[MissionToolRun, ...],
) -> list[MissionBlocker]:
    blockers: list[MissionBlocker] = []
    if brief.initial_rights_state in {RightsState.RESTRICTED, RightsState.BLOCKED}:
        blockers.append(
            MissionBlocker(
                "REFERENCE_RIGHTS_BLOCKED",
                "The Task rights state does not allow progress.",
                task_ref,
            )
        )
    if approvals_truncated:
        blockers.append(
            MissionBlocker(
                "APPROVAL_SET_TRUNCATED",
                "The bounded approval set cannot establish a complete current frontier.",
                run_ref,
            )
        )
    if approval_frontier_inconsistent:
        blockers.append(
            MissionBlocker(
                "APPROVAL_FRONTIER_INCONSISTENT",
                "A pending request is not bound to the verified current artifact.",
                run_ref,
            )
        )
    if run.state is RunState.AWAITING_APPROVAL:
        if approvals_truncated or approval_frontier_inconsistent:
            pass
        elif approvals:
            blockers.extend(
                MissionBlocker(
                    "APPROVAL_REQUIRED",
                    f"Human decision required for {approval.gate_kind}.",
                    f"approval:{approval.id}:v{approval.request_version}",
                )
                for approval in approvals
            )
        else:
            blockers.append(
                MissionBlocker(
                    "APPROVAL_STATE_INCONSISTENT",
                    "Run awaits approval without a current undecided request.",
                    run_ref,
                )
            )
    elif approvals:
        blockers.append(
            MissionBlocker(
                "APPROVAL_STATE_INCONSISTENT",
                "A current undecided request exists outside awaiting_approval state.",
                run_ref,
            )
        )
    if run.state is RunState.AWAITING_INPUT:
        blockers.append(MissionBlocker("INPUT_REQUIRED", "User input is required.", run_ref))
    elif run.state is RunState.BLOCKED:
        blockers.append(MissionBlocker("RUN_BLOCKED", "The Run is blocked.", run_ref))
    elif run.state is RunState.FAILED:
        blockers.append(
            MissionBlocker("RUN_TECHNICAL_FAILURE", "The Run failed technically.", run_ref)
        )
    blockers.extend(
        MissionBlocker(
            tool.stable_error_code or f"TOOL_RUN_{tool.status.value.upper()}",
            tool.recovery_action or f"ToolRun is {tool.status.value}.",
            tool.ref,
        )
        for tool in tool_runs
        if tool.status in {ToolRunStatus.FAILED, ToolRunStatus.UNAVAILABLE, ToolRunStatus.UNKNOWN}
    )
    return blockers


def _next_action(
    run: MissionRun | None,
    blockers: tuple[MissionBlocker, ...],
    basis_refs: tuple[str, ...],
) -> MissionNextSafeAction:
    blocker_codes = {item.code for item in blockers}
    if blocker_codes & {
        "PLAN_FRONTIER_UNAVAILABLE",
        "PLAN_FRONTIER_AMBIGUOUS",
        "ARTIFACT_FRONTIER_UNAVAILABLE",
        "ARTIFACT_FRONTIER_AMBIGUOUS",
        "ARTIFACT_FRONTIER_UNVERIFIED",
        "APPROVAL_SET_TRUNCATED",
        "APPROVAL_FRONTIER_INCONSISTENT",
        "APPROVAL_STATE_INCONSISTENT",
    }:
        return MissionNextSafeAction(
            kind="refresh_evidence",
            label="Refresh authoritative state",
            reason="The current frontier cannot be established without verified evidence.",
            reason_code="FRONTIER_EVIDENCE_REQUIRED",
            interaction_intent="request_evidence",
            basis_refs=basis_refs,
        )
    if run is None:
        return MissionNextSafeAction(
            kind="preview_request_plan",
            label="Preview a plan request",
            reason="Mission Control is read-only and no public Run writer is available.",
            reason_code="PLAN_REQUEST_PREVIEW_ONLY",
            interaction_intent="request_plan",
            basis_refs=basis_refs,
        )
    unresolved = tuple(
        blocker
        for blocker in blockers
        if blocker.code not in {"APPROVAL_REQUIRED", "INPUT_REQUIRED"}
    )
    if any(
        blocker.code == "RUN_TECHNICAL_FAILURE" or blocker.source_ref.startswith("tool-run:")
        for blocker in unresolved
    ):
        return MissionNextSafeAction(
            kind="recovery_unavailable",
            label="Recovery is unavailable here",
            reason="A technical failure exists without a verified recovery receipt.",
            reason_code="RECOVERY_RECEIPT_UNAVAILABLE",
            interaction_intent=None,
            basis_refs=basis_refs,
        )
    if unresolved:
        return MissionNextSafeAction(
            kind="preview_request_evidence",
            label="Preview an evidence request",
            reason="An unresolved blocker must be resolved before any future advance.",
            reason_code="BLOCKER_RESOLUTION_REQUIRED",
            interaction_intent="request_evidence",
            basis_refs=basis_refs,
        )
    by_state: dict[RunState, tuple[str, str, str, str, str | None]] = {
        RunState.DRAFT: (
            "preview_request_plan",
            "Preview a plan request",
            "The Run has no current executable plan.",
            "PLAN_REQUEST_PREVIEW_ONLY",
            "request_plan",
        ),
        RunState.PLANNING: (
            "preview_request_plan",
            "Review planning state",
            "Planning remains authoritative and no action can execute here.",
            "PLAN_REQUEST_PREVIEW_ONLY",
            "request_plan",
        ),
        RunState.AWAITING_INPUT: (
            "preview_provide_input",
            "Preview additional input",
            "The Run requires explicit user input.",
            "INPUT_REQUIRED",
            "provide_input",
        ),
        RunState.RUNNABLE: (
            "preview_advance",
            "Preview the next safe advance",
            "Prerequisites must be rechecked before any future execution.",
            "PREREQUISITES_REQUIRE_RECHECK",
            "advance",
        ),
        RunState.RUNNING: (
            "observe_run",
            "Observe current activity",
            "The current Run is active; this surface cannot dispatch work.",
            "RUN_ACTIVE",
            None,
        ),
        RunState.AWAITING_APPROVAL: (
            "open_approval",
            "Open the current decision request",
            "Human approval is a separate seam and cannot be decided here.",
            "HUMAN_APPROVAL_REQUIRED",
            None,
        ),
        RunState.BLOCKED: (
            "preview_request_evidence",
            "Preview an evidence request",
            "The blocker must be resolved without guessing.",
            "BLOCKER_RESOLUTION_REQUIRED",
            "request_evidence",
        ),
        RunState.COMPLETED_WITH_LIMITS: (
            "review_results",
            "Review results and limitations",
            "Completion with limits is not publication or production acceptance.",
            "COMPLETED_WITH_LIMITS",
            None,
        ),
        RunState.FAILED: (
            "recovery_unavailable",
            "Recovery is unavailable here",
            "No verified command receipt is bound to this projection.",
            "RECOVERY_RECEIPT_UNAVAILABLE",
            None,
        ),
        RunState.STOPPED: (
            "no_action",
            "No action available",
            "The current Run was stopped.",
            "RUN_STOPPED",
            None,
        ),
    }
    kind, label, reason, reason_code, intent = by_state[run.state]
    return MissionNextSafeAction(
        kind=kind,
        label=label,
        reason=reason,
        reason_code=reason_code,
        interaction_intent=intent,
        basis_refs=basis_refs,
    )


def _brief_from_record(record: SvTaskRevisionRecord) -> TaskBrief:
    try:
        return TaskBrief.create(
            goal_track=GoalTrack(record.goal_track),
            decision_question=record.decision_question,
            subject=record.subject,
            platform=TargetPlatform(record.platform),
            market=record.market,
            language=record.language,
            performance_window=PerformanceWindow(
                start=record.performance_start,
                end=record.performance_end,
                timezone=record.performance_timezone,
            ),
            stop_condition=record.stop_condition,
            initial_rights_state=RightsState(record.initial_rights_state),
        )
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("mission_control_task_revision_invalid") from exc


def _text(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
