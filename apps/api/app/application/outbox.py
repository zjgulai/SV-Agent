from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.repositories import JobRepository, OutboxRepository
from app.domain.jobs.entities import JobType
from app.settings import settings

TaskDispatcher = Callable[[str, UUID], None]

TASK_NAME_BY_JOB_TYPE = {
    JobType.PRODUCT_IMPORT: "app.worker.tasks.import_product",
    JobType.SCRIPT_GENERATION: "app.worker.tasks.generate_script",
}


def task_name_for(job_type: JobType) -> str:
    return TASK_NAME_BY_JOB_TYPE[job_type]


@dataclass(frozen=True, slots=True)
class PublishResult:
    claimed: int = 0
    published: int = 0
    failed: int = 0
    dead_lettered: int = 0


def _backoff_seconds(*, attempt: int, base_seconds: int, max_seconds: int) -> int:
    return min(base_seconds * (2 ** max(attempt - 1, 0)), max_seconds)


@asynccontextmanager
async def _transaction(session: AsyncSession) -> AsyncIterator[None]:
    transaction = session.begin_nested() if session.in_transaction() else session.begin()
    async with transaction:
        yield


async def publish_pending_outbox(
    session: AsyncSession,
    dispatcher: TaskDispatcher,
    *,
    limit: int = 1,
    lease_seconds: int = 30,
    job_id: UUID | None = None,
    max_delivery_attempts: int | None = None,
    max_delivery_age_seconds: int | None = None,
    retry_base_seconds: int | None = None,
    retry_max_seconds: int | None = None,
) -> PublishResult:
    """Claim and publish due work without turning broker failure into Job failure."""

    max_delivery_attempts = max_delivery_attempts or settings.outbox_max_delivery_attempts
    max_delivery_age_seconds = (
        settings.outbox_max_delivery_age_seconds
        if max_delivery_age_seconds is None
        else max_delivery_age_seconds
    )
    retry_base_seconds = (
        settings.outbox_retry_base_seconds if retry_base_seconds is None else retry_base_seconds
    )
    retry_max_seconds = (
        settings.outbox_retry_max_seconds if retry_max_seconds is None else retry_max_seconds
    )
    result = PublishResult()
    for _ in range(limit):
        async with _transaction(session):
            outbox = OutboxRepository(session)
            dead_letter = await outbox.dead_letter_due(
                max_delivery_attempts=max_delivery_attempts,
                max_delivery_age_seconds=max_delivery_age_seconds,
                job_id=job_id,
            )
            if dead_letter is not None:
                job = await JobRepository(session).get(dead_letter.job_id, for_update=True)
                if job is None:
                    raise LookupError(f"outbox job {dead_letter.job_id} does not exist")
                await JobRepository(session).append_event(
                    job,
                    event_type="dispatch_dead_lettered",
                    error_code=dead_letter.dead_letter_code,
                    error_detail="Task broker delivery requires operator recovery.",
                )
            if dead_letter is not None:
                event = None
            else:
                event = await outbox.claim_due(lease_seconds=lease_seconds, job_id=job_id)
                if event is not None:
                    job = await JobRepository(session).get(event.job_id, for_update=True)
                    if job is None:
                        raise LookupError(f"outbox job {event.job_id} does not exist")
                    await JobRepository(session).append_event(
                        job,
                        event_type="dispatch_leased",
                        error_code=None,
                        error_detail=None,
                    )

        if dead_letter is not None:
            result = PublishResult(
                claimed=result.claimed,
                published=result.published,
                failed=result.failed,
                dead_lettered=result.dead_lettered + 1,
            )
            continue
        if event is None:
            return result

        result = PublishResult(
            claimed=result.claimed + 1,
            published=result.published,
            failed=result.failed,
            dead_lettered=result.dead_lettered,
        )
        assert event.lease_token is not None
        try:
            dispatcher(event.task_name, event.job_id)
        except OSError:
            async with _transaction(session):
                released = await OutboxRepository(session).release(
                    event_id=event.id,
                    lease_token=event.lease_token,
                    error_code="BROKER_UNAVAILABLE",
                    error_detail="The task broker did not accept the dispatch.",
                    backoff_seconds=_backoff_seconds(
                        attempt=event.delivery_attempt_count,
                        base_seconds=retry_base_seconds,
                        max_seconds=retry_max_seconds,
                    ),
                )
                if released:
                    job = await JobRepository(session).get(event.job_id, for_update=True)
                    if job is None:
                        raise LookupError(f"outbox job {event.job_id} does not exist")
                    await JobRepository(session).append_event(
                        job,
                        event_type="dispatch_retry_scheduled",
                        error_code="BROKER_UNAVAILABLE",
                        error_detail="The task broker did not accept the dispatch.",
                    )
                    result = PublishResult(
                        claimed=result.claimed,
                        published=result.published,
                        failed=result.failed + 1,
                        dead_lettered=result.dead_lettered,
                    )
            continue

        async with _transaction(session):
            published = await OutboxRepository(session).mark_published(
                event_id=event.id, lease_token=event.lease_token
            )
            if published:
                job = await JobRepository(session).get(event.job_id, for_update=True)
                if job is None:
                    raise LookupError(f"outbox job {event.job_id} does not exist")
                await JobRepository(session).append_event(
                    job,
                    event_type="dispatch_published",
                    error_code=None,
                    error_detail=None,
                )
                result = PublishResult(
                    claimed=result.claimed,
                    published=result.published + 1,
                    failed=result.failed,
                    dead_lettered=result.dead_lettered,
                )
    return result


async def publish_job_outbox(
    session: AsyncSession,
    dispatcher: TaskDispatcher,
    *,
    job_id: UUID,
    lease_seconds: int = 30,
) -> PublishResult:
    """Nudge one newly created/replayed Job without stealing another Job's work."""

    return await publish_pending_outbox(
        session,
        dispatcher,
        limit=1,
        lease_seconds=lease_seconds,
        job_id=job_id,
    )


async def reconcile_pending_outbox(
    session_factory: async_sessionmaker[AsyncSession],
    dispatcher: TaskDispatcher,
    *,
    limit: int = 100,
    lease_seconds: int = 30,
) -> PublishResult:
    """Run a bounded reconciliation pass from a process independent of Celery Beat."""

    result = PublishResult()
    for _ in range(limit):
        async with session_factory() as session:
            current = await publish_pending_outbox(
                session, dispatcher, limit=1, lease_seconds=lease_seconds
            )
        result = PublishResult(
            claimed=result.claimed + current.claimed,
            published=result.published + current.published,
            failed=result.failed + current.failed,
            dead_lettered=result.dead_lettered + current.dead_lettered,
        )
        if current.claimed == 0 and current.dead_lettered == 0:
            return result
    return result


async def retry_dead_outbox(session: AsyncSession, *, job_id: UUID):
    """Requeue a dead broker delivery from a deployment-channel operator command."""

    async with _transaction(session):
        outbox = OutboxRepository(session)
        event = await outbox.retry_dead(job_id=job_id)
        if event is None:
            raise ValueError("job is not a dead queued delivery")
        job = await JobRepository(session).get(job_id, for_update=True)
        if job is None:
            raise LookupError(f"outbox job {job_id} does not exist")
        await JobRepository(session).append_event(
            job,
            event_type="dispatch_manual_retry_scheduled",
            error_code=None,
            error_detail=None,
        )
        return job
