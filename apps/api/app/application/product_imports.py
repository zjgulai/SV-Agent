from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import JobRecord
from app.adapters.db.repositories import ProductRepository
from app.domain.common.canonical import canonical_digest


class ImportIdempotencyConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class QueuedImport:
    id: UUID
    state: str
    source_id: UUID
    created: bool


class ProductImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def queue(self, *, url: str, idempotency_key: str) -> QueuedImport:
        input_digest = canonical_digest({"url": url})
        job_id = uuid4()
        async with self.session.begin():
            products = ProductRepository(self.session)
            source = await products.get_or_create_url_source(url)
            inserted_id = await self.session.scalar(
                insert(JobRecord)
                .values(
                    id=job_id,
                    job_type="product_import",
                    idempotency_key=idempotency_key,
                    state="queued",
                    input_digest=input_digest,
                    attempt_count=0,
                    result_id=source.id,
                )
                .on_conflict_do_nothing(constraint="uq_job_idempotency")
                .returning(JobRecord.id)
            )
            if inserted_id is not None:
                return QueuedImport(
                    id=inserted_id,
                    state="queued",
                    source_id=source.id,
                    created=True,
                )

            existing = await self.session.scalar(
                select(JobRecord).where(
                    JobRecord.job_type == "product_import",
                    JobRecord.idempotency_key == idempotency_key,
                )
            )
            if existing is None:
                raise RuntimeError("idempotency insert returned no job")
            if existing.input_digest != input_digest:
                raise ImportIdempotencyConflictError(idempotency_key)
            if existing.result_id is None:
                raise RuntimeError("product import job has no source")
            return QueuedImport(
                id=existing.id,
                state=existing.state,
                source_id=existing.result_id,
                created=False,
            )
