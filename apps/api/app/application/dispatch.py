from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import JobRepository
from app.domain.jobs.entities import JobState


async def mark_dispatch_failed(session: AsyncSession, job_id: UUID) -> None:
    async with session.begin():
        repository = JobRepository(session)
        job = await repository.get(job_id, for_update=True)
        if job is not None and job.state is JobState.QUEUED:
            await repository.save(
                job.transition_to(
                    JobState.FAILED,
                    error_code="BROKER_UNAVAILABLE",
                    error_detail="The background task could not be dispatched.",
                )
            )
