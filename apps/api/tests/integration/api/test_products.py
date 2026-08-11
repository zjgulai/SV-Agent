import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ProductFactRecord, ProductSnapshotRecord


async def _create_product(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/api/v1/products",
        json={
            "title": "Pulse Mix",
            "description": "Resealable drink mix pouch",
            "category_path": ["Food", "Drink Mix"],
            "images": ["https://example.com/pulse.png"],
            "price": {"amount": "19.90", "currency": "USD"},
            "facts": [
                {
                    "claim_type": "feature",
                    "claim": "The pouch is resealable",
                    "value": {"resealable": True},
                    "evidence_excerpt": "Resealable drink mix pouch",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_create_manual_product_returns_snapshot_and_proposed_facts(
    client: AsyncClient,
) -> None:
    body = await _create_product(client)
    assert body["snapshot"]["title"] == "Pulse Mix"
    assert body["facts"][0]["status"] == "proposed"

    product_id = body["product_id"]
    list_response = await client.get("/api/v1/products")
    detail_response = await client.get(f"/api/v1/products/{product_id}")

    assert list_response.status_code == 200
    assert product_id in [item["product_id"] for item in list_response.json()]
    assert detail_response.status_code == 200
    assert detail_response.json()["snapshot"]["canonical_digest"] == body["snapshot"][
        "canonical_digest"
    ]


async def test_fact_can_be_confirmed_and_locked_but_locked_fact_cannot_be_rejected(
    client: AsyncClient,
) -> None:
    body = await _create_product(client)
    product_id = body["product_id"]
    fact_id = body["facts"][0]["id"]

    confirmed = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}",
        json={"status": "confirmed"},
    )
    locked = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}",
        json={"status": "locked"},
    )
    conflict = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}",
        json={"status": "rejected"},
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert locked.status_code == 200
    assert locked.json()["status"] == "locked"
    assert conflict.status_code == 409
    assert conflict.headers["content-type"] == "application/problem+json"
    assert conflict.json()["code"] == "FACT_STATE_CONFLICT"
    detail = await client.get(f"/api/v1/products/{product_id}")
    assert detail.json()["facts"][0]["status"] == "locked"


async def test_manual_fact_cannot_spoof_connector_evidence(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/products",
        json={
            "title": "Spoofed evidence",
            "facts": [
                {
                    "claim_type": "feature",
                    "claim": "Unsupported source claim",
                    "value": {"feature": True},
                    "evidence_excerpt": "Typed by a user",
                    "evidence_kind": "source_field",
                    "evidence_locator": "offers.price",
                }
            ],
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "image_url",
    [
        "http://169.254.169.254/latest/meta-data",
        "https://user:secret@example.com/private.png",
        "https://example.com:444/wrong-port.png",
    ],
)
async def test_manual_product_rejects_non_public_image_urls(
    client: AsyncClient, image_url: str
) -> None:
    response = await client.post(
        "/api/v1/products",
        json={"title": "Unsafe image", "images": [image_url], "facts": []},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "IMAGE_URL_BLOCKED"


async def test_fact_evidence_is_database_immutable(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = await _create_product(client)
    fact_id = body["facts"][0]["id"]

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(ProductFactRecord)
                .where(ProductFactRecord.id == fact_id)
                .values(claim="mutated evidence")
            )


async def test_snapshot_and_locked_fact_are_database_immutable(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = await _create_product(client)
    product_id = body["product_id"]
    snapshot_id = body["snapshot"]["id"]
    fact_id = body["facts"][0]["id"]
    await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "confirmed"}
    )
    await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "locked"}
    )

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(ProductSnapshotRecord)
                .where(ProductSnapshotRecord.id == snapshot_id)
                .values(title="mutated")
            )
    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(ProductFactRecord)
                .where(ProductFactRecord.id == fact_id)
                .values(status="rejected")
            )
