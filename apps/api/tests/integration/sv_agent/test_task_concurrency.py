import asyncio
import os
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.sv_agent_repository import SvAgentRepository, TaskWriteResult
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import TaskRevisionConflict
from app.domain.sv_agent.runtime_records import ActorKind, ActorStamp, ReplayQuery

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
        ),
        id=uuid4(),
        created_at=datetime.now(UTC),
    )


async def test_concurrent_same_command_converges_on_one_receipt() -> None:
    engine = create_async_engine(_database_url())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    task = _task()

    async def create_once() -> TaskWriteResult:
        async with sessions() as session:
            result = await SvAgentRepository(session).create_task(
                task,
                idempotency_key=f"create-{task.id}",
                initiated_by=HUMAN,
                executed_by=AGENT,
            )
            await session.commit()
            return result

    try:
        first, second = await asyncio.gather(create_once(), create_once())
        assert sorted((first.replayed, second.replayed)) == [False, True]
        assert first.task == second.task == task
        assert first.event_sequence == second.event_sequence
    finally:
        await engine.dispose()


async def test_concurrent_task_revisions_allow_exactly_one_compare_and_swap() -> None:
    engine = create_async_engine(_database_url())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    original = _task()
    async with sessions() as setup_session:
        await SvAgentRepository(setup_session).create_task(
            original,
            idempotency_key=f"create-{original.id}",
            initiated_by=HUMAN,
            executed_by=AGENT,
        )
        await setup_session.commit()

    first_revision = original.revise(
        replace(original.brief, subject="First competing subject"),
        updated_at=original.updated_at + timedelta(seconds=1),
    )
    second_revision = original.revise(
        replace(original.brief, subject="Second competing subject"),
        updated_at=original.updated_at + timedelta(seconds=2),
    )

    async def revise_once(task: Task, key: str) -> TaskWriteResult | TaskRevisionConflict:
        async with sessions() as session:
            try:
                result = await SvAgentRepository(session).revise_task(
                    task,
                    expected_revision=1,
                    idempotency_key=key,
                    initiated_by=HUMAN,
                    executed_by=AGENT,
                )
                await session.commit()
                return result
            except TaskRevisionConflict as exc:
                await session.rollback()
                return exc

    try:
        outcomes = await asyncio.gather(
            revise_once(first_revision, f"first-{original.id}"),
            revise_once(second_revision, f"second-{original.id}"),
        )
        successes = [item for item in outcomes if isinstance(item, TaskWriteResult)]
        conflicts = [item for item in outcomes if isinstance(item, TaskRevisionConflict)]
        assert len(successes) == 1
        assert len(conflicts) == 1
        assert conflicts[0].code == "TASK_REVISION_CONFLICT"

        async with sessions() as read_session:
            repository = SvAgentRepository(read_session)
            current = await repository.get_task(original.id)
            replay = await repository.read_replay(ReplayQuery(task_id=original.id))
        assert current is not None
        assert current.revision == 2
        assert current.brief.subject in {
            first_revision.brief.subject,
            second_revision.brief.subject,
        }
        assert len(replay.entries) == 2
    finally:
        await engine.dispose()
