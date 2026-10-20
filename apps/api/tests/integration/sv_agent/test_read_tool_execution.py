from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ImportAttemptRecord,
    JobEventRecord,
    JobRecord,
    OutboxEventRecord,
    ProductFactRecord,
    ProductSnapshotRecord,
    ProductSourceRecord,
    ScriptGenerationRecord,
    ScriptVersionRecord,
    StoryboardApprovalEventRecord,
    StoryboardVersionRecord,
)
from app.adapters.db.repositories import ProductRepository
from app.adapters.db.sv_agent_models import (
    SvRunRecord,
    SvToolJobLinkRecord,
    SvToolRunEventRecord,
    SvToolRunRecord,
)
from app.adapters.db.sv_agent_repository import SvAgentRepository
from app.adapters.db.sv_agent_tool_run_repository import SvToolRunRepository
from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.application.storyboard_reviews import StoryboardReviewService
from app.application.sv_agent_read_tool_execution import (
    ReadToolExecutionContext,
    ReadToolExecutionService,
)
from app.application.sv_agent_tool_contracts import (
    JobReadOutput,
    ReadResultState,
    ReadToolInput,
    ReadToolName,
    ReadToolOutput,
    ScriptProjection,
    ScriptReadOutput,
)
from app.application.sv_agent_tool_errors import ReadToolSourceFailure
from app.application.sv_agent_tool_handler import ApplicationReadToolRuntime
from app.application.sv_agent_tool_registry import StaticReadToolRegistry
from app.domain.common.canonical import canonical_digest
from app.domain.jobs.entities import JobState, JobType
from app.domain.products.entities import (
    FactStatus,
    ProductFact,
    ProductSnapshot,
    ProductSource,
    SourceType,
)
from app.domain.scripts.audience import audience_context
from app.domain.scripts.creative_contract import enforce_creative_contract
from app.domain.scripts.models import ValidationReport
from app.domain.scripts.patterns import compile_pattern
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    RunState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import ToolRunRevisionConflict
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ActorStamp,
    ToolRunEventType,
    ToolRunStatus,
)
from app.domain.sv_agent.tool_runs import ToolRun
from app.ports.script_provider import ScriptGenerationRequest, SupportedFact

TASK_ID = UUID("33000000-0000-0000-0000-000000000001")
RUN_ID = UUID("33000000-0000-0000-0000-000000000002")
MISSING_ID = UUID("33000000-0000-0000-0000-000000000099")
HUMAN = ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer")
AGENT = ActorStamp(kind=ActorKind.AGENT, ref="sv-agent")


@dataclass(frozen=True, slots=True)
class FoundSubjects:
    product_id: UUID
    job_id: UUID
    script_id: UUID
    control_version_id: UUID
    variant_version_id: UUID
    storyboard_id: UUID


BUSINESS_TABLES = (
    ProductSourceRecord,
    ProductSnapshotRecord,
    ProductFactRecord,
    JobRecord,
    JobEventRecord,
    ImportAttemptRecord,
    OutboxEventRecord,
    ScriptGenerationRecord,
    ScriptVersionRecord,
    StoryboardVersionRecord,
    StoryboardApprovalEventRecord,
)


async def _business_counts(db_session: AsyncSession) -> dict[str, int]:
    return {
        table.__tablename__: int(
            await db_session.scalar(select(func.count()).select_from(table)) or 0
        )
        for table in BUSINESS_TABLES
    }


async def _seed_found_subjects(db_session: AsyncSession) -> FoundSubjects:
    product_id = UUID("34000000-0000-0000-0000-000000000001")
    snapshot_id = UUID("34000000-0000-0000-0000-000000000002")
    fact_id = UUID("34000000-0000-0000-0000-000000000003")
    job_id = UUID("34000000-0000-0000-0000-000000000004")
    script_id = UUID("34000000-0000-0000-0000-000000000007")
    control_version_id = UUID("34000000-0000-0000-0000-000000000008")
    variant_version_id = UUID("34000000-0000-0000-0000-000000000009")
    observed_at = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)

    source = ProductSource.create(
        id=product_id,
        source_type=SourceType.MANUAL,
        raw_payload={"title": "Momcozy baby-care proof"},
        retrieved_at=observed_at,
    )
    snapshot = ProductSnapshot.create(
        id=snapshot_id,
        source_id=source.id,
        title="Momcozy baby-care proof",
        description="A frozen test subject for read-only SV-Agent tools.",
        images=("https://example.com/momcozy-proof.png",),
        created_at=observed_at,
    )
    fact = ProductFact.create(
        id=fact_id,
        snapshot_id=snapshot.id,
        claim_type="feature",
        claim="The pouch is resealable",
        value={"resealable": True},
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt="The pouch is resealable",
        confidence=Decimal(1),
        status=FactStatus.CONFIRMED,
        updated_at=observed_at,
    )
    products = ProductRepository(db_session)
    await products.add_source(source)
    await products.add_snapshot(snapshot)
    await products.add_fact(fact)

    compiled_pattern = compile_pattern(
        "problem_solution",
        duration_seconds=15,
        language="en",
        audience_profile_key="general",
    )
    audience = audience_context("general")
    draft = enforce_creative_contract(
        await DeterministicScriptProvider().generate(
            ScriptGenerationRequest(
                snapshot_id=snapshot.id,
                title=snapshot.title,
                facts=[
                    SupportedFact(
                        id=fact.id,
                        claim=fact.claim,
                        claim_type=fact.claim_type,
                    )
                ],
                target_duration_seconds=15,
                language="en",
                audience=audience.label,
                pattern_definition=compiled_pattern,
            )
        ),
        pattern=compiled_pattern,
        promotion=None,
    )
    report = ValidationReport(findings=[])
    db_session.add_all(
        [
            JobRecord(
                id=job_id,
                job_type=JobType.PRODUCT_IMPORT.value,
                idempotency_key="sv-103-found-job",
                state=JobState.SUCCEEDED.value,
                input_digest="1" * 64,
                attempt_count=1,
                error_code=None,
                error_detail="provider-private-detail-must-not-project",
                result_id=snapshot.id,
                created_at=observed_at,
                started_at=observed_at,
                finished_at=observed_at,
            ),
            ScriptGenerationRecord(
                id=script_id,
                snapshot_id=snapshot.id,
                selected_fact_ids=[str(fact.id)],
                excluded_fact_ids=[],
                configuration={
                    "target_duration_seconds": 15,
                    "language": "en",
                    "audience": audience.label,
                    "audience_profile": audience.model_dump(mode="json"),
                    "promotion": None,
                    "pattern_definition": compiled_pattern.model_dump(mode="json"),
                },
                pattern_key=compiled_pattern.key,
                pattern_version=compiled_pattern.version,
                provider="deterministic",
                model="deterministic-v1",
                prompt_contract_version="1.3",
                input_digest="2" * 64,
                created_at=observed_at,
            ),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            JobEventRecord(
                id=UUID("34000000-0000-0000-0000-000000000005"),
                job_id=job_id,
                event_type="job_succeeded",
                from_state=JobState.PARSING.value,
                to_state=JobState.SUCCEEDED.value,
                attempt_count=1,
                error_code=None,
                error_detail="provider-private-detail-must-not-project",
                created_at=observed_at,
            ),
            ImportAttemptRecord(
                id=UUID("34000000-0000-0000-0000-000000000006"),
                job_id=job_id,
                source_id=source.id,
                attempt_token=1,
                stage="succeeded",
                source_url_digest="3" * 64,
                resolution_digest="4" * 64,
                response_digest="5" * 64,
                snapshot_id=snapshot.id,
                error_code=None,
                created_at=observed_at,
            ),
            ScriptVersionRecord(
                id=control_version_id,
                generation_id=script_id,
                parent_version_id=None,
                draft=draft.model_dump(mode="json"),
                validation_report=report.model_dump(mode="json"),
                created_at=observed_at,
            ),
            ScriptVersionRecord(
                id=variant_version_id,
                generation_id=script_id,
                parent_version_id=control_version_id,
                draft=draft.model_copy(
                    update={"titles": ["A second evidence-bound title"]}
                ).model_dump(mode="json"),
                validation_report=report.model_dump(mode="json"),
                created_at=observed_at,
            ),
        ]
    )
    await db_session.flush()
    storyboard = await StoryboardReviewService(db_session).create(
        script_id=script_id,
        version_id=control_version_id,
        operation_key="sv-103-found-storyboard",
    )
    return FoundSubjects(
        product_id=product_id,
        job_id=job_id,
        script_id=script_id,
        control_version_id=control_version_id,
        variant_version_id=variant_version_id,
        storyboard_id=storyboard.record.id,
    )


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
        created_at=datetime(2026, 10, 21, 10, 0, tzinfo=UTC),
    )


async def _runtime(db_session: AsyncSession) -> ReadToolExecutionService:
    task = _task()
    await SvAgentRepository(db_session).create_task(
        task,
        idempotency_key="sv-103-create-task",
        initiated_by=HUMAN,
        executed_by=AGENT,
    )
    db_session.add(
        SvRunRecord(
            id=RUN_ID,
            task_id=TASK_ID,
            task_revision=1,
            revision=1,
            state=RunState.DRAFT.value,
            primary_mechanism=None,
            creative_dimension=None,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    await db_session.flush()
    registry = StaticReadToolRegistry(ApplicationReadToolRuntime(db_session))
    return ReadToolExecutionService(registry, SvToolRunRepository(db_session))


def _context() -> ReadToolExecutionContext:
    return ReadToolExecutionContext(
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=1,
        initiated_by=HUMAN,
        executed_by=AGENT,
    )


async def test_all_six_registered_reads_execute_without_business_side_effects(
    db_session: AsyncSession,
) -> None:
    service = await _runtime(db_session)
    cases = (
        (
            ReadToolName.PRODUCT_TRUTH,
            {"tool": "product_truth.inspect", "product_id": str(MISSING_ID)},
            ReadResultState.NOT_FOUND,
        ),
        (
            ReadToolName.PATTERN_CONTRACT,
            {
                "tool": "pattern_contract.inspect",
                "pattern_key": "problem_solution",
                "pattern_version": "1.3",
                "duration_seconds": 30,
                "language": "en",
                "audience_profile_key": "general",
            },
            ReadResultState.FOUND,
        ),
        (
            ReadToolName.JOB,
            {
                "tool": "job.inspect",
                "job_id": str(MISSING_ID),
                "include_events": True,
                "include_import_attempts": True,
            },
            ReadResultState.NOT_FOUND,
        ),
        (
            ReadToolName.SCRIPT,
            {
                "tool": "script.inspect",
                "query": {"action": "inspect", "script_id": str(MISSING_ID)},
            },
            ReadResultState.NOT_FOUND,
        ),
        (
            ReadToolName.STORYBOARD,
            {
                "tool": "storyboard.inspect",
                "query": {
                    "action": "preflight",
                    "script_id": str(MISSING_ID),
                    "version_id": str(MISSING_ID),
                },
            },
            ReadResultState.NOT_FOUND,
        ),
        (
            ReadToolName.CREATIVE_COMPARISON,
            {
                "tool": "creative_comparison.inspect",
                "script_id": str(MISSING_ID),
                "control_version_id": UUID(int=1),
                "variant_version_id": UUID(int=2),
            },
            ReadResultState.NOT_FOUND,
        ),
    )

    executions = []
    for tool_name, payload, expected_state in cases:
        execution = await service.execute(_context(), tool_name, payload)
        executions.append(execution)
        assert execution.tool_run.status is ToolRunStatus.COMPLETED
        assert execution.output is not None
        assert execution.output.result.state is expected_state

    assert await db_session.scalar(select(func.count()).select_from(SvToolRunRecord)) == 6
    assert await db_session.scalar(select(func.count()).select_from(SvToolRunEventRecord)) == 18
    assert await db_session.scalar(select(func.count()).select_from(SvToolJobLinkRecord)) == 0
    assert {row.tool_name for row in (await db_session.scalars(select(SvToolRunRecord))).all()} == {
        item.value for item in ReadToolName
    }
    assert all(item.tool_run.input_digest for item in executions)


async def test_all_found_read_actions_preserve_business_state_and_journal_result_digests(
    db_session: AsyncSession,
) -> None:
    subjects = await _seed_found_subjects(db_session)
    service = await _runtime(db_session)
    before = await _business_counts(db_session)
    cases = (
        (
            ReadToolName.PRODUCT_TRUTH,
            {
                "tool": "product_truth.inspect",
                "product_id": str(subjects.product_id),
            },
        ),
        (
            ReadToolName.PATTERN_CONTRACT,
            {
                "tool": "pattern_contract.inspect",
                "pattern_key": "problem_solution",
                "pattern_version": "1.3",
                "duration_seconds": 15,
                "language": "en",
                "audience_profile_key": "general",
            },
        ),
        (
            ReadToolName.JOB,
            {
                "tool": "job.inspect",
                "job_id": str(subjects.job_id),
                "include_events": True,
                "include_import_attempts": True,
                "event_limit": 1,
                "import_attempt_limit": 1,
            },
        ),
        (
            ReadToolName.SCRIPT,
            {
                "tool": "script.inspect",
                "query": {
                    "action": "inspect",
                    "script_id": str(subjects.script_id),
                    "version_limit": 1,
                },
            },
        ),
        (
            ReadToolName.SCRIPT,
            {
                "tool": "script.inspect",
                "query": {
                    "action": "version",
                    "script_id": str(subjects.script_id),
                    "version_id": str(subjects.control_version_id),
                },
            },
        ),
        (
            ReadToolName.SCRIPT,
            {
                "tool": "script.inspect",
                "query": {
                    "action": "diff",
                    "script_id": str(subjects.script_id),
                    "left_version_id": str(subjects.control_version_id),
                    "right_version_id": str(subjects.variant_version_id),
                },
            },
        ),
        (
            ReadToolName.SCRIPT,
            {
                "tool": "script.inspect",
                "query": {
                    "action": "export",
                    "script_id": str(subjects.script_id),
                    "version_id": str(subjects.control_version_id),
                    "format": "markdown",
                },
            },
        ),
        (
            ReadToolName.STORYBOARD,
            {
                "tool": "storyboard.inspect",
                "query": {
                    "action": "preflight",
                    "script_id": str(subjects.script_id),
                    "version_id": str(subjects.control_version_id),
                },
            },
        ),
        (
            ReadToolName.STORYBOARD,
            {
                "tool": "storyboard.inspect",
                "query": {
                    "action": "preview",
                    "storyboard_id": str(subjects.storyboard_id),
                },
            },
        ),
        (
            ReadToolName.STORYBOARD,
            {
                "tool": "storyboard.inspect",
                "query": {
                    "action": "approval_state",
                    "storyboard_id": str(subjects.storyboard_id),
                },
            },
        ),
        (
            ReadToolName.CREATIVE_COMPARISON,
            {
                "tool": "creative_comparison.inspect",
                "script_id": str(subjects.script_id),
                "control_version_id": str(subjects.control_version_id),
                "variant_version_id": str(subjects.variant_version_id),
            },
        ),
    )

    executions = []
    for tool_name, payload in cases:
        execution = await service.execute(_context(), tool_name, payload)
        executions.append(execution)
        assert execution.tool_run.status is ToolRunStatus.COMPLETED
        assert execution.output is not None
        assert execution.output.result.state is ReadResultState.FOUND

    assert await _business_counts(db_session) == before
    events = (
        await db_session.scalars(
            select(SvToolRunEventRecord).where(
                SvToolRunEventRecord.event_type == ToolRunEventType.COMPLETED.value
            )
        )
    ).all()
    event_by_run = {item.tool_run_id: item for item in events}
    assert len(event_by_run) == len(cases)
    for execution in executions:
        assert execution.output is not None
        assert event_by_run[execution.tool_run.id].payload["result_digest"] == canonical_digest(
            execution.output.model_dump(mode="json")
        )

    job_output = executions[2].output
    assert isinstance(job_output, JobReadOutput)
    assert "provider-private-detail" not in job_output.model_dump_json()
    script_output = executions[3].output
    assert isinstance(script_output, ScriptReadOutput)
    assert isinstance(script_output.result.value, ScriptProjection)
    assert len(script_output.result.value.versions) == 1


async def test_tool_run_save_rejects_same_revision_from_the_wrong_prior_state(
    db_session: AsyncSession,
) -> None:
    await _runtime(db_session)
    journal = SvToolRunRepository(db_session)
    pending = ToolRun.new(
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=1,
        tool_name=ReadToolName.PRODUCT_TRUTH.value,
        tool_version="1.0.0",
        intent_summary="Inspect product truth without changing business state.",
        input_digest="f" * 64,
    )
    await journal.create(pending, initiated_by=HUMAN, executed_by=AGENT)
    await db_session.execute(
        update(SvToolRunRecord)
        .where(SvToolRunRecord.id == pending.id)
        .values(
            revision=2,
            status=ToolRunStatus.COMPLETED.value,
            started_at=pending.created_at,
            finished_at=pending.created_at,
            updated_at=pending.created_at,
        )
    )

    with pytest.raises(ToolRunRevisionConflict, match="stale"):
        await journal.save(
            pending.start().complete(),
            expected_revision=2,
            result_digest="e" * 64,
            initiated_by=HUMAN,
            executed_by=AGENT,
        )


async def test_unavailable_tool_is_journaled_separately_from_negative_evidence(
    db_session: AsyncSession,
) -> None:
    await _runtime(db_session)
    registry = StaticReadToolRegistry(None)
    service = ReadToolExecutionService(registry, SvToolRunRepository(db_session))

    execution = await service.execute(
        _context(),
        ReadToolName.PRODUCT_TRUTH,
        {"tool": "product_truth.inspect", "product_id": str(MISSING_ID)},
    )

    assert execution.output is None
    assert execution.tool_run.status is ToolRunStatus.UNAVAILABLE
    assert execution.tool_run.stable_error_code == "TOOL_UNAVAILABLE"
    assert execution.tool_run.recovery_action
    events = (
        await db_session.scalars(
            select(SvToolRunEventRecord)
            .where(SvToolRunEventRecord.tool_run_id == execution.tool_run.id)
            .order_by(SvToolRunEventRecord.event_sequence)
        )
    ).all()
    assert [item.event_type for item in events] == [
        ToolRunEventType.CREATED.value,
        ToolRunEventType.STARTED.value,
        ToolRunEventType.UNAVAILABLE.value,
    ]


class FailingRuntime:
    def supports(self, name: ReadToolName) -> bool:
        return name is ReadToolName.PRODUCT_TRUTH

    async def execute(self, command: ReadToolInput) -> ReadToolOutput:
        del command
        raise ReadToolSourceFailure(
            "PRODUCT_TRUTH_UNAVAILABLE",
            "Restore the authoritative Product Truth store, then start a new ToolRun.",
        )


async def test_failure_records_safe_error_recovery_and_revision_fence(
    db_session: AsyncSession,
) -> None:
    await _runtime(db_session)
    journal = SvToolRunRepository(db_session)
    service = ReadToolExecutionService(StaticReadToolRegistry(FailingRuntime()), journal)

    execution = await service.execute(
        _context(),
        ReadToolName.PRODUCT_TRUTH,
        {"tool": "product_truth.inspect", "product_id": str(MISSING_ID)},
    )

    assert execution.output is None
    assert execution.tool_run.status is ToolRunStatus.FAILED
    assert execution.tool_run.stable_error_code == "PRODUCT_TRUTH_UNAVAILABLE"
    assert execution.tool_run.recovery_action == (
        "Restore the authoritative Product Truth store, then start a new ToolRun."
    )
    stored = await db_session.get(SvToolRunRecord, execution.tool_run.id)
    assert stored is not None
    assert stored.intent_summary.startswith("Inspect authoritative Product Snapshot")
    assert stored.artifact_refs == []

    try:
        await journal.save(
            execution.tool_run,
            expected_revision=2,
            initiated_by=HUMAN,
            executed_by=AGENT,
        )
    except ToolRunRevisionConflict:
        pass
    else:
        raise AssertionError("a stale ToolRun revision must not append another event")

    events = (
        await db_session.scalars(
            select(SvToolRunEventRecord)
            .where(SvToolRunEventRecord.tool_run_id == execution.tool_run.id)
            .order_by(SvToolRunEventRecord.event_sequence)
        )
    ).all()
    assert [item.event_type for item in events] == [
        ToolRunEventType.CREATED.value,
        ToolRunEventType.STARTED.value,
        ToolRunEventType.FAILED.value,
    ]
