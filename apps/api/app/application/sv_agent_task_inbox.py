from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, case, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvDecisionEventRecord,
    SvRunRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
)
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    RunState,
    TargetPlatform,
    TaskBrief,
)
from app.domain.sv_agent.errors import JournalIntegrityError
from app.domain.sv_agent.runtime_records import ApprovalGateKind

_MAX_INBOX_TASKS = 100


class TaskInboxLane(StrEnum):
    NEEDS_DECISION = "needs_decision"
    NEEDS_INPUT = "needs_input"
    BLOCKED = "blocked"
    TECHNICAL_ATTENTION = "technical_attention"
    AGENT_RUNNING = "agent_running"
    COMPLETED_WITH_LIMITS = "completed_with_limits"
    STOPPED = "stopped"
    NOT_STARTED = "not_started"


class TaskInboxOrderingReason(StrEnum):
    HUMAN_DECISION_REQUIRED = "human_decision_required"
    USER_INPUT_REQUIRED = "user_input_required"
    BUSINESS_BLOCKER_PRESENT = "business_blocker_present"
    RUNTIME_INTEGRITY_ATTENTION = "runtime_integrity_attention"
    TECHNICAL_FAILURE_REQUIRES_REVIEW = "technical_failure_requires_review"
    AGENT_WORK_IN_PROGRESS = "agent_work_in_progress"
    COMPLETED_WITH_DECLARED_LIMITS = "completed_with_declared_limits"
    STOPPED_BY_DECISION = "stopped_by_decision"
    RUN_NOT_STARTED = "run_not_started"


@dataclass(frozen=True, slots=True)
class TaskInboxItem:
    task_id: UUID
    task_revision: int
    goal_track: GoalTrack
    subject: str
    decision_question: str
    active_run_id: UUID | None
    active_run_revision: int | None
    run_state: RunState | None
    pending_decision_count: int
    pending_gate_kinds: tuple[ApprovalGateKind, ...]
    lane: TaskInboxLane
    ordering_reason: TaskInboxOrderingReason
    priority_at: datetime


@dataclass(frozen=True, slots=True)
class TaskInboxProjection:
    schema_version: Literal["sv-task-inbox/v1"]
    authority: Literal["postgresql"]
    ordering_policy_version: Literal["sv-task-inbox-order/v1"]
    items: tuple[TaskInboxItem, ...]
    truncated: bool


class TaskInbox:
    """Read-only projection of authoritative Task and active Run heads."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect(self) -> TaskInboxProjection:
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
        pending_approvals = (
            select(
                SvApprovalRequestRecord.task_id,
                SvApprovalRequestRecord.task_revision,
                SvApprovalRequestRecord.run_id,
                SvApprovalRequestRecord.run_revision,
                func.count(SvApprovalRequestRecord.id).label("pending_decision_count"),
                func.array_agg(SvApprovalRequestRecord.gate_kind).label("pending_gate_kinds"),
                func.bool_or(decision_for_request).label("decision_binding_drift"),
            )
            .where(~matching_decision)
            .group_by(
                SvApprovalRequestRecord.task_id,
                SvApprovalRequestRecord.task_revision,
                SvApprovalRequestRecord.run_id,
                SvApprovalRequestRecord.run_revision,
            )
            .subquery("pending_approvals")
        )
        pending_decision_count = func.coalesce(pending_approvals.c.pending_decision_count, 0)
        decision_binding_drift = func.coalesce(
            pending_approvals.c.decision_binding_drift,
            literal(False),
        )
        has_pending_decision = pending_decision_count > 0
        awaiting_approval = SvRunRecord.state == RunState.AWAITING_APPROVAL.value
        awaiting_decision = awaiting_approval & has_pending_decision
        approval_integrity_attention = or_(
            awaiting_approval & ~has_pending_decision,
            and_(
                SvRunRecord.state.is_not(None),
                ~awaiting_approval,
                has_pending_decision,
            ),
        )
        no_run = SvTaskRecord.active_run_id.is_(None)
        agent_active = SvRunRecord.state.in_(
            (
                RunState.PLANNING.value,
                RunState.RUNNABLE.value,
                RunState.RUNNING.value,
            )
        )
        not_started = no_run | (SvRunRecord.state == RunState.DRAFT.value)

        lane = case(
            (awaiting_decision, literal(TaskInboxLane.NEEDS_DECISION.value)),
            (
                approval_integrity_attention,
                literal(TaskInboxLane.TECHNICAL_ATTENTION.value),
            ),
            (
                SvRunRecord.state == RunState.AWAITING_INPUT.value,
                literal(TaskInboxLane.NEEDS_INPUT.value),
            ),
            (
                SvRunRecord.state == RunState.BLOCKED.value,
                literal(TaskInboxLane.BLOCKED.value),
            ),
            (
                SvRunRecord.state == RunState.FAILED.value,
                literal(TaskInboxLane.TECHNICAL_ATTENTION.value),
            ),
            (agent_active, literal(TaskInboxLane.AGENT_RUNNING.value)),
            (
                SvRunRecord.state == RunState.COMPLETED_WITH_LIMITS.value,
                literal(TaskInboxLane.COMPLETED_WITH_LIMITS.value),
            ),
            (
                SvRunRecord.state == RunState.STOPPED.value,
                literal(TaskInboxLane.STOPPED.value),
            ),
            (not_started, literal(TaskInboxLane.NOT_STARTED.value)),
            else_=literal(TaskInboxLane.TECHNICAL_ATTENTION.value),
        ).label("lane")
        ordering_reason = case(
            (
                awaiting_decision,
                literal(TaskInboxOrderingReason.HUMAN_DECISION_REQUIRED.value),
            ),
            (
                approval_integrity_attention,
                literal(TaskInboxOrderingReason.RUNTIME_INTEGRITY_ATTENTION.value),
            ),
            (
                SvRunRecord.state == RunState.AWAITING_INPUT.value,
                literal(TaskInboxOrderingReason.USER_INPUT_REQUIRED.value),
            ),
            (
                SvRunRecord.state == RunState.BLOCKED.value,
                literal(TaskInboxOrderingReason.BUSINESS_BLOCKER_PRESENT.value),
            ),
            (
                SvRunRecord.state == RunState.FAILED.value,
                literal(TaskInboxOrderingReason.TECHNICAL_FAILURE_REQUIRES_REVIEW.value),
            ),
            (
                agent_active,
                literal(TaskInboxOrderingReason.AGENT_WORK_IN_PROGRESS.value),
            ),
            (
                SvRunRecord.state == RunState.COMPLETED_WITH_LIMITS.value,
                literal(TaskInboxOrderingReason.COMPLETED_WITH_DECLARED_LIMITS.value),
            ),
            (
                SvRunRecord.state == RunState.STOPPED.value,
                literal(TaskInboxOrderingReason.STOPPED_BY_DECISION.value),
            ),
            (
                not_started,
                literal(TaskInboxOrderingReason.RUN_NOT_STARTED.value),
            ),
            else_=literal(TaskInboxOrderingReason.RUNTIME_INTEGRITY_ATTENTION.value),
        ).label("ordering_reason")
        lane_rank = case(
            (lane == TaskInboxLane.NEEDS_DECISION.value, 0),
            (lane == TaskInboxLane.NEEDS_INPUT.value, 1),
            (lane == TaskInboxLane.BLOCKED.value, 2),
            (lane == TaskInboxLane.TECHNICAL_ATTENTION.value, 3),
            (lane == TaskInboxLane.AGENT_RUNNING.value, 4),
            (lane == TaskInboxLane.COMPLETED_WITH_LIMITS.value, 5),
            (lane == TaskInboxLane.STOPPED.value, 6),
            else_=7,
        )
        priority_at = func.coalesce(SvRunRecord.updated_at, SvTaskRecord.updated_at).label(
            "priority_at"
        )

        rows = (
            await self._session.execute(
                select(
                    SvTaskRecord.id.label("task_id"),
                    SvTaskRecord.current_revision.label("task_revision"),
                    SvTaskRecord.active_run_id,
                    SvTaskRevisionRecord.goal_track,
                    SvTaskRevisionRecord.subject,
                    SvTaskRevisionRecord.decision_question,
                    SvTaskRevisionRecord.platform,
                    SvTaskRevisionRecord.market,
                    SvTaskRevisionRecord.language,
                    SvTaskRevisionRecord.performance_start,
                    SvTaskRevisionRecord.performance_end,
                    SvTaskRevisionRecord.performance_timezone,
                    SvTaskRevisionRecord.stop_condition,
                    SvTaskRevisionRecord.initial_rights_state,
                    SvTaskRevisionRecord.brief_digest,
                    SvRunRecord.revision.label("active_run_revision"),
                    SvRunRecord.task_revision.label("active_run_task_revision"),
                    SvRunRecord.state.label("run_state"),
                    pending_decision_count.label("pending_decision_count"),
                    pending_approvals.c.pending_gate_kinds,
                    decision_binding_drift.label("decision_binding_drift"),
                    lane,
                    ordering_reason,
                    priority_at,
                )
                .select_from(SvTaskRecord)
                .outerjoin(
                    SvTaskRevisionRecord,
                    (SvTaskRevisionRecord.task_id == SvTaskRecord.id)
                    & (SvTaskRevisionRecord.revision == SvTaskRecord.current_revision),
                )
                .outerjoin(
                    SvRunRecord,
                    (SvRunRecord.task_id == SvTaskRecord.id)
                    & (SvRunRecord.id == SvTaskRecord.active_run_id),
                )
                .outerjoin(
                    pending_approvals,
                    (pending_approvals.c.task_id == SvTaskRecord.id)
                    & (pending_approvals.c.task_revision == SvTaskRecord.current_revision)
                    & (pending_approvals.c.run_id == SvRunRecord.id)
                    & (pending_approvals.c.run_revision == SvRunRecord.revision),
                )
                .order_by(
                    lane_rank,
                    priority_at.desc(),
                    SvTaskRecord.id,
                )
                .limit(_MAX_INBOX_TASKS + 1)
            )
        ).all()
        truncated = len(rows) > _MAX_INBOX_TASKS
        rows = rows[:_MAX_INBOX_TASKS]
        if any(row.decision_binding_drift for row in rows):
            raise JournalIntegrityError("task_inbox_approval_decision_binding_mismatch")
        if any(
            row.goal_track is None
            or row.subject is None
            or row.decision_question is None
            or (row.active_run_id is not None and row.active_run_revision is None)
            or (row.active_run_id is not None and row.active_run_task_revision != row.task_revision)
            for row in rows
        ):
            raise JournalIntegrityError("task_inbox_current_head_invalid")
        for row in rows:
            try:
                brief = TaskBrief.create(
                    goal_track=GoalTrack(row.goal_track),
                    decision_question=row.decision_question,
                    subject=row.subject,
                    platform=TargetPlatform(row.platform),
                    market=row.market,
                    language=row.language,
                    performance_window=PerformanceWindow(
                        start=row.performance_start,
                        end=row.performance_end,
                        timezone=row.performance_timezone,
                    ),
                    stop_condition=row.stop_condition,
                    initial_rights_state=RightsState(row.initial_rights_state),
                )
            except (TypeError, ValueError) as exc:
                raise JournalIntegrityError("task_inbox_current_head_invalid") from exc
            if canonical_digest(brief) != row.brief_digest:
                raise JournalIntegrityError("task_inbox_brief_digest_mismatch")

        return TaskInboxProjection(
            schema_version="sv-task-inbox/v1",
            authority="postgresql",
            ordering_policy_version="sv-task-inbox-order/v1",
            items=tuple(
                TaskInboxItem(
                    task_id=row.task_id,
                    task_revision=row.task_revision,
                    goal_track=GoalTrack(row.goal_track),
                    subject=row.subject,
                    decision_question=row.decision_question,
                    active_run_id=row.active_run_id,
                    active_run_revision=row.active_run_revision,
                    run_state=RunState(row.run_state) if row.run_state is not None else None,
                    pending_decision_count=row.pending_decision_count,
                    pending_gate_kinds=tuple(
                        sorted(
                            {
                                ApprovalGateKind(gate_kind)
                                for gate_kind in (row.pending_gate_kinds or ())
                            },
                            key=lambda item: item.value,
                        )
                    ),
                    lane=TaskInboxLane(row.lane),
                    ordering_reason=TaskInboxOrderingReason(row.ordering_reason),
                    priority_at=row.priority_at,
                )
                for row in rows
            ),
            truncated=truncated,
        )
