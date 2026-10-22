from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, exists, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvArtifactRecord,
    SvDecisionEventRecord,
    SvRunPlanRecord,
    SvRunRecord,
    SvTaskEventRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvToolRunEventRecord,
    SvToolRunRecord,
)
from app.adapters.db.sv_agent_repository import SvAgentRepository
from app.domain.sv_agent.entities import RunState
from app.domain.sv_agent.errors import JournalIntegrityError, TaskNotFound
from app.domain.sv_agent.runtime_records import (
    ApprovalDecision,
    ApprovalGateKind,
    ArtifactStatus,
    ArtifactType,
    DecisionEventType,
    EventStream,
    ReplayEntry,
    ReplayQuery,
    TaskEventType,
    ToolRunEventType,
    ToolRunStatus,
)

_MAX_APPROVALS = 100
_MAX_TIMELINE_ENTRIES = 200
_MAX_STATEMENTS = 20
_MAX_STATEMENT_LENGTH = 256
_SAFE_STATEMENT_KEYS = frozenset(
    {
        "code",
        "condition",
        "effect",
        "field",
        "limitation",
        "message",
        "proof_level",
        "source_kind",
        "state",
        "status",
        "summary",
    }
)
_UUID_TEXT = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_DIGEST_TEXT = re.compile(r"[0-9a-f]{64}", re.IGNORECASE)
_PRIVATE_LOCATION_TEXT = re.compile(
    r"(?:\b(?:https?|file|s3|gs)://|(?:^|[^a-z0-9])(?:~?[/\\](?=\S)|[a-z]:[/\\](?=\S)|[a-z0-9._-]+[/\\]\S+))",
    re.IGNORECASE,
)
_CREDENTIAL_TEXT = re.compile(
    r"(?:\b(?:api[\s_-]?key|access[\s_-]?key|client[\s_-]?secret|private[\s_-]?key|credential(?:s)?|authorization|bearer|password|secret|token)\b(?:\s+|\s*[:=]\s*)\S+|\bsk-[a-z0-9_-]{8,})",
    re.IGNORECASE,
)
_JSON_FRAGMENT_TEXT = re.compile(r"(?:\{.*\}|\[.*\])", re.DOTALL)
_EXPLICIT_NON_EFFECTS = (
    "does_not_write_postgresql",
    "does_not_decide_approvals",
    "does_not_advance_task_or_run",
    "does_not_call_providers",
    "does_not_render_or_publish",
)


class ApprovalDecisionState(StrEnum):
    PENDING = "pending"
    DECIDED = "decided"


class ApprovalScopeState(StrEnum):
    CURRENT = "current"
    STALE = "stale"


class ReplayTimelineKind(StrEnum):
    TASK_EVENT = "task_event"
    PLAN_REVISION = "plan_revision"
    ARTIFACT_REVISION = "artifact_revision"
    APPROVAL_REQUEST = "approval_request"
    TOOL_RUN = "tool_run"
    DECISION = "decision"


@dataclass(frozen=True, slots=True)
class ApprovalReplayTask:
    task_id: UUID
    task_revision: int
    subject: str


@dataclass(frozen=True, slots=True)
class ApprovalReplayRun:
    run_id: UUID
    run_revision: int
    state: RunState


@dataclass(frozen=True, slots=True)
class ApprovalAudit:
    task_revision: int
    run_revision: int


@dataclass(frozen=True, slots=True)
class ApprovalCard:
    request_version: int
    gate_kind: ApprovalGateKind
    target_artifact_type: ArtifactType
    target_version: int
    decision_state: ApprovalDecisionState
    scope_state: ApprovalScopeState
    predicted_effects: tuple[str, ...]
    explicit_non_effects: tuple[str, ...]
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    stale_conditions: tuple[str, ...]
    decision: ApprovalDecision | None
    decided_at: datetime | None
    audit: ApprovalAudit


@dataclass(frozen=True, slots=True)
class ApprovalSummary:
    pending: int
    decided: int
    stale: int


@dataclass(frozen=True, slots=True)
class ReplayTimelineEntry:
    event_sequence: int
    kind: ReplayTimelineKind
    event_type: str
    summary: str
    task_revision: int
    run_revision: int | None


@dataclass(frozen=True, slots=True)
class ReplayTimeline:
    snapshot_through_sequence: int
    next_after_sequence: int | None
    truncated: bool
    entries: tuple[ReplayTimelineEntry, ...]


@dataclass(frozen=True, slots=True)
class ApprovalReplayProjection:
    schema_version: str
    authority: str
    task: ApprovalReplayTask
    run: ApprovalReplayRun | None
    summary: ApprovalSummary
    decision_vocabulary: tuple[ApprovalDecision, ...]
    decision_available: bool
    approvals: tuple[ApprovalCard, ...]
    approvals_truncated: bool
    timeline: ReplayTimeline
    explicit_non_effects: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _TaskSnapshot:
    task_id: UUID
    current_revision: int
    active_run_id: UUID | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class _RunSnapshot:
    run_id: UUID
    task_id: UUID
    task_revision: int
    revision: int
    state: str
    updated_at: datetime


class ApprovalReplayWorkspace:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect(self, task_id: UUID) -> ApprovalReplayProjection:
        task, task_revision = await self._load_task(task_id)
        run = await self._load_run(task)
        task_snapshot = _TaskSnapshot(
            task_id=task.id,
            current_revision=task.current_revision,
            active_run_id=task.active_run_id,
            updated_at=task.updated_at,
        )
        run_snapshot = (
            _RunSnapshot(
                run_id=run.id,
                task_id=run.task_id,
                task_revision=run.task_revision,
                revision=run.revision,
                state=run.state,
                updated_at=run.updated_at,
            )
            if run is not None
            else None
        )
        repository = SvAgentRepository(self._session)
        boundary_page = await repository.read_replay(ReplayQuery(task_id=task.id, limit=1))
        through_sequence = boundary_page.snapshot_through_sequence
        snapshot_event_count = boundary_page.snapshot_event_count
        if through_sequence < 1:
            raise JournalIntegrityError("approval_replay_event_boundary_missing")

        approval_rows, approvals_truncated = await self._load_approvals(
            task.id,
            through_sequence,
        )
        decisions = await self._load_decisions(approval_rows, through_sequence)
        approvals = tuple(
            [
                await self._project_approval(
                    request, decisions.get((request.id, request.request_version)), task, run
                )
                for request in approval_rows
            ]
        )

        replay = await repository.read_replay(
            ReplayQuery(
                task_id=task.id,
                through_sequence=through_sequence,
                limit=_MAX_TIMELINE_ENTRIES,
            )
        )
        timeline_entries = tuple(
            [await self._project_timeline_entry(entry) for entry in replay.entries]
        )
        await self._assert_approval_journal_complete(task.id, through_sequence)
        await self._assert_snapshot_unchanged(
            task_snapshot,
            run_snapshot,
            through_sequence,
            snapshot_event_count,
        )

        return ApprovalReplayProjection(
            schema_version="sv-approval-replay/v1",
            authority="postgresql",
            task=ApprovalReplayTask(
                task_id=task_snapshot.task_id,
                task_revision=task_snapshot.current_revision,
                subject=_safe_visible_text(
                    task_revision.subject,
                    "approval_task_subject",
                ),
            ),
            run=(
                ApprovalReplayRun(
                    run_id=run_snapshot.run_id,
                    run_revision=run_snapshot.revision,
                    state=RunState(run_snapshot.state),
                )
                if run_snapshot is not None
                else None
            ),
            summary=ApprovalSummary(
                pending=sum(
                    item.decision_state is ApprovalDecisionState.PENDING for item in approvals
                ),
                decided=sum(
                    item.decision_state is ApprovalDecisionState.DECIDED for item in approvals
                ),
                stale=sum(item.scope_state is ApprovalScopeState.STALE for item in approvals),
            ),
            decision_vocabulary=tuple(ApprovalDecision),
            decision_available=False,
            approvals=approvals,
            approvals_truncated=approvals_truncated,
            timeline=ReplayTimeline(
                snapshot_through_sequence=replay.snapshot_through_sequence,
                next_after_sequence=replay.next_after_sequence,
                truncated=replay.next_after_sequence is not None,
                entries=timeline_entries,
            ),
            explicit_non_effects=_EXPLICIT_NON_EFFECTS,
        )

    async def _load_task(
        self,
        task_id: UUID,
    ) -> tuple[SvTaskRecord, SvTaskRevisionRecord]:
        task = await self._session.get(SvTaskRecord, task_id)
        if task is None:
            raise TaskNotFound(task_id)
        revision = await self._session.get(
            SvTaskRevisionRecord,
            (task.id, task.current_revision),
        )
        if revision is None:
            raise JournalIntegrityError("approval_replay_task_revision_missing")
        return task, revision

    async def _load_run(self, task: SvTaskRecord) -> SvRunRecord | None:
        if task.active_run_id is None:
            return None
        run = await self._session.get(SvRunRecord, task.active_run_id)
        if run is None or run.task_id != task.id or run.task_revision != task.current_revision:
            raise JournalIntegrityError("approval_replay_active_run_scope_invalid")
        try:
            RunState(run.state)
        except ValueError as exc:
            raise JournalIntegrityError("approval_replay_run_state_invalid") from exc
        return run

    async def _load_approvals(
        self,
        task_id: UUID,
        through_sequence: int,
    ) -> tuple[tuple[SvApprovalRequestRecord, ...], bool]:
        event_rows = (
            await self._session.scalars(
                select(SvTaskEventRecord)
                .where(
                    SvTaskEventRecord.task_id == task_id,
                    SvTaskEventRecord.event_type == TaskEventType.APPROVAL_REQUESTED.value,
                    SvTaskEventRecord.event_sequence <= through_sequence,
                )
                .order_by(SvTaskEventRecord.event_sequence.desc())
                .limit(_MAX_APPROVALS + 1)
            )
        ).all()
        approvals: list[SvApprovalRequestRecord] = []
        seen: set[tuple[UUID, int]] = set()
        for row in event_rows[:_MAX_APPROVALS]:
            entry = _task_replay_entry(row)
            request = await self._validate_approval_event(entry)
            key = (request.id, request.request_version)
            if key in seen:
                raise JournalIntegrityError("approval_event_duplicate")
            seen.add(key)
            approvals.append(request)
        return tuple(approvals), len(event_rows) > _MAX_APPROVALS

    async def _load_decisions(
        self,
        approvals: tuple[SvApprovalRequestRecord, ...],
        through_sequence: int,
    ) -> dict[tuple[UUID, int], SvDecisionEventRecord]:
        if not approvals:
            return {}
        keys = [(request.id, request.request_version) for request in approvals]
        rows = (
            await self._session.scalars(
                select(SvDecisionEventRecord)
                .where(
                    tuple_(
                        SvDecisionEventRecord.approval_request_id,
                        SvDecisionEventRecord.approval_request_version,
                    ).in_(keys),
                    SvDecisionEventRecord.event_sequence <= through_sequence,
                )
                .order_by(SvDecisionEventRecord.event_sequence)
            )
        ).all()
        decisions: dict[tuple[UUID, int], SvDecisionEventRecord] = {}
        for row in rows:
            key = (row.approval_request_id, row.approval_request_version)
            if key in decisions:
                raise JournalIntegrityError("approval_decision_duplicate")
            decisions[key] = row
        return decisions

    async def _project_approval(
        self,
        request: SvApprovalRequestRecord,
        decision: SvDecisionEventRecord | None,
        task: SvTaskRecord,
        run: SvRunRecord | None,
    ) -> ApprovalCard:
        try:
            gate_kind = ApprovalGateKind(request.gate_kind)
        except ValueError as exc:
            raise JournalIntegrityError("approval_gate_unknown") from exc
        try:
            artifact_type = ArtifactType(request.artifact_type)
        except ValueError as exc:
            raise JournalIntegrityError("approval_target_type_unknown") from exc

        projected_decision: ApprovalDecision | None = None
        decided_at: datetime | None = None
        if decision is not None:
            self._validate_decision(request, decision)
            projected_decision = ApprovalDecision(decision.decision)
            decided_at = decision.created_at

        target = await self._load_approval_target(request, artifact_type)
        newest_version = await self._session.scalar(
            select(func.max(SvArtifactRecord.version)).where(
                SvArtifactRecord.artifact_id == target.artifact_id
            )
        )
        if newest_version is None:
            raise JournalIntegrityError("approval_target_binding_invalid")
        target_stale = (
            target.status
            in {
                ArtifactStatus.STALE.value,
                ArtifactStatus.SUPERSEDED.value,
            }
            or newest_version > target.version
        )
        is_current = (
            request.task_revision == task.current_revision
            and run is not None
            and request.run_id == run.id
            and request.run_revision == run.revision
            and not target_stale
        )
        return ApprovalCard(
            request_version=request.request_version,
            gate_kind=gate_kind,
            target_artifact_type=artifact_type,
            target_version=request.artifact_version,
            decision_state=(
                ApprovalDecisionState.DECIDED
                if decision is not None
                else ApprovalDecisionState.PENDING
            ),
            scope_state=(ApprovalScopeState.CURRENT if is_current else ApprovalScopeState.STALE),
            predicted_effects=_statement_list(request.predicted_effects, "predicted_effects"),
            explicit_non_effects=_statement_list(
                request.explicit_non_effects,
                "explicit_non_effects",
            ),
            evidence=_statement_mapping(request.evidence_summary, "evidence_summary"),
            limitations=_statement_list(request.limitations, "limitations"),
            stale_conditions=_statement_list(request.stale_if, "stale_if"),
            decision=projected_decision,
            decided_at=decided_at,
            audit=ApprovalAudit(
                task_revision=request.task_revision,
                run_revision=request.run_revision,
            ),
        )

    async def _load_approval_target(
        self,
        request: SvApprovalRequestRecord,
        artifact_type: ArtifactType,
    ) -> SvArtifactRecord:
        try:
            artifact_id = UUID(request.artifact_id)
        except ValueError as exc:
            raise JournalIntegrityError("approval_target_binding_invalid") from exc
        record = await self._session.get(
            SvArtifactRecord,
            (artifact_id, request.artifact_version),
        )
        if (
            record is None
            or record.artifact_type != artifact_type.value
            or record.payload_digest != request.artifact_digest
            or record.task_id != request.task_id
            or record.task_revision != request.task_revision
            or record.run_id != request.run_id
            or record.run_revision != request.run_revision
        ):
            raise JournalIntegrityError("approval_target_binding_invalid")
        try:
            ArtifactStatus(record.status)
        except ValueError as exc:
            raise JournalIntegrityError("approval_target_status_unknown") from exc
        return record

    def _validate_decision(
        self,
        request: SvApprovalRequestRecord,
        decision: SvDecisionEventRecord,
    ) -> None:
        if (
            decision.event_type != DecisionEventType.HUMAN_DECISION_RECORDED.value
            or decision.approval_request_id != request.id
            or decision.approval_request_version != request.request_version
            or decision.request_digest != request.request_digest
            or decision.task_id != request.task_id
            or decision.task_revision != request.task_revision
            or decision.run_id != request.run_id
            or decision.run_revision != request.run_revision
            or decision.decided_by_kind != "human"
        ):
            raise JournalIntegrityError("approval_decision_binding_invalid")
        try:
            parsed_decision = ApprovalDecision(decision.decision)
        except ValueError as exc:
            raise JournalIntegrityError("approval_decision_unknown") from exc
        expected_payload = {
            "approval_request_id": str(request.id),
            "decision": parsed_decision.value,
        }
        if decision.payload != expected_payload:
            raise JournalIntegrityError("approval_decision_payload_invalid")
        ReplayEntry(
            event_id=decision.id,
            event_sequence=decision.event_sequence,
            stream=EventStream.DECISION,
            event_type=DecisionEventType.HUMAN_DECISION_RECORDED,
            task_id=decision.task_id,
            run_id=decision.run_id,
            task_revision=decision.task_revision,
            run_revision=decision.run_revision,
            payload=decision.payload,
            payload_digest=decision.payload_digest,
        )

    async def _project_timeline_entry(self, entry: ReplayEntry) -> ReplayTimelineEntry:
        kind = ReplayTimelineKind.TASK_EVENT
        summary = _task_event_summary(entry.event_type)
        if entry.stream is EventStream.TASK:
            if entry.event_type is TaskEventType.RUN_PLAN_RECORDED:
                plan_record = await self._validate_plan_event(entry)
                kind = ReplayTimelineKind.PLAN_REVISION
                summary = f"RunPlan v{plan_record.version} recorded."
            elif entry.event_type is TaskEventType.ARTIFACT_RECORDED:
                artifact_record = await self._validate_artifact_event(entry)
                kind = ReplayTimelineKind.ARTIFACT_REVISION
                summary = f"{artifact_record.artifact_type} v{artifact_record.version} recorded."
            elif entry.event_type is TaskEventType.APPROVAL_REQUESTED:
                approval_record = await self._validate_approval_event(entry)
                kind = ReplayTimelineKind.APPROVAL_REQUEST
                summary = (
                    f"{approval_record.gate_kind} approval request "
                    f"v{approval_record.request_version} recorded."
                )
        elif entry.stream is EventStream.TOOL_RUN:
            await self._validate_tool_run_event(entry)
            kind = ReplayTimelineKind.TOOL_RUN
            summary = _tool_event_summary(entry.event_type)
        else:
            await self._validate_decision_event(entry)
            kind = ReplayTimelineKind.DECISION
            summary = f"Human decision {entry.payload['decision']} recorded."
        return ReplayTimelineEntry(
            event_sequence=entry.event_sequence,
            kind=kind,
            event_type=entry.event_type.value,
            summary=summary,
            task_revision=entry.task_revision,
            run_revision=entry.run_revision,
        )

    async def _validate_plan_event(self, entry: ReplayEntry) -> SvRunPlanRecord:
        payload = _closed_handle(entry.payload, {"run_plan_id", "version", "digest"})
        record = await self._session.get(SvRunPlanRecord, _uuid(payload["run_plan_id"]))
        if (
            record is None
            or record.task_id != entry.task_id
            or record.task_revision != entry.task_revision
            or record.run_id != entry.run_id
            or record.run_revision != entry.run_revision
            or record.version != _positive_int(payload["version"])
            or record.plan_digest != _digest(payload["digest"])
        ):
            raise JournalIntegrityError("run_plan_event_binding_invalid")
        return record

    async def _validate_artifact_event(self, entry: ReplayEntry) -> SvArtifactRecord:
        payload = _closed_handle(
            entry.payload,
            {"artifact_id", "artifact_type", "version", "digest"},
        )
        artifact_id = _uuid(payload["artifact_id"])
        version = _positive_int(payload["version"])
        record = await self._session.get(SvArtifactRecord, (artifact_id, version))
        if (
            record is None
            or record.task_id != entry.task_id
            or record.task_revision != entry.task_revision
            or record.run_id != entry.run_id
            or record.run_revision != entry.run_revision
            or record.artifact_type != _text(payload["artifact_type"])
            or record.payload_digest != _digest(payload["digest"])
        ):
            raise JournalIntegrityError("artifact_event_binding_invalid")
        return record

    async def _validate_approval_event(self, entry: ReplayEntry) -> SvApprovalRequestRecord:
        payload = _closed_handle(
            entry.payload,
            {"approval_request_id", "request_version", "request_digest"},
        )
        request_id = _uuid(payload["approval_request_id"])
        request_version = _positive_int(payload["request_version"])
        record = await self._session.get(
            SvApprovalRequestRecord,
            (request_id, request_version),
        )
        if (
            record is None
            or record.task_id != entry.task_id
            or record.task_revision != entry.task_revision
            or record.run_id != entry.run_id
            or record.run_revision != entry.run_revision
            or record.request_digest != _digest(payload["request_digest"])
        ):
            raise JournalIntegrityError("approval_event_binding_invalid")
        return record

    async def _validate_decision_event(self, entry: ReplayEntry) -> None:
        payload = _closed_handle(entry.payload, {"approval_request_id", "decision"})
        request_id = _uuid(payload["approval_request_id"])
        decision = await self._session.scalar(
            select(SvDecisionEventRecord).where(SvDecisionEventRecord.id == entry.event_id)
        )
        if decision is None or decision.approval_request_id != request_id:
            raise JournalIntegrityError("decision_event_missing")
        request = await self._session.get(
            SvApprovalRequestRecord,
            (decision.approval_request_id, decision.approval_request_version),
        )
        if request is None:
            raise JournalIntegrityError("decision_event_request_invalid")
        self._validate_decision(request, decision)

    async def _validate_tool_run_event(self, entry: ReplayEntry) -> None:
        event = await self._session.scalar(
            select(SvToolRunEventRecord).where(SvToolRunEventRecord.id == entry.event_id)
        )
        if (
            event is None
            or event.event_type != entry.event_type.value
            or event.task_id != entry.task_id
            or event.task_revision != entry.task_revision
            or event.run_id != entry.run_id
            or event.run_revision != entry.run_revision
            or event.payload != dict(entry.payload)
            or event.payload_digest != entry.payload_digest
        ):
            raise JournalIntegrityError("tool_run_event_binding_invalid")
        record = await self._session.get(SvToolRunRecord, event.tool_run_id)
        try:
            payload = _closed_handle(
                entry.payload,
                {
                    "artifact_refs",
                    "attempt_token",
                    "input_digest",
                    "recovery_action",
                    "result_digest",
                    "revision",
                    "stable_error_code",
                    "status",
                    "tool_name",
                    "tool_run_id",
                    "tool_version",
                },
            )
            payload_tool_run_id = _uuid(payload["tool_run_id"])
            payload_status = ToolRunStatus(_text(payload["status"]))
            payload_revision = _positive_int(payload["revision"])
            payload_attempt = _positive_int(payload["attempt_token"])
            payload_input_digest = _digest(payload["input_digest"])
            payload_tool_name = payload["tool_name"]
            payload_tool_version = payload["tool_version"]
            if not isinstance(payload_tool_name, str) or not isinstance(payload_tool_version, str):
                raise JournalIntegrityError("tool_run_event_binding_invalid")
            if not isinstance(payload["artifact_refs"], list):
                raise JournalIntegrityError("tool_run_event_binding_invalid")
            if payload["stable_error_code"] is not None and not isinstance(
                payload["stable_error_code"], str
            ):
                raise JournalIntegrityError("tool_run_event_binding_invalid")
            if payload["recovery_action"] is not None and not isinstance(
                payload["recovery_action"], str
            ):
                raise JournalIntegrityError("tool_run_event_binding_invalid")
        except (JournalIntegrityError, KeyError, TypeError, ValueError) as exc:
            raise JournalIntegrityError("tool_run_event_binding_invalid") from exc
        expected_event_type = {
            ToolRunStatus.PENDING: ToolRunEventType.CREATED,
            ToolRunStatus.RUNNING: ToolRunEventType.STARTED,
            ToolRunStatus.COMPLETED: ToolRunEventType.COMPLETED,
            ToolRunStatus.FAILED: ToolRunEventType.FAILED,
            ToolRunStatus.UNAVAILABLE: ToolRunEventType.UNAVAILABLE,
            ToolRunStatus.UNKNOWN: ToolRunEventType.EFFECT_UNKNOWN,
        }[payload_status]
        result_digest = payload["result_digest"]
        result_binding_valid = (
            isinstance(result_digest, str) and _DIGEST_TEXT.fullmatch(result_digest) is not None
            if payload_status is ToolRunStatus.COMPLETED
            else result_digest is None
        )
        if (
            record is None
            or payload_tool_run_id != event.tool_run_id
            or record.id != event.tool_run_id
            or record.task_id != event.task_id
            or record.task_revision != event.task_revision
            or record.run_id != event.run_id
            or record.run_revision != event.run_revision
            or record.attempt_token != event.attempt_token
            or payload_attempt != event.attempt_token
            or payload_revision > record.revision
            or entry.event_type is not expected_event_type
            or payload_input_digest != record.input_digest
            or payload_tool_name != record.tool_name
            or payload_tool_version != record.tool_version
            or not result_binding_valid
        ):
            raise JournalIntegrityError("tool_run_event_binding_invalid")
        if payload_revision == record.revision and (
            payload_status.value != record.status
            or payload["artifact_refs"] != record.artifact_refs
            or payload["stable_error_code"] != record.stable_error_code
            or payload["recovery_action"] != record.recovery_action
        ):
            raise JournalIntegrityError("tool_run_event_binding_invalid")

    async def _assert_snapshot_unchanged(
        self,
        task: _TaskSnapshot,
        run: _RunSnapshot | None,
        through_sequence: int,
        snapshot_event_count: int,
    ) -> None:
        current_snapshot = await SvAgentRepository(self._session).read_replay(
            ReplayQuery(task_id=task.task_id, limit=1)
        )
        if (
            current_snapshot.snapshot_through_sequence != through_sequence
            or current_snapshot.snapshot_event_count != snapshot_event_count
        ):
            raise JournalIntegrityError("approval_replay_snapshot_changed")
        if run is None:
            task_row = (
                await self._session.execute(
                    select(
                        SvTaskRecord.current_revision,
                        SvTaskRecord.active_run_id,
                        SvTaskRecord.updated_at,
                    ).where(SvTaskRecord.id == task.task_id)
                )
            ).one_or_none()
            if task_row is None or tuple(task_row) != (
                task.current_revision,
                task.active_run_id,
                task.updated_at,
            ):
                raise JournalIntegrityError("approval_replay_snapshot_changed")
            return
        run_row = (
            await self._session.execute(
                select(
                    SvTaskRecord.current_revision,
                    SvTaskRecord.active_run_id,
                    SvTaskRecord.updated_at,
                    SvRunRecord.task_id,
                    SvRunRecord.task_revision,
                    SvRunRecord.revision,
                    SvRunRecord.state,
                    SvRunRecord.updated_at,
                )
                .join(SvRunRecord, SvRunRecord.id == SvTaskRecord.active_run_id)
                .where(SvTaskRecord.id == task.task_id, SvRunRecord.id == run.run_id)
            )
        ).one_or_none()
        if run_row is None or tuple(run_row) != (
            task.current_revision,
            task.active_run_id,
            task.updated_at,
            run.task_id,
            run.task_revision,
            run.revision,
            run.state,
            run.updated_at,
        ):
            raise JournalIntegrityError("approval_replay_snapshot_changed")

    async def _assert_approval_journal_complete(
        self,
        task_id: UUID,
        through_sequence: int,
    ) -> None:
        matching_event = exists(
            select(SvTaskEventRecord.id).where(
                SvTaskEventRecord.task_id == SvApprovalRequestRecord.task_id,
                SvTaskEventRecord.task_revision == SvApprovalRequestRecord.task_revision,
                SvTaskEventRecord.run_id == SvApprovalRequestRecord.run_id,
                SvTaskEventRecord.run_revision == SvApprovalRequestRecord.run_revision,
                SvTaskEventRecord.event_type == TaskEventType.APPROVAL_REQUESTED.value,
                SvTaskEventRecord.event_sequence <= through_sequence,
                SvTaskEventRecord.payload["approval_request_id"].as_string()
                == cast(SvApprovalRequestRecord.id, String),
                SvTaskEventRecord.payload["request_version"].as_integer()
                == SvApprovalRequestRecord.request_version,
                SvTaskEventRecord.payload["request_digest"].as_string()
                == SvApprovalRequestRecord.request_digest,
            )
        ).correlate(SvApprovalRequestRecord)
        missing = await self._session.scalar(
            select(
                exists(
                    select(SvApprovalRequestRecord.id).where(
                        SvApprovalRequestRecord.task_id == task_id,
                        ~matching_event,
                    )
                )
            )
        )
        if missing:
            raise JournalIntegrityError("approval_event_missing")


def _statement_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > _MAX_STATEMENTS:
        raise JournalIntegrityError(f"approval_{field}_invalid")
    return tuple(
        statement
        for index, item in enumerate(value)
        for statement in _statement_mapping(item, f"{field}_{index}")
    )


def _statement_mapping(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Mapping) or len(value) > _MAX_STATEMENTS:
        raise JournalIntegrityError(f"approval_{field}_invalid")
    statements: list[str] = []
    for key in sorted(value):
        if key not in _SAFE_STATEMENT_KEYS:
            raise JournalIntegrityError(f"approval_{field}_field_unsupported")
        raw = value[key]
        if not isinstance(raw, (str, int, bool)):
            raise JournalIntegrityError(f"approval_{field}_value_invalid")
        text = _safe_visible_text(
            str(raw).lower() if isinstance(raw, bool) else str(raw),
            f"approval_{field}_value",
        )
        statements.append(f"{key}: {text}")
    return tuple(statements)


def _safe_visible_text(
    value: Any,
    field: str,
    *,
    max_length: int = _MAX_STATEMENT_LENGTH,
) -> str:
    if not isinstance(value, str):
        raise JournalIntegrityError(f"{field}_invalid")
    text = value.strip()
    if not text or len(text) > max_length:
        raise JournalIntegrityError(f"{field}_invalid")
    if (
        _UUID_TEXT.search(text)
        or _DIGEST_TEXT.search(text)
        or _PRIVATE_LOCATION_TEXT.search(text)
        or _CREDENTIAL_TEXT.search(text)
        or _JSON_FRAGMENT_TEXT.search(text)
        or "chain_of_thought" in text.lower()
        or "private_reasoning" in text.lower()
    ):
        raise JournalIntegrityError(f"{field}_unsafe")
    return text


def _closed_handle(payload: Mapping[str, Any], keys: set[str]) -> Mapping[str, Any]:
    if set(payload) != keys:
        raise JournalIntegrityError("replay_event_handle_invalid")
    return payload


def _uuid(value: Any) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("replay_event_handle_invalid") from exc


def _positive_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise JournalIntegrityError("replay_event_handle_invalid")
    return value


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not _DIGEST_TEXT.fullmatch(value):
        raise JournalIntegrityError("replay_event_handle_invalid")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise JournalIntegrityError("replay_event_handle_invalid")
    return value


def _task_event_summary(event_type: object) -> str:
    labels: dict[object, str] = {
        TaskEventType.TASK_CREATED: "Task created.",
        TaskEventType.TASK_REVISED: "Task revised.",
        TaskEventType.RUN_CREATED: "Run created.",
        TaskEventType.RUN_STATE_TRANSITIONED: "Run state changed.",
        TaskEventType.REPLICATION_AXIS_SELECTED: "Replication axis selected.",
        TaskEventType.RUNTIME_LINEAGE_VERIFIED: "Runtime lineage verified.",
    }
    return labels.get(event_type, "Task journal event recorded.")


def _tool_event_summary(event_type: object) -> str:
    labels: dict[object, str] = {
        ToolRunEventType.CREATED: "ToolRun created.",
        ToolRunEventType.STARTED: "ToolRun started.",
        ToolRunEventType.COMPLETED: "Read tool completed.",
        ToolRunEventType.FAILED: "ToolRun failed.",
        ToolRunEventType.UNAVAILABLE: "ToolRun unavailable.",
        ToolRunEventType.EFFECT_UNKNOWN: "ToolRun effect remains unknown.",
        ToolRunEventType.TECHNICAL_JOB_LINKED: "Technical Job linked.",
    }
    return labels.get(event_type, "ToolRun event recorded.")


def _task_replay_entry(record: SvTaskEventRecord) -> ReplayEntry:
    try:
        event_type = TaskEventType(record.event_type)
    except ValueError as exc:
        raise JournalIntegrityError("approval_event_type_unknown") from exc
    return ReplayEntry(
        event_id=record.id,
        event_sequence=record.event_sequence,
        stream=EventStream.TASK,
        event_type=event_type,
        task_id=record.task_id,
        run_id=record.run_id,
        task_revision=record.task_revision,
        run_revision=record.run_revision,
        payload=record.payload,
        payload_digest=record.payload_digest,
    )
