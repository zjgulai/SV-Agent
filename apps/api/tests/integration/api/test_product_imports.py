import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.connectors.schema_org import ParsedProduct, SourceUnavailable
from app.adapters.db.models import ProductSourceRecord
from app.adapters.db.repositories import JobRepository
from app.application.product_imports import ProductImportService
from app.domain.jobs.entities import JobState
from app.worker.tasks import ProductImportWorker


class ControlledConnector:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def fetch(self, _url: str) -> ParsedProduct:
        self.started.set()
        await self.release.wait()
        if self.fail:
            raise SourceUnavailable("controlled import failure")
        return ParsedProduct(
            title="Imported product",
            description="Public product description",
            category_path=(),
            images=(),
            price_amount=None,
            price_currency=None,
            raw_payload={"title": "Imported product"},
        )


async def test_product_import_creates_idempotent_queued_job(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatched: list[str] = []
    monkeypatch.setattr(
        "app.worker.tasks.import_product.delay",
        lambda job_id: dispatched.append(job_id),
    )
    headers = {"Idempotency-Key": "import-001"}
    first = await client.post(
        "/api/v1/product-imports",
        headers=headers,
        json={"url": "https://example.com/product"},
    )
    second = await client.post(
        "/api/v1/product-imports",
        headers=headers,
        json={"url": "https://example.com/product"},
    )
    third = await client.post(
        "/api/v1/product-imports",
        headers={"Idempotency-Key": "import-002"},
        json={"url": "https://example.com/product"},
    )

    assert first.status_code == 202
    assert first.headers["location"] == f"/api/v1/jobs/{first.json()['id']}"
    assert first.json()["state"] == "queued"
    assert second.status_code == 202
    assert second.json()["id"] == first.json()["id"]
    assert third.status_code == 202
    assert third.json()["id"] != first.json()["id"]
    assert third.json()["source_id"] == first.json()["source_id"]
    source = await db_session.get(ProductSourceRecord, first.json()["source_id"])
    assert source is not None and source.raw_payload == {}
    assert dispatched == [first.json()["id"], third.json()["id"]]


async def test_distinct_import_keys_reuse_one_url_source(db_session: AsyncSession) -> None:
    url = f"https://example.com/concurrent-{uuid4()}"

    first = await ProductImportService(db_session).queue(
        url=url, idempotency_key=f"a-{uuid4()}"
    )
    second = await ProductImportService(db_session).queue(
        url=url, idempotency_key=f"b-{uuid4()}"
    )

    assert first.source_id == second.source_id


async def test_import_redelivery_fences_stale_worker_terminal_write(
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/fenced-{uuid4()}",
        idempotency_key=f"fenced-{uuid4()}",
    )
    factory = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    stale_connector = ControlledConnector(fail=True)
    current_connector = ControlledConnector()
    stale_run = asyncio.create_task(
        ProductImportWorker(factory, stale_connector).run(queued.id)
    )
    await stale_connector.started.wait()
    current_run = asyncio.create_task(
        ProductImportWorker(factory, current_connector).run(
            queued.id, allow_retry=True
        )
    )
    await current_connector.started.wait()

    stale_connector.release.set()
    await stale_run
    during_redelivery = await JobRepository(db_session).get(queued.id)
    current_connector.release.set()
    current_source_id = await current_run
    completed = await JobRepository(db_session).get(queued.id)

    assert during_redelivery is not None
    assert during_redelivery.state is JobState.FETCHING
    assert current_source_id == queued.source_id
    assert completed is not None and completed.state is JobState.SUCCEEDED
