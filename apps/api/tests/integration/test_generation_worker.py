from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import ScriptVersionRecord
from app.adapters.db.repositories import JobRepository, ProductRepository
from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.application.generations import GenerationCommand, GenerationService, GenerationWorker
from app.domain.jobs.entities import JobState
from app.domain.products.entities import (
    FactStatus,
    ProductFact,
    ProductSnapshot,
    ProductSource,
    SourceType,
)
from app.settings import settings

SOURCE_ID = UUID("00000000-0000-0000-0000-000000000301")
SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000302")
FACT_ID = UUID("00000000-0000-0000-0000-000000000303")


async def test_repeated_generation_delivery_creates_one_version_and_db_survives_redis_loss(
    db_session: AsyncSession,
) -> None:
    async with db_session.begin_nested():
        products = ProductRepository(db_session)
        await products.add_source(
            ProductSource.create(
                id=SOURCE_ID,
                source_type=SourceType.MANUAL,
                raw_payload={"title": "Pulse Mix"},
            )
        )
        await products.add_snapshot(
            ProductSnapshot.create(
                id=SNAPSHOT_ID,
                source_id=SOURCE_ID,
                title="Pulse Mix",
                description="Resealable pouch",
            )
        )
        await products.add_fact(
            ProductFact.create(
                id=FACT_ID,
                snapshot_id=SNAPSHOT_ID,
                claim_type="feature",
                claim="The pouch is resealable",
                value={"resealable": True},
                evidence_kind="user_assertion",
                evidence_locator="manual-form",
                evidence_excerpt="Resealable pouch",
                confidence=1,
                status=FactStatus.LOCKED,
            )
        )
        queued = await GenerationService(db_session).queue(
            product_id=SOURCE_ID,
            idempotency_key="worker-001",
            command=GenerationCommand(
                target_duration_seconds=15,
                language="en",
                audience="busy professionals",
                creative_pattern_key="problem_solution",
            ),
        )
        job = queued.job

    session_factory = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    worker = GenerationWorker(session_factory, DeterministicScriptProvider())

    first_version_id = await worker.run(job.id)
    second_version_id = await worker.run(job.id)

    version_count = await db_session.scalar(
        select(func.count()).select_from(ScriptVersionRecord).where(
            ScriptVersionRecord.generation_id == job.result_id
        )
    )
    stored_job = await JobRepository(db_session).get(job.id)
    redis = Redis.from_url(settings.redis_url)
    result_key = f"celery-task-meta-{job.id}"
    await redis.set(result_key, "transient-result")
    await redis.delete(result_key)
    await redis.aclose()
    stored_after_redis_loss = await JobRepository(db_session).get(job.id)

    assert first_version_id is not None
    assert second_version_id == first_version_id
    assert version_count == 1
    assert stored_job is not None and stored_job.state is JobState.SUCCEEDED
    assert stored_after_redis_loss is not None
    assert stored_after_redis_loss.state is JobState.SUCCEEDED
