from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvDecisionEventRecord,
    SvRunRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
)
from app.application.sv_agent_task_inbox import (
    TaskInbox,
    TaskInboxLane,
    TaskInboxOrderingReason,
)
from app.domain.common.canonical import canonical_digest
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
from app.domain.sv_agent.errors import JournalIntegrityError


def _task(*, task_id: str, subject: str, created_at: datetime) -> Task:
    return Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question=f"What should {subject} test next?",
            subject=subject,
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
        id=UUID(task_id),
        created_at=created_at,
    )


def _task_revision_record(
    task: Task,
    *,
    revision: int | None = None,
    brief_digest: str | None = None,
) -> SvTaskRevisionRecord:
    return SvTaskRevisionRecord(
        task_id=task.id,
        revision=revision or task.revision,
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
        brief_digest=brief_digest or canonical_digest(task.brief),
        created_at=task.created_at,
    )


async def _persist_task(
    session: AsyncSession,
    task: Task,
    *,
    run_id: UUID | None = None,
    run_state: RunState | None = None,
    run_updated_at: datetime | None = None,
    brief_digest: str | None = None,
) -> None:
    session.add(
        SvTaskRecord(
            id=task.id,
            current_revision=task.revision,
            active_run_id=run_id,
            summary={"subject": task.brief.subject},
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    session.add(_task_revision_record(task, brief_digest=brief_digest))
    await session.flush()
    if run_id is not None and run_state is not None:
        session.add(
            SvRunRecord(
                id=run_id,
                task_id=task.id,
                task_revision=task.revision,
                revision=1,
                state=run_state.value,
                primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR.value,
                creative_dimension=CreativeDimension.HOOK_TRIGGER.value,
                created_at=task.created_at,
                updated_at=run_updated_at or task.updated_at,
            )
        )
        await session.flush()


async def test_inbox_fails_closed_on_current_brief_digest_drift(
    db_session: AsyncSession,
) -> None:
    task = _task(
        task_id="21000000-0000-0000-0000-000000000090",
        subject="Momcozy corrupt brief",
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )
    await _persist_task(db_session, task, brief_digest="f" * 64)

    with pytest.raises(JournalIntegrityError, match="task_inbox_brief_digest_mismatch"):
        await TaskInbox(db_session).inspect()


async def test_inbox_fails_closed_when_active_run_belongs_to_an_old_task_revision(
    db_session: AsyncSession,
) -> None:
    task = _task(
        task_id="21000000-0000-0000-0000-000000000091",
        subject="Momcozy stale active run",
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )
    run_id = UUID("22000000-0000-0000-0000-000000000091")
    db_session.add(
        SvTaskRecord(
            id=task.id,
            current_revision=2,
            active_run_id=run_id,
            summary={"subject": task.brief.subject},
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    db_session.add_all(
        [
            _task_revision_record(task, revision=1),
            _task_revision_record(task, revision=2),
        ]
    )
    await db_session.flush()
    db_session.add(
        SvRunRecord(
            id=run_id,
            task_id=task.id,
            task_revision=1,
            revision=1,
            state=RunState.RUNNING.value,
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR.value,
            creative_dimension=CreativeDimension.HOOK_TRIGGER.value,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    await db_session.flush()

    with pytest.raises(JournalIntegrityError, match="task_inbox_current_head_invalid"):
        await TaskInbox(db_session).inspect()


async def test_inbox_prioritizes_running_persisted_tasks_and_explains_order(
    db_session: AsyncSession,
) -> None:
    not_started = _task(
        task_id="21000000-0000-0000-0000-000000000001",
        subject="Momcozy newborn routine",
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )
    running = _task(
        task_id="21000000-0000-0000-0000-000000000002",
        subject="Momcozy baby reaction story",
        created_at=datetime(2026, 10, 21, 7, 0, tzinfo=UTC),
    )
    await _persist_task(db_session, not_started)
    await _persist_task(
        db_session,
        running,
        run_id=UUID("22000000-0000-0000-0000-000000000002"),
        run_state=RunState.RUNNING,
        run_updated_at=datetime(2026, 10, 21, 9, 0, tzinfo=UTC),
    )

    projection = await TaskInbox(db_session).inspect()

    assert projection.schema_version == "sv-task-inbox/v1"
    assert projection.authority == "postgresql"
    assert projection.truncated is False
    assert [item.task_id for item in projection.items] == [running.id, not_started.id]
    assert projection.items[0].lane is TaskInboxLane.AGENT_RUNNING
    assert projection.items[0].ordering_reason is TaskInboxOrderingReason.AGENT_WORK_IN_PROGRESS
    assert projection.items[1].lane is TaskInboxLane.NOT_STARTED
    assert projection.items[1].ordering_reason is TaskInboxOrderingReason.RUN_NOT_STARTED


async def test_inbox_requires_a_current_undecided_request_for_the_decision_lane(
    db_session: AsyncSession,
) -> None:
    waiting = _task(
        task_id="21000000-0000-0000-0000-000000000011",
        subject="Momcozy contract review",
        created_at=datetime(2026, 10, 21, 10, 0, tzinfo=UTC),
    )
    inconsistent = _task(
        task_id="21000000-0000-0000-0000-000000000012",
        subject="Momcozy missing approval record",
        created_at=datetime(2026, 10, 21, 11, 0, tzinfo=UTC),
    )
    waiting_run_id = UUID("22000000-0000-0000-0000-000000000011")
    inconsistent_run_id = UUID("22000000-0000-0000-0000-000000000012")
    await _persist_task(
        db_session,
        waiting,
        run_id=waiting_run_id,
        run_state=RunState.AWAITING_APPROVAL,
    )
    await _persist_task(
        db_session,
        inconsistent,
        run_id=inconsistent_run_id,
        run_state=RunState.AWAITING_APPROVAL,
    )
    db_session.add(
        SvApprovalRequestRecord(
            id=UUID("23000000-0000-0000-0000-000000000011"),
            request_version=1,
            request_digest="a" * 64,
            task_id=waiting.id,
            task_revision=waiting.revision,
            run_id=waiting_run_id,
            run_revision=1,
            gate_kind="replication_contract",
            artifact_type="replication_contract",
            artifact_id="contract-001",
            artifact_version=1,
            artifact_digest="b" * 64,
            precondition_digest="c" * 64,
            predicted_effects=[],
            explicit_non_effects=[],
            evidence_summary={},
            limitations=[],
            stale_if=[],
            created_at=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
        )
    )
    await db_session.flush()

    projection = await TaskInbox(db_session).inspect()

    assert [item.task_id for item in projection.items] == [waiting.id, inconsistent.id]
    assert projection.items[0].lane is TaskInboxLane.NEEDS_DECISION
    assert projection.items[0].ordering_reason is TaskInboxOrderingReason.HUMAN_DECISION_REQUIRED
    assert projection.items[0].pending_decision_count == 1
    assert [item.value for item in projection.items[0].pending_gate_kinds] == [
        "replication_contract"
    ]
    assert projection.items[1].lane is TaskInboxLane.TECHNICAL_ATTENTION
    assert (
        projection.items[1].ordering_reason is TaskInboxOrderingReason.RUNTIME_INTEGRITY_ATTENTION
    )

    decision_payload = {
        "approval_request_id": "23000000-0000-0000-0000-000000000011",
        "decision": "approve",
    }
    db_session.add(
        SvDecisionEventRecord(
            id=UUID("24000000-0000-0000-0000-000000000011"),
            event_type="human_decision.recorded.v1",
            approval_request_id=UUID("23000000-0000-0000-0000-000000000011"),
            approval_request_version=1,
            request_digest="a" * 64,
            task_id=waiting.id,
            task_revision=waiting.revision,
            run_id=waiting_run_id,
            run_revision=1,
            decision="approve",
            rationale="Local review only.",
            payload=decision_payload,
            payload_digest=canonical_digest(decision_payload),
            decided_by_kind="human",
            decided_by_ref="local-reviewer",
            created_at=datetime(2026, 10, 21, 13, 0, tzinfo=UTC),
        )
    )
    await db_session.flush()

    decided_projection = await TaskInbox(db_session).inspect()
    decided_item = next(item for item in decided_projection.items if item.task_id == waiting.id)
    assert decided_item.pending_decision_count == 0
    assert decided_item.pending_gate_kinds == ()
    assert decided_item.lane is TaskInboxLane.TECHNICAL_ATTENTION
    assert decided_item.ordering_reason is TaskInboxOrderingReason.RUNTIME_INTEGRITY_ATTENTION


async def test_inbox_fails_closed_on_approval_decision_binding_drift(
    db_session: AsyncSession,
) -> None:
    task = _task(
        task_id="21000000-0000-0000-0000-000000000092",
        subject="Momcozy approval binding drift",
        created_at=datetime(2026, 10, 21, 10, 0, tzinfo=UTC),
    )
    run_id = UUID("22000000-0000-0000-0000-000000000092")
    approval_id = UUID("23000000-0000-0000-0000-000000000092")
    await _persist_task(
        db_session,
        task,
        run_id=run_id,
        run_state=RunState.AWAITING_APPROVAL,
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
            artifact_id="contract-092",
            artifact_version=1,
            artifact_digest="b" * 64,
            precondition_digest="c" * 64,
            predicted_effects=[],
            explicit_non_effects=[],
            evidence_summary={},
            limitations=[],
            stale_if=[],
            created_at=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
        )
    )
    decision_payload = {
        "approval_request_id": str(approval_id),
        "decision": "approve",
    }
    db_session.add(
        SvDecisionEventRecord(
            id=UUID("24000000-0000-0000-0000-000000000092"),
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
            created_at=datetime(2026, 10, 21, 13, 0, tzinfo=UTC),
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="task_inbox_approval_decision_binding_mismatch",
    ):
        await TaskInbox(db_session).inspect()


async def test_inbox_fails_closed_when_a_non_approval_run_has_a_pending_request(
    db_session: AsyncSession,
) -> None:
    task_ids: list[UUID] = []
    for offset, run_state in enumerate(
        (RunState.RUNNING, RunState.AWAITING_INPUT, RunState.BLOCKED),
        start=13,
    ):
        task = _task(
            task_id=f"21000000-0000-0000-0000-{offset:012d}",
            subject=f"Momcozy approval state drift {run_state.value}",
            created_at=datetime(2026, 10, 21, 10, 0, tzinfo=UTC),
        )
        run_id = UUID(f"22000000-0000-0000-0000-{offset:012d}")
        await _persist_task(
            db_session,
            task,
            run_id=run_id,
            run_state=run_state,
        )
        db_session.add(
            SvApprovalRequestRecord(
                id=UUID(f"23000000-0000-0000-0000-{offset:012d}"),
                request_version=1,
                request_digest="a" * 64,
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=1,
                gate_kind="replication_contract",
                artifact_type="replication_contract",
                artifact_id=f"contract-{offset:03d}",
                artifact_version=1,
                artifact_digest="b" * 64,
                precondition_digest="c" * 64,
                predicted_effects=[],
                explicit_non_effects=[],
                evidence_summary={},
                limitations=[],
                stale_if=[],
                created_at=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
            )
        )
        task_ids.append(task.id)
    await db_session.flush()

    projection = await TaskInbox(db_session).inspect()

    projected = {item.task_id: item for item in projection.items}
    for task_id in task_ids:
        assert projected[task_id].lane is TaskInboxLane.TECHNICAL_ATTENTION
        assert (
            projected[task_id].ordering_reason
            is TaskInboxOrderingReason.RUNTIME_INTEGRITY_ATTENTION
        )
        assert projected[task_id].pending_decision_count == 1


async def test_inbox_returns_a_stable_bounded_projection(
    db_session: AsyncSession,
) -> None:
    created_at = datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    for offset in range(101):
        task = _task(
            task_id=f"21000000-0000-0000-0000-{offset:012d}",
            subject=f"Momcozy bounded task {offset}",
            created_at=created_at,
        )
        await _persist_task(db_session, task)

    projection = await TaskInbox(db_session).inspect()

    assert projection.truncated is True
    assert len(projection.items) == 100
    assert projection.items[0].task_id == UUID("21000000-0000-0000-0000-000000000000")
    assert projection.items[-1].task_id == UUID("21000000-0000-0000-0000-000000000099")


async def test_inbox_keeps_business_and_technical_run_states_distinct(
    db_session: AsyncSession,
) -> None:
    cases = (
        (
            "21",
            RunState.AWAITING_INPUT,
            TaskInboxLane.NEEDS_INPUT,
            TaskInboxOrderingReason.USER_INPUT_REQUIRED,
        ),
        (
            "22",
            RunState.BLOCKED,
            TaskInboxLane.BLOCKED,
            TaskInboxOrderingReason.BUSINESS_BLOCKER_PRESENT,
        ),
        (
            "23",
            RunState.FAILED,
            TaskInboxLane.TECHNICAL_ATTENTION,
            TaskInboxOrderingReason.TECHNICAL_FAILURE_REQUIRES_REVIEW,
        ),
        (
            "24",
            RunState.COMPLETED_WITH_LIMITS,
            TaskInboxLane.COMPLETED_WITH_LIMITS,
            TaskInboxOrderingReason.COMPLETED_WITH_DECLARED_LIMITS,
        ),
        (
            "25",
            RunState.STOPPED,
            TaskInboxLane.STOPPED,
            TaskInboxOrderingReason.STOPPED_BY_DECISION,
        ),
    )
    expected: dict[UUID, tuple[TaskInboxLane, TaskInboxOrderingReason]] = {}
    for suffix, run_state, lane, reason in cases:
        task = _task(
            task_id=f"21000000-0000-0000-0000-0000000000{suffix}",
            subject=f"Momcozy state {run_state.value}",
            created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
        )
        await _persist_task(
            db_session,
            task,
            run_id=UUID(f"22000000-0000-0000-0000-0000000000{suffix}"),
            run_state=run_state,
        )
        expected[task.id] = (lane, reason)

    projection = await TaskInbox(db_session).inspect()

    assert [item.lane for item in projection.items] == [
        TaskInboxLane.NEEDS_INPUT,
        TaskInboxLane.BLOCKED,
        TaskInboxLane.TECHNICAL_ATTENTION,
        TaskInboxLane.COMPLETED_WITH_LIMITS,
        TaskInboxLane.STOPPED,
    ]
    for item in projection.items:
        assert (item.lane, item.ordering_reason) == expected[item.task_id]
