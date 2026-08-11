from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.connectors.ssrf import SourceFetchBlocked, SsrfGuard
from app.adapters.db.session import get_db_session
from app.api.problems import ApiProblem
from app.application.dispatch import mark_dispatch_failed
from app.application.product_imports import (
    ImportIdempotencyConflictError,
    ProductImportService,
)
from app.worker.tasks import import_product

router = APIRouter(prefix="/api/v1/product-imports", tags=["product-imports"])


def get_ssrf_guard() -> SsrfGuard:
    return SsrfGuard()


class ProductImportInput(BaseModel):
    url: HttpUrl


class ProductImportOutput(BaseModel):
    id: UUID
    state: str
    source_id: UUID


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
    if job.created or job.state == "queued":
        try:
            import_product.delay(str(job.id))
        except Exception as exc:
            await mark_dispatch_failed(session, job.id)
            raise ApiProblem(
                status=503,
                code="BROKER_UNAVAILABLE",
                title="Background queue unavailable",
                detail="The import task could not be dispatched.",
            ) from exc
    response.headers["Location"] = f"/api/v1/jobs/{job.id}"
    return ProductImportOutput(id=job.id, state=job.state, source_id=job.source_id)
