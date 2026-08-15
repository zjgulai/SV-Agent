from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.connectors.schema_org import ParsedProduct
from app.adapters.db.models import ImportAttemptRecord, JobEventRecord, OutboxEventRecord
from app.adapters.db.repositories import (
    ImportAttemptRepository,
    JobRepository,
    OutboxRepository,
)
from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.application.generations import GenerationCommand, GenerationService, GenerationWorker
from app.application.outbox import publish_pending_outbox, retry_dead_outbox
from app.application.product_imports import ProductImportService
from app.domain.jobs.entities import JobState
from app.domain.products.entities import (
    FactStatus,
    ProductFact,
    ProductSnapshot,
    ProductSource,
    SourceType,
)
from app.worker.tasks import ProductImportWorker


class SuccessfulConnector:
    async def fetch(self, _url: str) -> ParsedProduct:
        return ParsedProduct(
            title="Imported product",
            description="Public description",
            category_path=(),
            images=(),
            price_amount=None,
            price_currency=None,
            raw_payload={"title": "Imported product"},
            resolution_digest="a" * 64,
        )


async def _ready_generation_job(db_session: AsyncSession) -> UUID:
    source = ProductSource.create(
        source_type=SourceType.MANUAL,
        raw_payload={"title": "Ledger product"},
    )
    snapshot = ProductSnapshot.create(
        source_id=source.id,
        title="Ledger product",
        description="Evidence-backed product",
    )
    fact = ProductFact.create(
        snapshot_id=snapshot.id,
        claim_type="feature",
        claim="The pouch is resealable",
        value={"resealable": True},
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt="The pouch is resealable",
        confidence=1,
        status=FactStatus.LOCKED,
    )
    async with db_session.begin_nested():
        from app.adapters.db.repositories import ProductRepository

        products = ProductRepository(db_session)
        await products.add_source(source)
        await products.add_snapshot(snapshot)
        await products.add_fact(fact)
        queued = await GenerationService(db_session).queue(
            product_id=source.id,
            idempotency_key=f"ledger-{uuid4()}",
            command=GenerationCommand(
                target_duration_seconds=15,
                language="en",
                audience="general",
                creative_pattern_key="problem_solution",
                selected_fact_ids=(fact.id,),
            ),
        )
    return queued.job.id


async def test_queue_commits_initial_job_event_and_outbox_together(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/ledger-{uuid4()}",
        idempotency_key=f"ledger-{uuid4()}",
    )

    events = await JobRepository(db_session).list_events(queued.id)
    outbox = await OutboxRepository(db_session).get_by_job_id(queued.id)

    assert [(JobState(event.to_state), event.attempt_count) for event in events] == [
        (JobState.QUEUED, 0)
    ]
    assert outbox is not None
    assert outbox.task_name == "app.worker.tasks.import_product"
    assert outbox.delivery_state == "pending"


async def test_broker_failure_keeps_job_queued_for_outbox_recovery(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/outbox-{uuid4()}",
        idempotency_key=f"outbox-{uuid4()}",
    )

    def unavailable(_task_name: str, _job_id: UUID) -> None:
        raise OSError("broker unavailable")

    first = await publish_pending_outbox(
        db_session, unavailable, retry_base_seconds=0
    )
    submitted: list[UUID] = []
    second = await publish_pending_outbox(
        db_session,
        lambda _task_name, job_id: submitted.append(job_id),
        job_id=queued.id,
    )
    published = await OutboxRepository(db_session).get_by_job_id(queued.id)
    stored = await JobRepository(db_session).get(queued.id)

    assert first.failed == 1
    assert stored is not None and stored.state is JobState.QUEUED
    assert second.published == 1
    assert submitted == [queued.id]
    assert published is not None and published.delivery_state == "published"


async def test_outbox_dead_letters_exhausted_delivery_without_failing_the_job(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/dead-letter-{uuid4()}",
        idempotency_key=f"dead-letter-{uuid4()}",
    )

    def unavailable(_task_name: str, _job_id: UUID) -> None:
        raise OSError("broker unavailable")

    first = await publish_pending_outbox(
        db_session,
        unavailable,
        max_delivery_attempts=1,
        retry_base_seconds=0,
    )
    second = await publish_pending_outbox(
        db_session,
        lambda _task_name, _job_id: pytest.fail("dead letter must not dispatch"),
        max_delivery_attempts=1,
    )
    stored = await JobRepository(db_session).get(queued.id)
    outbox = await OutboxRepository(db_session).get_by_job_id(queued.id)
    events = await JobRepository(db_session).list_events(queued.id)

    assert first.failed == 1
    assert second.dead_lettered == 1
    assert stored is not None and stored.state is JobState.QUEUED
    assert outbox is not None
    assert outbox.delivery_state == "dead"
    assert outbox.dead_letter_code == "OUTBOX_MAX_DELIVERY_ATTEMPTS"
    assert outbox.dead_lettered_at is not None
    assert [event.event_type for event in events][-1] == "dispatch_dead_lettered"
    assert (await publish_pending_outbox(db_session, unavailable)).claimed == 0


async def test_broker_failure_uses_backoff_before_the_next_delivery_claim(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/backoff-{uuid4()}",
        idempotency_key=f"backoff-{uuid4()}",
    )

    def unavailable(_task_name: str, _job_id: UUID) -> None:
        raise OSError("broker unavailable")

    await publish_pending_outbox(
        db_session,
        unavailable,
        retry_base_seconds=5,
        retry_max_seconds=5,
    )
    outbox = await OutboxRepository(db_session).get_by_job_id(queued.id)
    immediate = await publish_pending_outbox(
        db_session,
        lambda _task_name, _job_id: pytest.fail("backoff must prevent dispatch"),
    )

    assert outbox is not None
    assert outbox.delivery_state == "pending"
    assert outbox.delivery_attempt_count == 1
    assert outbox.available_at > datetime.now(UTC)
    assert immediate.claimed == 0


async def test_outbox_dead_letters_an_expired_delivery_cycle(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/dead-age-{uuid4()}",
        idempotency_key=f"dead-age-{uuid4()}",
    )
    result = await publish_pending_outbox(
        db_session,
        lambda _task_name, _job_id: pytest.fail("expired cycle must not dispatch"),
        max_delivery_age_seconds=0,
    )
    outbox = await OutboxRepository(db_session).get_by_job_id(queued.id)

    assert result.dead_lettered == 1
    assert outbox is not None
    assert outbox.delivery_state == "dead"
    assert outbox.dead_letter_code == "OUTBOX_MAX_DELIVERY_AGE"


async def test_operator_can_requeue_only_a_dead_queued_delivery_cycle(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/manual-retry-{uuid4()}",
        idempotency_key=f"manual-retry-{uuid4()}",
    )

    def unavailable(_task_name: str, _job_id: UUID) -> None:
        raise OSError("broker unavailable")

    await publish_pending_outbox(
        db_session,
        unavailable,
        max_delivery_attempts=1,
        retry_base_seconds=0,
    )
    await publish_pending_outbox(
        db_session,
        unavailable,
        max_delivery_attempts=1,
    )

    retried = await retry_dead_outbox(db_session, job_id=queued.id)
    outbox = await OutboxRepository(db_session).get_by_job_id(queued.id)
    events = await JobRepository(db_session).list_events(queued.id)

    assert retried.id == queued.id
    assert outbox is not None
    assert outbox.delivery_state == "pending"
    assert outbox.delivery_attempt_count == 0
    assert outbox.manual_retry_count == 1
    assert outbox.dead_letter_code is None
    assert [event.event_type for event in events][-1] == "dispatch_manual_retry_scheduled"
    with pytest.raises(ValueError, match="not a dead queued delivery"):
        await retry_dead_outbox(db_session, job_id=queued.id)


async def test_database_rejects_reopening_a_dead_delivery_without_operator_cycle(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/dead-guard-{uuid4()}",
        idempotency_key=f"dead-guard-{uuid4()}",
    )

    def unavailable(_task_name: str, _job_id: UUID) -> None:
        raise OSError("broker unavailable")

    await publish_pending_outbox(
        db_session,
        unavailable,
        max_delivery_attempts=1,
        retry_base_seconds=0,
    )
    await publish_pending_outbox(
        db_session,
        unavailable,
        max_delivery_attempts=1,
    )

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(OutboxEventRecord)
                .where(OutboxEventRecord.job_id == queued.id)
                .values(
                    delivery_state="pending",
                    delivery_attempt_count=0,
                    available_at=datetime.now(UTC),
                    dead_letter_code=None,
                    dead_lettered_at=None,
                )
            )


async def test_generation_events_are_append_only_actual_state_history(
    db_session: AsyncSession,
) -> None:
    job_id = await _ready_generation_job(db_session)
    factory = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    version_id = await GenerationWorker(factory, DeterministicScriptProvider()).run(job_id)
    events = await JobRepository(db_session).list_events(job_id)

    assert version_id is not None
    assert [JobState(event.to_state) for event in events] == [
        JobState.QUEUED,
        JobState.GENERATING,
        JobState.VALIDATING,
        JobState.SUCCEEDED,
    ]
    assert [event.event_sequence for event in events] == sorted(
        event.event_sequence for event in events
    )


async def test_import_attempts_are_immutable_and_reference_the_snapshot(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/import-attempt-{uuid4()}",
        idempotency_key=f"import-attempt-{uuid4()}",
    )
    factory = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    result = await ProductImportWorker(factory, SuccessfulConnector()).run(queued.id)
    attempts = await ImportAttemptRepository(db_session).list_by_job_id(queued.id)

    assert result == queued.source_id
    assert [attempt.stage for attempt in attempts] == ["started", "parsed", "succeeded"]
    assert [attempt.attempt_sequence for attempt in attempts] == sorted(
        attempt.attempt_sequence for attempt in attempts
    )
    assert attempts[0].source_url_digest == "" or len(attempts[0].source_url_digest) == 64
    assert attempts[-1].snapshot_id is not None
    assert attempts[-1].response_digest is not None
    assert len(attempts[-1].response_digest) == 64
    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(ImportAttemptRecord)
                .where(ImportAttemptRecord.id == attempts[-1].id)
                .values(stage="failed")
            )


async def test_outbox_lease_fences_an_expired_publisher(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/lease-{uuid4()}",
        idempotency_key=f"lease-{uuid4()}",
    )
    async with db_session.begin_nested():
        outbox = OutboxRepository(db_session)
        first = await outbox.claim_due(lease_seconds=30, job_id=queued.id)
        assert first is not None and first.lease_token is not None
        first_token = first.lease_token
        await db_session.execute(
            update(OutboxEventRecord)
            .where(OutboxEventRecord.id == first.id)
            .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        second = await outbox.claim_due(lease_seconds=30, job_id=queued.id)
        assert second is not None and second.lease_token is not None
        assert second.lease_token != first_token
        assert not await outbox.mark_published(
            event_id=first.id, lease_token=first_token
        )
        assert await outbox.mark_published(
            event_id=first.id, lease_token=second.lease_token
        )


async def test_reconciler_never_republishes_a_running_job(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/running-{uuid4()}",
        idempotency_key=f"running-{uuid4()}",
    )
    async with db_session.begin_nested():
        outbox = OutboxRepository(db_session)
        leased = await outbox.claim_due(lease_seconds=30, job_id=queued.id)
        assert leased is not None
        jobs = JobRepository(db_session)
        job = await jobs.get(queued.id, for_update=True)
        assert job is not None
        await jobs.save(job.transition_to(JobState.FETCHING))
        await db_session.execute(
            update(OutboxEventRecord)
            .where(OutboxEventRecord.job_id == queued.id)
            .values(
                lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        assert await OutboxRepository(db_session).claim_due(lease_seconds=30) is None


async def test_job_event_rows_are_database_immutable(db_session: AsyncSession) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/immutable-event-{uuid4()}",
        idempotency_key=f"immutable-event-{uuid4()}",
    )
    event = (await JobRepository(db_session).list_events(queued.id))[0]

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(JobEventRecord)
                .where(JobEventRecord.id == event.id)
                .values(event_type="rewritten")
            )
    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(OutboxEventRecord)
                .where(OutboxEventRecord.job_id == queued.id)
                .values(payload={"rewritten": True})
            )
