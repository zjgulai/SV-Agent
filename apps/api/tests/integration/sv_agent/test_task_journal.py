from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvCommandReceiptRecord,
    SvTaskEventRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
)
from app.adapters.db.sv_agent_repository import SvAgentRepository
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import IdempotencyConflict, TaskNotFound, TaskRevisionConflict
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ActorStamp,
    ReplayQuery,
    TaskEventType,
)

TASK_ID = UUID("10000000-0000-0000-0000-000000000001")
HUMAN = ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer")
AGENT = ActorStamp(kind=ActorKind.AGENT, ref="sv-agent")


def _task() -> Task:
    brief = TaskBrief.create(
        goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
        decision_question="Which baby reaction story should Momcozy test?",
        subject="Momcozy baby-care brand voice",
        platform=TargetPlatform.TIKTOK,
        market="US",
        language="en-US",
        performance_window=PerformanceWindow(
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
            timezone="America/Los_Angeles",
        ),
        stop_condition="Stop before any provider write or publication.",
        initial_rights_state=RightsState.ANALYSIS_ONLY,
    )
    return Task.new(
        brief,
        id=TASK_ID,
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )


async def test_create_task_persists_head_revision_event_and_receipt_atomically(
    db_session: AsyncSession,
) -> None:
    repository = SvAgentRepository(db_session)
    task = _task()

    result = await repository.create_task(
        task,
        idempotency_key="create-brand-voice-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )

    assert result.task == task
    assert result.replayed is False
    assert result.event_sequence >= 1
    assert await repository.get_task(TASK_ID) == task

    replay = await repository.read_replay(ReplayQuery(task_id=TASK_ID))
    assert replay.snapshot_through_sequence == result.event_sequence
    assert replay.next_after_sequence is None
    assert len(replay.entries) == 1
    assert replay.entries[0].event_type is TaskEventType.TASK_CREATED
    assert dict(replay.entries[0].payload) == {
        "brief_digest": canonical_digest(task.brief),
        "task_revision_ref": f"{TASK_ID}:1",
        "to_revision": 1,
    }

    for record_type in (
        SvTaskRecord,
        SvTaskRevisionRecord,
        SvTaskEventRecord,
        SvCommandReceiptRecord,
    ):
        count = await db_session.scalar(select(func.count()).select_from(record_type))
        assert count == 1


async def test_create_task_replays_the_same_receipt_without_duplicate_writes(
    db_session: AsyncSession,
) -> None:
    repository = SvAgentRepository(db_session)
    task = _task()

    first = await repository.create_task(
        task,
        idempotency_key="create-brand-voice-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )
    replayed = await repository.create_task(
        task,
        idempotency_key="create-brand-voice-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )

    assert replayed == replace(first, replayed=True)
    for record_type in (
        SvTaskRecord,
        SvTaskRevisionRecord,
        SvTaskEventRecord,
        SvCommandReceiptRecord,
    ):
        count = await db_session.scalar(select(func.count()).select_from(record_type))
        assert count == 1


async def test_create_task_rejects_same_key_with_a_different_input_digest(
    db_session: AsyncSession,
) -> None:
    repository = SvAgentRepository(db_session)
    task = _task()
    await repository.create_task(
        task,
        idempotency_key="create-brand-voice-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )
    conflicting = Task.new(
        replace(task.brief, subject="A different subject"),
        id=task.id,
        created_at=task.created_at,
    )

    with pytest.raises(IdempotencyConflict) as exc_info:
        await repository.create_task(
            conflicting,
            idempotency_key="create-brand-voice-task",
            initiated_by=HUMAN,
            executed_by=AGENT,
        )

    assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"


async def test_revise_task_uses_compare_and_swap_and_appends_history(
    db_session: AsyncSession,
) -> None:
    repository = SvAgentRepository(db_session)
    original = _task()
    await repository.create_task(
        original,
        idempotency_key="create-brand-voice-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )
    revised = original.revise(
        replace(original.brief, decision_question="Which reaction format should we test first?"),
        updated_at=datetime(2026, 10, 21, 8, 5, tzinfo=UTC),
    )

    result = await repository.revise_task(
        revised,
        expected_revision=1,
        idempotency_key="revise-decision-question",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )

    assert result.task == revised
    assert result.replayed is False
    assert await repository.get_task(TASK_ID) == revised
    replay = await repository.read_replay(ReplayQuery(task_id=TASK_ID))
    assert [entry.event_type for entry in replay.entries] == [
        TaskEventType.TASK_CREATED,
        TaskEventType.TASK_REVISED,
    ]
    assert [entry.task_revision for entry in replay.entries] == [1, 2]
    assert await db_session.scalar(select(func.count()).select_from(SvTaskRevisionRecord)) == 2

    replayed = await repository.revise_task(
        revised,
        expected_revision=1,
        idempotency_key="revise-decision-question",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )
    assert replayed == replace(result, replayed=True)
    assert await db_session.scalar(select(func.count()).select_from(SvTaskRevisionRecord)) == 2

    stale_revision = original.revise(
        replace(original.brief, subject="A stale competing edit"),
        updated_at=datetime(2026, 10, 21, 8, 6, tzinfo=UTC),
    )
    with pytest.raises(TaskRevisionConflict) as exc_info:
        await repository.revise_task(
            stale_revision,
            expected_revision=1,
            idempotency_key="stale-edit",
            initiated_by=HUMAN,
            executed_by=AGENT,
        )

    assert exc_info.value.code == "TASK_REVISION_CONFLICT"


async def test_revise_task_distinguishes_missing_task_from_stale_revision(
    db_session: AsyncSession,
) -> None:
    repository = SvAgentRepository(db_session)
    original = _task()
    missing = original.revise(
        replace(original.brief, subject="Missing task"),
        updated_at=datetime(2026, 10, 21, 8, 7, tzinfo=UTC),
    )

    with pytest.raises(TaskNotFound) as exc_info:
        await repository.revise_task(
            missing,
            expected_revision=1,
            idempotency_key="missing-task-edit",
            initiated_by=HUMAN,
            executed_by=AGENT,
        )

    assert exc_info.value.code == "TASK_NOT_FOUND"
