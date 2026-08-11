from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import JobRepository
from app.adapters.db.session import get_db_session
from app.api.problems import ApiProblem
from app.api.schemas.scripts import JobOutput
from app.domain.jobs.entities import Job

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def job_output(job: Job) -> JobOutput:
    return JobOutput(
        id=job.id,
        job_type=job.job_type,
        state=job.state,
        attempt_count=job.attempt_count,
        error_code=job.error_code,
        error_detail=job.error_detail,
        result_id=job.result_id,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/{job_id}", response_model=JobOutput)
async def get_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobOutput:
    job = await JobRepository(session).get(job_id)
    if job is None:
        raise ApiProblem(
            status=404,
            code="JOB_NOT_FOUND",
            title="Job not found",
            detail="The requested job does not exist.",
        )
    return job_output(job)
