import os
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.sv_agent_models import SvTaskEventRecord
from app.adapters.db.sv_agent_repository import SvAgentRepository
from app.application.sv_agent.approval_replay import ApprovalReplayWorkspace
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import JournalIntegrityError
from app.domain.sv_agent.runtime_records import ActorKind, ActorStamp, TaskEventType

HUMAN = ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer")
AGENT = ActorStamp(kind=ActorKind.AGENT, ref="sv-agent")


def _database_url() -> str:
    value = os.getenv("SV_CONCURRENCY_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("SV_CONCURRENCY_TEST_DATABASE_URL is required for committed concurrency tests")
    return value


def _task() -> Task:
    return Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which replay boundary is internally consistent?",
            subject="Momcozy approval replay concurrency",
            platform=TargetPlatform.TIKTOK,
            market="US",
            language="en-US",
            performance_window=PerformanceWindow(
                start=date(2026, 10, 1),
                end=date(2026, 10, 21),
                timezone="America/Los_Angeles",
            ),
            stop_condition="Stop before any write or publication.",
            initial_rights_state=RightsState.ANALYSIS_ONLY,
        ),
        id=uuid4(),
        created_at=datetime.now(UTC),
    )


def _task_event(task: Task, marker: str) -> SvTaskEventRecord:
    payload = {"marker": marker}
    return SvTaskEventRecord(
        id=uuid4(),
        event_type=TaskEventType.TASK_REVISED.value,
        task_id=task.id,
        run_id=None,
        task_revision=1,
        run_revision=None,
        payload=payload,
        payload_digest=canonical_digest(payload),
        initiated_by_kind=AGENT.kind.value,
        initiated_by_ref=AGENT.ref,
        executed_by_kind=AGENT.kind.value,
        executed_by_ref=AGENT.ref,
        causation_receipt_id=None,
    )


async def test_workspace_detects_a_lower_sequence_committed_after_its_highwater(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine(_database_url())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    task = _task()
    lower_session = sessions()
    higher_session = sessions()
    reader_session = sessions()
    try:
        async with sessions() as setup_session:
            await SvAgentRepository(setup_session).create_task(
                task,
                idempotency_key=f"approval-replay-concurrency-{task.id}",
                initiated_by=HUMAN,
                executed_by=AGENT,
            )
            await setup_session.commit()

        lower_event = _task_event(task, "lower-sequence-late-commit")
        lower_session.add(lower_event)
        await lower_session.flush()

        higher_event = _task_event(task, "higher-sequence-first-commit")
        higher_session.add(higher_event)
        await higher_session.commit()
        assert lower_event.event_sequence < higher_event.event_sequence

        workspace = ApprovalReplayWorkspace(reader_session)
        original = workspace._assert_approval_journal_complete

        async def commit_lower_after_timeline(
            task_id: UUID,
            through_sequence: int,
        ) -> None:
            await lower_session.commit()
            await original(task_id, through_sequence)

        monkeypatch.setattr(
            workspace,
            "_assert_approval_journal_complete",
            commit_lower_after_timeline,
        )

        with pytest.raises(JournalIntegrityError, match="approval_replay_snapshot_changed"):
            await workspace.inspect(task.id)
    finally:
        await lower_session.rollback()
        await higher_session.rollback()
        await reader_session.rollback()
        await lower_session.close()
        await higher_session.close()
        await reader_session.close()
        await engine.dispose()
