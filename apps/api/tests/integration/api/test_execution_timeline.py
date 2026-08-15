from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.connectors.schema_org import ParsedProduct
from app.application.product_imports import ProductImportService
from app.worker.tasks import ProductImportWorker


class SuccessfulConnector:
    async def fetch(self, _url: str) -> ParsedProduct:
        return ParsedProduct(
            title="Imported product",
            description="Public description",
            category_path=(),
            images=(),
            price_amount=None,
            price_currency=None,
            raw_payload={"title": "Imported product"},
            resolution_digest="a" * 64,
        )


async def test_job_and_import_attempt_timelines_are_readable_without_raw_payloads(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    queued = await ProductImportService(db_session).queue(
        url=f"https://example.com/readable-attempt-{uuid4()}",
        idempotency_key=f"readable-attempt-{uuid4()}",
    )
    factory = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    await ProductImportWorker(factory, SuccessfulConnector()).run(queued.id)

    events = await client.get(f"/api/v1/jobs/{queued.id}/events")
    attempts = await client.get(f"/api/v1/product-imports/{queued.id}/attempts")

    assert events.status_code == 200
    assert [item["to_state"] for item in events.json()] == [
        "queued",
        "fetching",
        "parsing",
        "succeeded",
    ]
    assert attempts.status_code == 200
    assert [item["stage"] for item in attempts.json()] == [
        "started",
        "parsed",
        "succeeded",
    ]
    assert "raw_payload" not in attempts.text
    assert "example.com" not in attempts.text
