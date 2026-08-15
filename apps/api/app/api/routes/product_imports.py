import logging
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.connectors.ssrf import SourceFetchBlocked, SsrfGuard
from app.adapters.db.models import ImportAttemptRecord
from app.adapters.db.repositories import ImportAttemptRepository, JobRepository
from app.adapters.db.session import get_db_session
from app.api.problems import ApiProblem
from app.api.schemas.scripts import ImportAttemptOutput
from app.application.outbox import publish_job_outbox
from app.application.product_imports import (
    ImportIdempotencyConflictError,
    ProductImportService,
)
from app.worker.tasks import dispatch_job

router = APIRouter(prefix="/api/v1/product-imports", tags=["product-imports"])
LOGGER = logging.getLogger(__name__)


def get_ssrf_guard() -> SsrfGuard:
    return SsrfGuard()


class ProductImportInput(BaseModel):
    url: HttpUrl


class ProductImportOutput(BaseModel):
    id: UUID
    state: str
    source_id: UUID


def import_attempt_output(record: ImportAttemptRecord) -> ImportAttemptOutput:
    return ImportAttemptOutput(
        id=record.id,
        job_id=record.job_id,
        source_id=record.source_id,
        attempt_token=record.attempt_token,
        stage=cast(Literal["started", "parsed", "succeeded", "failed"], record.stage),
        source_url_digest=record.source_url_digest,
        resolution_digest=record.resolution_digest,
        response_digest=record.response_digest,
        snapshot_id=record.snapshot_id,
        error_code=record.error_code,
        attempt_sequence=record.attempt_sequence,
        created_at=record.created_at,
    )


@router.post("", response_model=ProductImportOutput, status_code=status.HTTP_202_ACCEPTED)
async def create_product_import(
    payload: ProductImportInput,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    guard: Annotated[SsrfGuard, Depends(get_ssrf_guard)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> ProductImportOutput:
    try:
        validated = await guard.validate(str(payload.url))
        job = await ProductImportService(session).queue(
            url=validated.url, idempotency_key=idempotency_key
        )
    except SourceFetchBlocked as exc:
        raise ApiProblem(
            status=422,
            code=exc.code,
            title="Product URL blocked",
            detail="The product URL did not pass the public-network safety policy.",
        ) from exc
    except ImportIdempotencyConflictError as exc:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Idempotency conflict",
            detail="This Idempotency-Key was already used with different input.",
        ) from exc
    try:
        await publish_job_outbox(session, dispatch_job, job_id=job.id)
    except (OSError, SQLAlchemyError):
        # The durable event has already committed. The reconciler owns recovery.
        LOGGER.warning("immediate import outbox dispatch deferred", exc_info=True)
    response.headers["Location"] = f"/api/v1/jobs/{job.id}"
    return ProductImportOutput(id=job.id, state=job.state, source_id=job.source_id)


@router.get("/{job_id}/attempts", response_model=list[ImportAttemptOutput])
async def list_import_attempts(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ImportAttemptOutput]:
    job = await JobRepository(session).get(job_id)
    if job is None or job.job_type.value != "product_import":
        raise ApiProblem(
            status=404,
            code="JOB_NOT_FOUND",
            title="Job not found",
            detail="The requested product import job does not exist.",
        )
    return [
        import_attempt_output(item)
        for item in await ImportAttemptRepository(session).list_by_job_id(job_id)
    ]
