from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import StoryboardApprovalEventRecord, StoryboardVersionRecord
from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.application.generations import GenerationWorker


@pytest.fixture(autouse=True)
def disable_celery_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.worker.tasks.generate_script.delay", lambda _job_id: None)


def _worker_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


async def _ready_script_version(
    client: AsyncClient, db_session: AsyncSession
) -> tuple[str, UUID, str, str]:
    created = await client.post(
        "/api/v1/products",
        json={
            "title": "Storyboard review product",
            "description": "The pouch is resealable",
            "facts": [
                {
                    "claim_type": "feature",
                    "claim": "The pouch is resealable",
                    "value": {"resealable": True},
                    "evidence_excerpt": "The pouch is resealable",
                }
            ],
        },
    )
    assert created.status_code == 201
    product: dict[str, Any] = created.json()
    product_id = str(product["product_id"])
    fact_id = str(product["facts"][0]["id"])
    confirmed = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "confirmed"}
    )
    assert confirmed.status_code == 200

    queued = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "storyboard-review-script-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [fact_id],
            "excluded_fact_ids": [],
        },
    )
    assert queued.status_code == 202
    job = queued.json()
    generation_id = str(job["result_id"])
    version_id = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(job["id"])))
    assert version_id is not None
    return generation_id, version_id, product_id, fact_id


async def test_storyboard_review_is_idempotent_and_becomes_stale_when_facts_change(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    script_id, version_id, product_id, fact_id = await _ready_script_version(client, db_session)
    path = f"/api/v1/scripts/{script_id}/versions/{version_id}/storyboards"

    created = await client.post(path, headers={"Idempotency-Key": "storyboard-create-001"})
    repeated = await client.post(path, headers={"Idempotency-Key": "storyboard-create-001"})

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert created.json()["id"] == repeated.json()["id"]
    storyboard_id = created.json()["id"]

    preview = await client.get(f"/api/v1/storyboards/{storyboard_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["preview_contract_version"] == "p2.0-animatic-v1"
    assert preview.json()["shots"][0]["supported_fact_ids"] == [fact_id]

    approved = await client.post(
        f"/api/v1/storyboards/{storyboard_id}/approval-events",
        headers={"Idempotency-Key": "storyboard-approval-001"},
        json={"decision": "approved", "reason": "ready for a future quote gate"},
    )
    assert approved.status_code == 201
    conflicting_replay = await client.post(
        f"/api/v1/storyboards/{storyboard_id}/approval-events",
        headers={"Idempotency-Key": "storyboard-approval-001"},
        json={"decision": "rejected", "reason": "same key, different decision"},
    )
    assert conflicting_replay.status_code == 409
    assert conflicting_replay.json()["code"] == "IDEMPOTENCY_CONFLICT"
    current = await client.get(f"/api/v1/storyboards/{storyboard_id}/approval")
    assert current.json()["status"] == "approved"

    rejected = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "rejected"}
    )
    assert rejected.status_code == 200

    stale = await client.get(f"/api/v1/storyboards/{storyboard_id}/approval")
    blocked_approval = await client.post(
        f"/api/v1/storyboards/{storyboard_id}/approval-events",
        headers={"Idempotency-Key": "storyboard-approval-002"},
        json={"decision": "approved"},
    )

    assert stale.json()["status"] == "stale"
    assert blocked_approval.status_code == 409
    assert blocked_approval.json()["code"] == "STORYBOARD_APPROVAL_STALE"


async def test_storyboard_review_refuses_a_version_that_is_no_longer_ready(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    script_id, version_id, product_id, fact_id = await _ready_script_version(client, db_session)
    rejected = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "rejected"}
    )
    assert rejected.status_code == 200

    response = await client.post(
        f"/api/v1/scripts/{script_id}/versions/{version_id}/storyboards",
        headers={"Idempotency-Key": "storyboard-create-blocked-001"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "STORYBOARD_NOT_READY"


async def test_storyboard_approval_becomes_stale_when_its_promotion_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    created = await client.post(
        "/api/v1/products",
        json={
            "title": "Promotion storyboard review product",
            "facts": [
                {
                    "claim_type": "feature",
                    "claim": "The pouch is resealable",
                    "value": {"resealable": True},
                    "evidence_excerpt": "The pouch is resealable",
                }
            ],
        },
    )
    assert created.status_code == 201
    product = created.json()
    product_id = str(product["product_id"])
    fact_id = str(product["facts"][0]["id"])
    assert (
        await client.patch(
            f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "confirmed"}
        )
    ).status_code == 200
    promotion = await client.post(
        f"/api/v1/products/{product_id}/promotion-facts",
        headers={"Idempotency-Key": "storyboard-promotion-fact-001"},
        json={
            "value": {
                "schema_version": "promotion-v1",
                "kind": "percent_off",
                "percent": "10",
                "market": "US",
                "channel": "tiktok_shop",
                "timezone": "America/Los_Angeles",
                "effective_from": "2000-01-01T00:00:00-08:00",
                "effective_to": "2100-01-01T00:00:00-08:00",
            },
            "evidence_excerpt": "Promotion review window",
        },
    )
    assert promotion.status_code == 201
    promotion_id = str(promotion.json()["id"])
    assert (
        await client.patch(
            f"/api/v1/products/{product_id}/facts/{promotion_id}",
            json={"status": "confirmed"},
        )
    ).status_code == 200
    queued = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "storyboard-promotion-script-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "offer_cta",
            "selected_fact_ids": [fact_id],
            "excluded_fact_ids": [],
            "promotion_fact_id": promotion_id,
        },
    )
    assert queued.status_code == 202
    job = queued.json()
    generation_id = str(job["result_id"])
    version_id = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(job["id"])))
    assert version_id is not None
    storyboard = await client.post(
        f"/api/v1/scripts/{generation_id}/versions/{version_id}/storyboards",
        headers={"Idempotency-Key": "storyboard-promotion-create-001"},
    )
    assert storyboard.status_code == 201
    storyboard_id = str(storyboard.json()["id"])
    assert (
        await client.post(
            f"/api/v1/storyboards/{storyboard_id}/approval-events",
            headers={"Idempotency-Key": "storyboard-promotion-approval-001"},
            json={"decision": "approved"},
        )
    ).status_code == 201
    assert (
        await client.patch(
            f"/api/v1/products/{product_id}/facts/{promotion_id}",
            json={"status": "rejected"},
        )
    ).status_code == 200

    preflight = await client.get(
        f"/api/v1/scripts/{generation_id}/versions/{version_id}/storyboard-preflight"
    )
    approval = await client.get(f"/api/v1/storyboards/{storyboard_id}/approval")
    blocked_approval = await client.post(
        f"/api/v1/storyboards/{storyboard_id}/approval-events",
        headers={"Idempotency-Key": "storyboard-promotion-approval-002"},
        json={"decision": "approved"},
    )

    assert preflight.json()["status"] == "blocked"
    assert any(
        item["rule_id"] == "PROMOTION_NOT_ACTIVE"
        for item in preflight.json()["validation_report"]["findings"]
    )
    assert approval.json()["status"] == "stale"
    assert blocked_approval.status_code == 409
    assert blocked_approval.json()["code"] == "STORYBOARD_APPROVAL_STALE"


async def test_storyboard_records_are_database_immutable(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    script_id, version_id, _product_id, _fact_id = await _ready_script_version(client, db_session)
    created = await client.post(
        f"/api/v1/scripts/{script_id}/versions/{version_id}/storyboards",
        headers={"Idempotency-Key": "storyboard-immutable-001"},
    )
    assert created.status_code == 201
    storyboard_id = UUID(created.json()["id"])
    approved = await client.post(
        f"/api/v1/storyboards/{storyboard_id}/approval-events",
        headers={"Idempotency-Key": "storyboard-immutable-approval-001"},
        json={"decision": "approved"},
    )
    assert approved.status_code == 201
    approval_id = UUID(approved.json()["id"])

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(StoryboardVersionRecord)
                .where(StoryboardVersionRecord.id == storyboard_id)
                .values(storyboard_digest="0" * 64)
            )
            await db_session.flush()
    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                delete(StoryboardApprovalEventRecord).where(
                    StoryboardApprovalEventRecord.id == approval_id
                )
            )
            await db_session.flush()
