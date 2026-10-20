from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import ImportAttemptRepository, JobRepository
from app.application.sv_agent_tool_contracts import (
    ImportAttemptProjection,
    JobEventProjection,
    JobInspectionProjection,
    JobProjection,
    JobReadInput,
    JobReadOutput,
    ReadResult,
)
from app.domain.jobs.entities import JobState, JobType


class JobReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._jobs = JobRepository(session)
        self._attempts = ImportAttemptRepository(session)

    async def inspect(self, command: JobReadInput) -> JobReadOutput:
        job = await self._jobs.get(command.job_id)
        if job is None:
            return JobReadOutput(
                result=ReadResult[JobInspectionProjection].not_found(
                    "JOB_NOT_FOUND",
                    subject_ref=str(command.job_id),
                )
            )

        events = (
            tuple(
                JobEventProjection(
                    id=item.id,
                    event_type=item.event_type,
                    from_state=(JobState(item.from_state) if item.from_state is not None else None),
                    to_state=JobState(item.to_state),
                    attempt_count=item.attempt_count,
                    error_code=item.error_code,
                    event_sequence=item.event_sequence,
                    created_at=item.created_at,
                )
                for item in (await self._jobs.list_events(job.id))[: command.event_limit]
            )
            if command.include_events
            else ()
        )
        attempts = (
            tuple(
                ImportAttemptProjection(
                    id=item.id,
                    job_id=item.job_id,
                    source_id=item.source_id,
                    attempt_token=item.attempt_token,
                    stage=cast(
                        Literal["started", "parsed", "succeeded", "failed"],
                        item.stage,
                    ),
                    source_url_digest=item.source_url_digest,
                    resolution_digest=item.resolution_digest,
                    response_digest=item.response_digest,
                    snapshot_id=item.snapshot_id,
                    error_code=item.error_code,
                    attempt_sequence=item.attempt_sequence,
                    created_at=item.created_at,
                )
                for item in (await self._attempts.list_by_job_id(job.id))[
                    : command.import_attempt_limit
                ]
            )
            if command.include_import_attempts and job.job_type is JobType.PRODUCT_IMPORT
            else ()
        )
        projection = JobInspectionProjection(
            job=JobProjection(
                id=job.id,
                job_type=job.job_type,
                state=job.state,
                attempt_count=job.attempt_count,
                error_code=job.error_code,
                result_id=job.result_id,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
            ),
            events=events,
            import_attempts=attempts,
        )
        return JobReadOutput(result=ReadResult[JobInspectionProjection].found(projection))
