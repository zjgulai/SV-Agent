import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.connectors.schema_org import (
    ProductDataMissing,
    SchemaOrgProductConnector,
    SourceContentTypeUnsupported,
    SourceFetchTimeout,
    SourceHttpError,
    SourceTooLarge,
    SourceUnavailable,
)
from app.adapters.connectors.ssrf import SourceFetchBlocked
from app.adapters.db.models import ProductSourceRecord
from app.adapters.db.repositories import JobRepository, ProductRepository
from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.adapters.providers.openai_compatible import OpenAICompatibleScriptProvider
from app.application.generations import GenerationWorker
from app.domain.common.canonical import canonical_digest
from app.domain.jobs.entities import TERMINAL_STATES, JobState, JobType
from app.domain.products.entities import ProductFact, ProductSnapshot
from app.ports.product_connector import ProductConnector
from app.settings import provider_api_key_is_configured, settings
from app.worker.celery_app import celery_app


class ProductImportWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        connector: ProductConnector,
    ) -> None:
        self.session_factory = session_factory
        self.connector = connector

    async def run(self, job_id: UUID, *, allow_retry: bool = False) -> UUID | None:
        source_id, source_url, should_execute, attempt_token = await self._start(
            job_id, allow_retry=allow_retry
        )
        if not should_execute:
            return source_id
        assert source_url is not None
        assert attempt_token is not None
        try:
            parsed = await self.connector.fetch(source_url)
            if not await self._mark_parsing(job_id, attempt_token=attempt_token):
                return None
            async with self.session_factory() as session, session.begin():
                jobs = JobRepository(session)
                job = await jobs.get(job_id, for_update=True)
                if job is None or job.result_id is None:
                    raise LookupError(str(job_id))
                if (
                    job.attempt_count != attempt_token
                    or job.state is not JobState.PARSING
                ):
                    return job.result_id if job.state is JobState.SUCCEEDED else None
                source = await session.scalar(
                    select(ProductSourceRecord)
                    .where(ProductSourceRecord.id == job.result_id)
                    .with_for_update()
                )
                if source is None:
                    raise LookupError(str(job.result_id))
                source.raw_payload = parsed.raw_payload
                source.content_digest = canonical_digest(parsed.raw_payload)
                source.parse_status = "succeeded"
                source.error_code = None
                source.retrieved_at = datetime.now(UTC)
                snapshot = ProductSnapshot.create(
                    source_id=source.id,
                    title=parsed.title,
                    description=parsed.description,
                    category_path=parsed.category_path,
                    images=parsed.images,
                    price_amount=parsed.price_amount,
                    price_currency=parsed.price_currency,
                )
                products = ProductRepository(session)
                await products.add_snapshot(snapshot)
                for fact in self._proposed_facts(snapshot, parsed.description):
                    await products.add_fact(fact)
                await jobs.save(job.transition_to(JobState.SUCCEEDED))
                return source.id
        except (SQLAlchemyError, OSError):
            raise
        except (
            SourceFetchBlocked,
            SourceFetchTimeout,
            SourceHttpError,
            SourceTooLarge,
            SourceUnavailable,
            SourceContentTypeUnsupported,
            ProductDataMissing,
        ) as exc:
            await self._mark_failed(job_id, exc.code, attempt_token=attempt_token)
            return None
        except Exception:
            await self._mark_failed(
                job_id, "PRODUCT_IMPORT_FAILED", attempt_token=attempt_token
            )
            raise

    async def _start(
        self, job_id: UUID, *, allow_retry: bool
    ) -> tuple[UUID | None, str | None, bool, int | None]:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if job is None or job.job_type is not JobType.PRODUCT_IMPORT or job.result_id is None:
                raise LookupError(str(job_id))
            source = await session.get(ProductSourceRecord, job.result_id)
            if source is None:
                raise LookupError(str(job.result_id))
            if job.state in TERMINAL_STATES:
                return source.id, None, False, None
            if job.state is JobState.QUEUED:
                job = job.transition_to(JobState.FETCHING)
                await jobs.save(job)
            elif allow_retry:
                job = job.register_retry()
                await jobs.save(job)
            else:
                return None, None, False, None
            return source.id, source.source_url, True, job.attempt_count

    async def _mark_parsing(self, job_id: UUID, *, attempt_token: int) -> bool:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if job is None or job.attempt_count != attempt_token:
                return False
            if job.state is JobState.FETCHING:
                await jobs.save(job.transition_to(JobState.PARSING))
                return True
            return job.state is JobState.PARSING

    async def _mark_failed(
        self, job_id: UUID, code: str, *, attempt_token: int
    ) -> None:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if (
                job is None
                or job.state in TERMINAL_STATES
                or job.attempt_count != attempt_token
            ):
                return
            if job.result_id is not None:
                source = await session.get(ProductSourceRecord, job.result_id)
                if source is not None:
                    source.parse_status = "failed"
                    source.error_code = code
            await jobs.save(
                job.transition_to(
                    JobState.FAILED,
                    error_code=code,
                    error_detail="Product import failed safely.",
                )
            )

    @staticmethod
    def _proposed_facts(
        snapshot: ProductSnapshot, description: str
    ) -> list[ProductFact]:
        facts: list[ProductFact] = []
        if description:
            facts.append(
                ProductFact.create(
                    snapshot_id=snapshot.id,
                    claim_type="description",
                    claim=description,
                    value={"description": description},
                    evidence_kind="source_field",
                    evidence_locator="description",
                    evidence_excerpt=description[:1000],
                    confidence=Decimal(1),
                )
            )
        if snapshot.price_amount is not None and snapshot.price_currency is not None:
            price_claim = f"Listed price: {snapshot.price_amount} {snapshot.price_currency}"
            facts.append(
                ProductFact.create(
                    snapshot_id=snapshot.id,
                    claim_type="price",
                    claim=price_claim,
                    value={
                        "amount": str(snapshot.price_amount),
                        "currency": snapshot.price_currency,
                    },
                    evidence_kind="source_field",
                    evidence_locator="offers.price",
                    evidence_excerpt=price_claim,
                    confidence=Decimal(1),
                )
            )
        return facts


async def _run_generation(job_id: UUID, *, allow_retry: bool = False) -> str | None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        if settings.script_provider == "openai_compatible":
            if not provider_api_key_is_configured(settings.provider_api_key):
                await GenerationWorker(
                    factory, DeterministicScriptProvider()
                ).fail_before_provider(
                    job_id,
                    code="PROVIDER_MISCONFIGURED",
                    detail="The configured script provider is missing its API key.",
                    allow_retry=allow_retry,
                )
                return None
            async with httpx.AsyncClient() as client:
                assert settings.provider_api_key is not None
                provider = OpenAICompatibleScriptProvider(
                    client=client,
                    base_url=settings.provider_base_url,
                    model=settings.provider_model,
                    api_key=settings.provider_api_key.get_secret_value(),
                )
                result = await GenerationWorker(factory, provider).run(
                    job_id, allow_retry=allow_retry
                )
        else:
            result = await GenerationWorker(factory, DeterministicScriptProvider()).run(
                job_id, allow_retry=allow_retry
            )
        return str(result) if result is not None else None
    finally:
        await engine.dispose()


async def _run_import(job_id: UUID, *, allow_retry: bool = False) -> str | None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            result = await ProductImportWorker(
                factory, SchemaOrgProductConnector(client)
            ).run(job_id, allow_retry=allow_retry)
        return str(result) if result is not None else None
    finally:
        await engine.dispose()


TRANSIENT_INFRASTRUCTURE_ERRORS = (SQLAlchemyError, OSError)


def _is_retry_or_redelivery(task: object) -> bool:
    request = getattr(task, "request", None)
    delivery_info = getattr(request, "delivery_info", None) or {}
    retries = int(getattr(request, "retries", 0) or 0)
    return bool(delivery_info.get("redelivered")) or retries > 0


@celery_app.task(
    bind=True,
    name="app.worker.tasks.generate_script",
    autoretry_for=TRANSIENT_INFRASTRUCTURE_ERRORS,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=None,
)
def generate_script(task: object, job_id: str) -> str | None:
    return asyncio.run(
        _run_generation(UUID(job_id), allow_retry=_is_retry_or_redelivery(task))
    )


@celery_app.task(
    bind=True,
    name="app.worker.tasks.import_product",
    autoretry_for=TRANSIENT_INFRASTRUCTURE_ERRORS,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=None,
)
def import_product(task: object, job_id: str) -> str | None:
    return asyncio.run(
        _run_import(UUID(job_id), allow_retry=_is_retry_or_redelivery(task))
    )
