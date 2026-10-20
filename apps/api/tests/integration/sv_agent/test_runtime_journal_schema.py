from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvDecisionEventRecord,
    SvRunRecord,
    SvTaskEventRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvToolRunEventRecord,
    SvToolRunRecord,
)
from app.adapters.db.sv_agent_repository import SvAgentRepository
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    RunState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import EventDigestMismatch, JournalIntegrityError
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ActorStamp,
    DecisionEventType,
    EventStream,
    ReplayQuery,
    TaskEventType,
    ToolRunEventType,
)

TASK_ID = UUID("20000000-0000-0000-0000-000000000001")
RUN_ID = UUID("20000000-0000-0000-0000-000000000002")
TOOL_RUN_ID = UUID("20000000-0000-0000-0000-000000000003")
APPROVAL_ID = UUID("20000000-0000-0000-0000-000000000004")
HUMAN = ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer")
AGENT = ActorStamp(kind=ActorKind.AGENT, ref="sv-agent")

EXPECTED_TABLES = {
    "sv_approval_requests",
    "sv_artifacts",
    "sv_command_receipts",
    "sv_decision_events",
    "sv_run_plans",
    "sv_runs",
    "sv_runtime_lineage_links",
    "sv_task_events",
    "sv_task_revisions",
    "sv_tasks",
    "sv_tool_job_links",
    "sv_tool_run_events",
    "sv_tool_runs",
}

IMMUTABLE_TABLES = EXPECTED_TABLES - {"sv_tasks", "sv_runs", "sv_tool_runs"}


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
        id=TASK_ID,
        created_at=datetime(2026, 10, 21, 9, 0, tzinfo=UTC),
    )


async def _create_task(db_session: AsyncSession) -> tuple[SvAgentRepository, Task]:
    repository = SvAgentRepository(db_session)
    task = _task()
    await repository.create_task(
        task,
        idempotency_key="create-runtime-schema-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )
    return repository, task


async def test_schema_has_the_bounded_runtime_tables_and_database_guards(
    db_session: AsyncSession,
) -> None:
    table_names = set(
        (
            await db_session.scalars(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = current_schema() AND tablename LIKE 'sv_%'"
                )
            )
        ).all()
    )
    trigger_rows = (
        await db_session.execute(
            text(
                "SELECT c.relname AS table_name, t.tgname AS trigger_name "
                "FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = current_schema() AND NOT t.tgisinternal "
                "AND c.relname LIKE 'sv_%'"
            )
        )
    ).all()
    triggers = {(row.table_name, row.trigger_name) for row in trigger_rows}

    assert table_names == EXPECTED_TABLES
    assert {
        (table_name, f"trg_{table_name}_immutable") for table_name in IMMUTABLE_TABLES
    } <= triggers
    assert {
        ("sv_tasks", "trg_sv_tasks_guard"),
        ("sv_runs", "trg_sv_runs_guard"),
        ("sv_tool_runs", "trg_sv_tool_runs_guard"),
    } <= triggers


async def test_database_rejects_history_mutation_and_head_deletion(
    db_session: AsyncSession,
) -> None:
    _, task = await _create_task(db_session)

    history_savepoint = await db_session.begin_nested()
    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(
            update(SvTaskRevisionRecord)
            .where(
                SvTaskRevisionRecord.task_id == task.id,
                SvTaskRevisionRecord.revision == 1,
            )
            .values(subject="tampered")
        )
    await history_savepoint.rollback()

    head_savepoint = await db_session.begin_nested()
    with pytest.raises(DBAPIError, match="cannot be deleted"):
        await db_session.execute(delete(SvTaskRecord).where(SvTaskRecord.id == task.id))
    await head_savepoint.rollback()

    stored = await db_session.scalar(
        select(SvTaskRevisionRecord.subject).where(
            SvTaskRevisionRecord.task_id == task.id,
            SvTaskRevisionRecord.revision == 1,
        )
    )
    assert stored == task.brief.subject


async def test_replay_merges_all_event_streams_and_keeps_a_stable_snapshot(
    db_session: AsyncSession,
) -> None:
    repository, task = await _create_task(db_session)
    run = SvRunRecord(
        id=RUN_ID,
        task_id=task.id,
        task_revision=1,
        revision=1,
        state=RunState.DRAFT.value,
        primary_mechanism=None,
        creative_dimension=None,
        created_at=task.created_at,
        updated_at=task.created_at,
    )
    db_session.add(run)
    await db_session.flush()

    request_digest = "a" * 64
    db_session.add(
        SvApprovalRequestRecord(
            id=APPROVAL_ID,
            request_version=1,
            request_digest=request_digest,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=1,
            gate_kind="replication_contract",
            artifact_type="replication_contract",
            artifact_id="contract-1",
            artifact_version=1,
            artifact_digest="b" * 64,
            precondition_digest="c" * 64,
            predicted_effects=[{"effect": "allow_next_read_only_stage"}],
            explicit_non_effects=[{"effect": "publish"}],
            evidence_summary={"status": "bounded"},
            limitations=[{"code": "local_review_only"}],
            stale_if=[{"field": "artifact_digest"}],
        )
    )
    await db_session.flush()

    db_session.add(
        SvToolRunRecord(
            id=TOOL_RUN_ID,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=1,
            revision=1,
            tool_name="inspect_product_truth",
            tool_version="1",
            intent_summary="Read already-authoritative product facts.",
            input_digest="d" * 64,
            effect_class="read",
            approval_request_id=None,
            approval_request_version=None,
            idempotency_key=None,
            attempt_token=1,
            status="pending",
            artifact_refs=[],
            stable_error_code=None,
            recovery_action=None,
            started_at=None,
            finished_at=None,
        )
    )
    await db_session.flush()

    tool_payload = {"status": "pending", "tool_run_id": str(TOOL_RUN_ID)}
    tool_event = SvToolRunEventRecord(
        id=UUID("20000000-0000-0000-0000-000000000005"),
        event_type=ToolRunEventType.CREATED.value,
        tool_run_id=TOOL_RUN_ID,
        task_id=task.id,
        task_revision=1,
        run_id=run.id,
        run_revision=1,
        attempt_token=1,
        payload=tool_payload,
        payload_digest=canonical_digest(tool_payload),
        initiated_by_kind=AGENT.kind.value,
        initiated_by_ref=AGENT.ref,
        executed_by_kind=AGENT.kind.value,
        executed_by_ref=AGENT.ref,
    )
    db_session.add(tool_event)
    await db_session.flush()

    decision_payload = {
        "approval_request_id": str(APPROVAL_ID),
        "decision": "approve",
    }
    decision_event = SvDecisionEventRecord(
        id=UUID("20000000-0000-0000-0000-000000000006"),
        event_type=DecisionEventType.HUMAN_DECISION_RECORDED.value,
        approval_request_id=APPROVAL_ID,
        approval_request_version=1,
        request_digest=request_digest,
        task_id=task.id,
        task_revision=1,
        run_id=run.id,
        run_revision=1,
        decision="approve",
        rationale="Local review only.",
        payload=decision_payload,
        payload_digest=canonical_digest(decision_payload),
        decided_by_kind=HUMAN.kind.value,
        decided_by_ref=HUMAN.ref,
    )
    db_session.add(decision_event)
    await db_session.flush()

    first_page = await repository.read_replay(ReplayQuery(task_id=task.id, limit=2))
    assert [entry.stream for entry in first_page.entries] == [
        EventStream.TASK,
        EventStream.TOOL_RUN,
    ]
    assert first_page.next_after_sequence == tool_event.event_sequence
    assert first_page.snapshot_through_sequence == decision_event.event_sequence

    revised = task.revise(
        replace(task.brief, subject="Momcozy parent-and-baby brand voice"),
        updated_at=datetime(2026, 10, 21, 9, 5, tzinfo=UTC),
    )
    await repository.revise_task(
        revised,
        expected_revision=1,
        idempotency_key="revise-after-replay-snapshot",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )

    second_page = await repository.read_replay(
        ReplayQuery(
            task_id=task.id,
            after_sequence=first_page.next_after_sequence,
            through_sequence=first_page.snapshot_through_sequence,
            limit=2,
        )
    )
    assert [entry.stream for entry in second_page.entries] == [EventStream.DECISION]
    assert second_page.next_after_sequence is None
    fresh = await repository.read_replay(ReplayQuery(task_id=task.id))
    assert [entry.event_type for entry in fresh.entries] == [
        TaskEventType.TASK_CREATED,
        ToolRunEventType.CREATED,
        DecisionEventType.HUMAN_DECISION_RECORDED,
        TaskEventType.TASK_REVISED,
    ]


@pytest.mark.parametrize(
    ("payload", "payload_digest", "error_type", "error_code"),
    (
        (
            {"chain_of_thought": "must never be replayed"},
            canonical_digest({"chain_of_thought": "must never be replayed"}),
            JournalIntegrityError,
            "JOURNAL_INTEGRITY_ERROR",
        ),
        (
            {"status": "factual"},
            "e" * 64,
            EventDigestMismatch,
            "EVENT_DIGEST_MISMATCH",
        ),
    ),
)
async def test_replay_fails_closed_on_private_or_digest_invalid_events(
    db_session: AsyncSession,
    payload: dict[str, str],
    payload_digest: str,
    error_type: type[Exception],
    error_code: str,
) -> None:
    repository, task = await _create_task(db_session)
    db_session.add(
        SvTaskEventRecord(
            id=UUID("20000000-0000-0000-0000-000000000007"),
            event_type=TaskEventType.TASK_REVISED.value,
            task_id=task.id,
            run_id=None,
            task_revision=1,
            run_revision=None,
            payload=payload,
            payload_digest=payload_digest,
            initiated_by_kind=AGENT.kind.value,
            initiated_by_ref=AGENT.ref,
            executed_by_kind=AGENT.kind.value,
            executed_by_ref=AGENT.ref,
            causation_receipt_id=None,
        )
    )
    await db_session.flush()

    with pytest.raises(error_type) as exc_info:
        await repository.read_replay(ReplayQuery(task_id=task.id))

    assert isinstance(exc_info.value, JournalIntegrityError | EventDigestMismatch)
    assert exc_info.value.code == error_code


async def test_database_rejects_oversized_event_payloads(
    db_session: AsyncSession,
) -> None:
    _, task = await _create_task(db_session)
    oversized_payload = {"text": "x" * 17_000}
    savepoint = await db_session.begin_nested()
    with pytest.raises(DBAPIError, match="ck_sv_task_events_payload_size"):
        db_session.add(
            SvTaskEventRecord(
                id=UUID("20000000-0000-0000-0000-000000000008"),
                event_type=TaskEventType.TASK_REVISED.value,
                task_id=task.id,
                run_id=None,
                task_revision=1,
                run_revision=None,
                payload=oversized_payload,
                payload_digest=canonical_digest(oversized_payload),
                initiated_by_kind=AGENT.kind.value,
                initiated_by_ref=AGENT.ref,
                executed_by_kind=AGENT.kind.value,
                executed_by_ref=AGENT.ref,
                causation_receipt_id=None,
            )
        )
        await db_session.flush()
    await savepoint.rollback()
