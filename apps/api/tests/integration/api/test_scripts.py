import asyncio
from copy import deepcopy
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import ScriptGenerationRecord, ScriptVersionRecord
from app.adapters.db.repositories import JobRepository, ProductRepository
from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.api.routes import scripts as script_routes
from app.application.generations import GenerationWorker
from app.domain.jobs.entities import JobState
from app.domain.products.entities import FactStatus
from app.domain.scripts.models import ScriptDraft, ScriptPhase, ScriptShot
from app.ports.script_provider import ProviderUnavailable, ScriptGenerationRequest


@pytest.fixture(autouse=True)
def disable_celery_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.worker.tasks.generate_script.delay", lambda _job_id: None)


async def create_ready_product(client: AsyncClient, *, lock_fact: bool = True) -> str:
    created = await client.post(
        "/api/v1/products",
        json={
            "title": "Pulse Mix",
            "description": "Resealable drink mix pouch",
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
    assert created.status_code == 201
    body: dict[str, Any] = created.json()
    product_id = str(body["product_id"])
    fact_id = str(body["facts"][0]["id"])
    confirmed = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "confirmed"}
    )
    assert confirmed.status_code == 200
    if lock_fact:
        locked = await client.patch(
            f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "locked"}
        )
        assert locked.status_code == 200
    return product_id


async def create_ready_product_with_facts(client: AsyncClient, claims: list[str]) -> tuple[str, list[str]]:
    created = await client.post(
        "/api/v1/products",
        json={
            "title": "Pulse Mix",
            "facts": [
                {
                    "claim_type": "feature",
                    "claim": claim,
                    "value": {"claim": claim},
                    "evidence_excerpt": claim,
                }
                for claim in claims
            ],
        },
    )
    assert created.status_code == 201
    body: dict[str, Any] = created.json()
    product_id = str(body["product_id"])
    fact_ids = [str(item["id"]) for item in body["facts"]]
    for fact_id in fact_ids:
        confirmed = await client.patch(
            f"/api/v1/products/{product_id}/facts/{fact_id}", json={"status": "confirmed"}
        )
        assert confirmed.status_code == 200
    return product_id, fact_ids


async def ready_fact_ids(client: AsyncClient, product_id: str) -> list[str]:
    product = await client.get(f"/api/v1/products/{product_id}")
    assert product.status_code == 200
    return [
        str(fact["id"])
        for fact in product.json()["facts"]
        if fact["status"] in {"confirmed", "locked"} and fact["claim_type"] != "promotion"
    ]


async def generation_payload(
    client: AsyncClient,
    product_id: str,
    *,
    duration: int = 15,
) -> dict[str, Any]:
    return {
        "target_duration_seconds": duration,
        "language": "en",
        "audience": "general",
        "creative_pattern_key": "problem_solution",
        "selected_fact_ids": await ready_fact_ids(client, product_id),
        "excluded_fact_ids": [],
    }


async def create_confirmed_promotion_fact(client: AsyncClient, product_id: str) -> str:
    created = await client.post(
        f"/api/v1/products/{product_id}/promotion-facts",
        headers={"Idempotency-Key": f"promotion-{uuid4()}"},
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
            "evidence_excerpt": "Operator-entered promotion window",
        },
    )
    assert created.status_code == 201
    promotion_id = created.json()["id"]
    confirmed = await client.patch(
        f"/api/v1/products/{product_id}/facts/{promotion_id}",
        json={"status": "confirmed"},
    )
    assert confirmed.status_code == 200
    return str(promotion_id)


async def test_repeated_generation_key_returns_same_job(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    dispatched: list[str] = []
    monkeypatch.setattr(
        "app.worker.tasks.generate_script.delay",
        lambda job_id: dispatched.append(job_id),
    )
    ready_product_id = await create_ready_product(client)
    payload = await generation_payload(client, ready_product_id)
    headers = {"Idempotency-Key": "script-001"}

    first = await client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        json=payload,
        headers=headers,
    )
    second = await client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert dispatched == [first.json()["id"]]


async def test_generation_persists_requested_fact_order_and_explicit_exclusions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id, fact_ids = await create_ready_product_with_facts(
        client,
        ["First supported fact", "Second supported fact", "Do not use this fact"],
    )

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "selection-contract-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [fact_ids[1], fact_ids[0]],
            "excluded_fact_ids": [fact_ids[2]],
        },
    )

    assert response.status_code == 202, response.json()
    generation_id = UUID(response.json()["result_id"])
    generation = await db_session.get(ScriptGenerationRecord, generation_id)
    assert generation is not None
    assert generation.selected_fact_ids == [fact_ids[1], fact_ids[0]]
    assert generation.excluded_fact_ids == [fact_ids[2]]

    script = await client.get(f"/api/v1/scripts/{generation_id}")
    assert script.status_code == 200
    assert script.json()["generation"]["selected_fact_ids"] == [fact_ids[1], fact_ids[0]]
    assert script.json()["generation"]["excluded_fact_ids"] == [fact_ids[2]]


@pytest.mark.parametrize(
    ("selected_fact_ids", "excluded_fact_ids"),
    [
        ("duplicate", "valid"),
        ("valid", "overlap"),
    ],
)
async def test_generation_rejects_invalid_fact_selection_contract(
    client: AsyncClient,
    selected_fact_ids: str,
    excluded_fact_ids: str,
) -> None:
    product_id, fact_ids = await create_ready_product_with_facts(
        client,
        ["First supported fact", "Second supported fact"],
    )
    selected = [fact_ids[0], fact_ids[0]] if selected_fact_ids == "duplicate" else [fact_ids[0]]
    excluded = [fact_ids[1]] if excluded_fact_ids == "valid" else [fact_ids[0]]

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": f"selection-invalid-{selected_fact_ids}-{excluded_fact_ids}"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": selected,
            "excluded_fact_ids": excluded,
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "FACT_SELECTION_INVALID"


@pytest.mark.parametrize("selection_field", ["selected_fact_ids", "excluded_fact_ids"])
async def test_generation_rejects_promotion_in_the_fact_selection_contract(
    client: AsyncClient,
    selection_field: str,
) -> None:
    product_id = await create_ready_product(client)
    ordinary_fact_id = (await ready_fact_ids(client, product_id))[0]
    promotion_fact_id = await create_confirmed_promotion_fact(client, product_id)
    payload = await generation_payload(client, product_id)
    payload["selected_fact_ids"] = [ordinary_fact_id]
    payload[selection_field] = [promotion_fact_id]

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": f"promotion-in-{selection_field}"},
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "FACT_SELECTION_INVALID"


async def test_generation_requires_an_explicit_nonempty_selection(client: AsyncClient) -> None:
    product_id = await create_ready_product(client)

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "selection-empty-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "FACTS_NOT_READY"


async def test_generation_requires_the_selection_field(client: AsyncClient) -> None:
    product_id = await create_ready_product(client)

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "selection-required-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "excluded_fact_ids": [],
        },
    )

    assert response.status_code == 422


async def test_broker_failure_keeps_generation_job_queued_for_recovery(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id = await create_ready_product(client)
    payload = await generation_payload(client, product_id)
    headers = {"Idempotency-Key": "broker-failure-001"}

    def fail_dispatch(_job_id: str) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("app.worker.tasks.generate_script.delay", fail_dispatch)
    failed = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        json=payload,
        headers=headers,
    )
    monkeypatch.setattr("app.worker.tasks.generate_script.delay", lambda _job_id: None)
    replay = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        json=payload,
        headers=headers,
    )

    assert failed.status_code == 202
    assert failed.json()["state"] == "queued"
    assert replay.status_code == 202
    assert replay.json()["state"] == "queued"
    assert replay.json()["error_code"] is None


async def test_generation_rejects_missing_provider_key(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id = await create_ready_product(client)
    monkeypatch.setattr(script_routes.settings, "script_provider", "openai_compatible")
    monkeypatch.setattr(script_routes.settings, "provider_api_key", None)

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "missing-provider-key-001"},
        json=await generation_payload(client, product_id),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "PROVIDER_MISCONFIGURED"


async def test_generation_rejects_blank_provider_key(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id = await create_ready_product(client)
    monkeypatch.setattr(script_routes.settings, "script_provider", "openai_compatible")
    monkeypatch.setattr(script_routes.settings, "provider_api_key", SecretStr(""))

    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "blank-provider-key-001"},
        json=await generation_payload(client, product_id),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "PROVIDER_MISCONFIGURED"


async def _queue_generation(
    client: AsyncClient,
    product_id: str,
    *,
    key: str,
    duration: int = 15,
    creative_pattern_key: str = "problem_solution",
    promotion_fact_id: str | None = None,
) -> dict[str, Any]:
    payload = await generation_payload(client, product_id, duration=duration)
    payload["creative_pattern_key"] = creative_pattern_key
    payload["promotion_fact_id"] = promotion_fact_id
    response = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": key},
        json=payload,
    )
    assert response.status_code == 202, response.json()
    return response.json()


def _worker_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


async def test_completed_script_can_be_viewed_compared_and_exported(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="script-export-001")
    generation_id = str(job["result_id"])
    version_id = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(job["id"])))
    assert version_id is not None

    job_response = await client.get(f"/api/v1/jobs/{job['id']}")
    script_response = await client.get(f"/api/v1/scripts/{generation_id}")
    json_export = await client.get(
        f"/api/v1/scripts/{generation_id}/versions/{version_id}/export?format=json"
    )
    markdown_export = await client.get(
        f"/api/v1/scripts/{generation_id}/versions/{version_id}/export?format=markdown"
    )

    assert job_response.json()["state"] == "succeeded"
    assert script_response.status_code == 200
    assert script_response.json()["versions"][0]["validation_report"]["acceptable"] is True
    assert json_export.status_code == 200
    assert json_export.json()["metadata"]["script_id"] == generation_id
    assert json_export.json()["metadata"]["selected_fact_ids"] == script_response.json()[
        "generation"
    ]["selected_fact_ids"]
    assert json_export.json()["metadata"]["excluded_fact_ids"] == []
    markdown = markdown_export.text
    headings = [
        "## Metadata",
        "## Validation summary",
        "## Phases",
        "## Shots",
        "## Titles",
        "## Tags",
        "## Shooting list",
    ]
    assert [markdown.index(heading) for heading in headings] == sorted(
        markdown.index(heading) for heading in headings
    )


async def test_storyboard_preflight_revalidates_and_exposes_frozen_fact_contract(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id, fact_ids = await create_ready_product_with_facts(
        client,
        ["First supported fact", "Second supported fact", "Excluded fact"],
    )
    queued = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "storyboard-preflight-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [fact_ids[1], fact_ids[0]],
            "excluded_fact_ids": [fact_ids[2]],
        },
    )
    assert queued.status_code == 202
    generation_id = str(queued.json()["result_id"])
    version_id = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(queued.json()["id"])))
    assert version_id is not None

    response = await client.get(
        f"/api/v1/scripts/{generation_id}/versions/{version_id}/storyboard-preflight"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert [item["id"] for item in body["selected_facts"]] == [fact_ids[1], fact_ids[0]]
    assert [item["id"] for item in body["excluded_facts"]] == [fact_ids[2]]
    assert all(
        set(shot["supported_fact_ids"]).issubset(set(fact_ids[:2]))
        for shot in body["shots"]
    )


async def test_storyboard_preflight_is_blocked_for_an_unacceptable_version(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="storyboard-preflight-blocked-001")
    generation_id = str(job["result_id"])
    version_id = await GenerationWorker(
        _worker_factory(db_session), BlockingProvider()
    ).run(UUID(str(job["id"])))
    assert version_id is not None

    response = await client.get(
        f"/api/v1/scripts/{generation_id}/versions/{version_id}/storyboard-preflight"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["validation_report"]["acceptable"] is False

    async with db_session.begin_nested():
        first = await db_session.get(ScriptVersionRecord, version_id)
        assert first is not None
        changed_draft = deepcopy(first.draft)
        changed_draft["titles"] = ["A changed title"]
        second = ScriptVersionRecord(
            id=uuid4(),
            generation_id=first.generation_id,
            parent_version_id=first.id,
            draft=changed_draft,
            validation_report=first.validation_report,
        )
        db_session.add(second)
        await db_session.flush()
        second_id = second.id

    comparison = await client.get(
        f"/api/v1/scripts/{generation_id}/compare?left={version_id}&right={second_id}"
    )
    assert comparison.status_code == 200
    assert comparison.json()["changed"] == [
        {"path": "titles[0]", "left": "Fact-led product script · General routine", "right": "A changed title"}
    ]


async def test_generation_requires_ready_facts_and_idempotent_input(client: AsyncClient) -> None:
    unready = await client.post(
        "/api/v1/products",
        json={"title": "Unready product", "facts": []},
    )
    unready_product_id = unready.json()["product_id"]
    blocked = await client.post(
        f"/api/v1/products/{unready_product_id}/script-generations",
        headers={"Idempotency-Key": "unready-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "FACTS_NOT_READY"

    ready_product_id = await create_ready_product(client)
    unsupported_duration = await client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        headers={"Idempotency-Key": "unsupported-duration-001"},
        json=await generation_payload(client, ready_product_id, duration=60),
    )
    assert unsupported_duration.status_code == 422
    assert unsupported_duration.json()["code"] == "DURATION_NOT_SUPPORTED"

    unsupported_language_payload = await generation_payload(client, ready_product_id)
    unsupported_language_payload["language"] = "fr"
    unsupported_language = await client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        headers={"Idempotency-Key": "unsupported-language-001"},
        json=unsupported_language_payload,
    )
    assert unsupported_language.status_code == 422
    assert unsupported_language.json()["code"] == "LANGUAGE_NOT_SUPPORTED"

    await _queue_generation(client, ready_product_id, key="conflict-001", duration=15)
    conflict = await client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        headers={"Idempotency-Key": "conflict-001"},
        json=await generation_payload(client, ready_product_id, duration=30),
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_creative_pattern_catalog_exposes_frozen_read_only_contracts(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/creative-patterns")

    assert response.status_code == 200
    catalog = response.json()
    assert len(catalog) == 7
    problem_solution = next(item for item in catalog if item["key"] == "problem_solution")
    assert problem_solution["version"] == "1.3"
    assert problem_solution["supported_languages"] == ["en", "zh-CN"]
    assert len(problem_solution["contracts"]) == 6
    contract = next(
        item
        for item in problem_solution["contracts"]
        if item["duration_seconds"] == 15 and item["language"] == "en"
    )
    assert contract["contract_version"] == "p1.3c"
    assert [phase["key"] for phase in contract["phases"]] == [
        "hook",
        "solution",
        "cta",
    ]
    assert [shot["phase_key"] for shot in contract["shots"]] == [
        "hook",
        "solution",
        "solution",
        "cta",
    ]
    assert [shot["budget_weight"] for shot in contract["shots"]] == [2, 4, 5, 4]
    assert contract["audience_policy"] == {
        "mode": "server_owned_profile",
        "allowed_slots": ["visual", "action", "acceptance_shot", "titles", "tags", "shooting_list"],
        "profile_key": "general",
    }
    assert contract["cta_policy"] == {"mode": "server_generic_no_offer"}


class BlockingProvider:
    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        fact = request.facts[0]
        return ScriptDraft(
            target_duration_seconds=request.target_duration_seconds,
            language=request.language,
            audience=request.audience,
            snapshot_id=request.snapshot_id,
            phases=[ScriptPhase(key="hook", purpose="Hook", start_seconds=0, end_seconds=15)],
            shots=[
                ScriptShot(
                    start_seconds=0,
                    end_seconds=15,
                    phase_key="hook",
                    voiceover="This guarantees results.",
                    visual="Show the product.",
                    action="Hold the product.",
                    caption="",
                    acceptance_shot="Product is visible.",
                    supported_fact_ids=[fact.id],
                    product_claims=[fact.claim],
                )
            ],
            titles=["Blocked draft"],
            tags=["blocked"],
            shooting_list=["product"],
        )


class FailingProvider:
    async def generate(self, _request: ScriptGenerationRequest) -> ScriptDraft:
        raise ProviderUnavailable("provider unavailable")


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        self.calls += 1
        return await DeterministicScriptProvider().generate(request)


class WrongContractProvider:
    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        fact = request.facts[0]
        return ScriptDraft(
            target_duration_seconds=60,
            language="zh-CN",
            audience="general",
            snapshot_id=uuid4(),
            phases=[ScriptPhase(key="hook", purpose="Hook", start_seconds=0, end_seconds=60)],
            shots=[
                ScriptShot(
                    start_seconds=0,
                    end_seconds=60,
                    phase_key="hook",
                    voiceover=fact.claim,
                    visual="Show the product",
                    action="Hold the product",
                    caption=fact.claim,
                    acceptance_shot="Product is visible",
                    supported_fact_ids=[fact.id],
                    product_claims=[fact.claim],
                )
            ],
            titles=["Fact-led script"],
            tags=["demo"],
            shooting_list=["product"],
        )


class RepairedProvider(DeterministicScriptProvider):
    last_attempt_count = 2


class RejectingFactProvider(DeterministicScriptProvider):
    def __init__(self, session: AsyncSession, fact_id: UUID) -> None:
        self.session = session
        self.fact_id = fact_id

    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        async with self.session.begin_nested():
            products = ProductRepository(self.session)
            fact = await products.get_fact(self.fact_id, for_update=True)
            assert fact is not None
            await products.save_fact(fact.transition_to(FactStatus.REJECTED))
        return await super().generate(request)


class RejectingPromotionProvider(DeterministicScriptProvider):
    def __init__(self, session: AsyncSession, promotion_fact_id: UUID) -> None:
        self.session = session
        self.promotion_fact_id = promotion_fact_id

    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        async with self.session.begin_nested():
            products = ProductRepository(self.session)
            promotion = await products.get_fact(self.promotion_fact_id, for_update=True)
            assert promotion is not None
            await products.save_fact(promotion.transition_to(FactStatus.REJECTED))
        return await super().generate(request)


class ControlledProvider(DeterministicScriptProvider):
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        self.started.set()
        await self.release.wait()
        if self.fail:
            raise ProviderUnavailable("controlled provider failure")
        return await super().generate(request)


class CapturingPatternProvider(DeterministicScriptProvider):
    def __init__(self) -> None:
        self.request: ScriptGenerationRequest | None = None

    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        self.request = request
        return await super().generate(request)


class ExcludedFactProvider(DeterministicScriptProvider):
    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        excluded = request.excluded_facts[0]
        draft = await super().generate(request)
        first = draft.shots[0].model_copy(
            update={
                "voiceover": excluded.claim,
                "caption": excluded.claim,
                "product_claims": [excluded.claim],
            }
        )
        return draft.model_copy(update={"shots": [first, *draft.shots[1:]]})


class TransientDatabaseProvider:
    async def generate(self, _request: ScriptGenerationRequest) -> ScriptDraft:
        raise SQLAlchemyError("database temporarily unavailable")


async def test_failed_generation_is_terminal_on_replay(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="failed-replay-001")
    factory = _worker_factory(db_session)

    first = await GenerationWorker(factory, FailingProvider()).run(UUID(str(job["id"])))
    counting = CountingProvider()
    replay = await GenerationWorker(factory, counting).run(UUID(str(job["id"])))

    assert first is None
    assert replay is None
    assert counting.calls == 0


async def test_only_celery_redelivery_can_resume_a_running_generation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    queued = await _queue_generation(client, product_id, key="running-redelivery-001")
    job_id = UUID(str(queued["id"]))
    async with db_session.begin_nested():
        repository = JobRepository(db_session)
        job = await repository.get(job_id, for_update=True)
        assert job is not None
        await repository.save(job.transition_to(JobState.GENERATING))

    factory = _worker_factory(db_session)
    duplicate_provider = CountingProvider()
    duplicate = await GenerationWorker(factory, duplicate_provider).run(job_id)
    redelivery_provider = CountingProvider()
    recovered = await GenerationWorker(factory, redelivery_provider).run(
        job_id, allow_retry=True
    )

    assert duplicate is None
    assert duplicate_provider.calls == 0
    assert recovered is not None
    assert redelivery_provider.calls == 1


async def test_celery_redelivery_can_resume_validating_generation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    queued = await _queue_generation(client, product_id, key="validating-redelivery-001")
    job_id = UUID(str(queued["id"]))
    async with db_session.begin_nested():
        repository = JobRepository(db_session)
        job = await repository.get(job_id, for_update=True)
        assert job is not None
        job = job.transition_to(JobState.GENERATING)
        await repository.save(job.transition_to(JobState.VALIDATING))

    provider = CountingProvider()
    recovered = await GenerationWorker(_worker_factory(db_session), provider).run(
        job_id, allow_retry=True
    )
    completed = await client.get(f"/api/v1/jobs/{job_id}")

    assert recovered is not None
    assert provider.calls == 1
    assert completed.json()["state"] == "succeeded"


async def test_redelivery_fences_stale_worker_terminal_write(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    queued = await _queue_generation(client, product_id, key="redelivery-fencing-001")
    job_id = UUID(str(queued["id"]))
    factory = _worker_factory(db_session)
    stale_provider = ControlledProvider(fail=True)
    current_provider = ControlledProvider()

    stale_run = asyncio.create_task(GenerationWorker(factory, stale_provider).run(job_id))
    await stale_provider.started.wait()
    current_run = asyncio.create_task(
        GenerationWorker(factory, current_provider).run(job_id, allow_retry=True)
    )
    await current_provider.started.wait()

    stale_provider.release.set()
    await stale_run
    during_redelivery = await client.get(f"/api/v1/jobs/{job_id}")
    current_provider.release.set()
    current_version_id = await current_run
    completed = await client.get(f"/api/v1/jobs/{job_id}")

    assert during_redelivery.json()["state"] == "generating"
    assert current_version_id is not None
    assert completed.json()["state"] == "succeeded"


async def test_transient_database_failure_keeps_job_retryable(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    queued = await _queue_generation(client, product_id, key="db-transient-retry-001")
    job_id = UUID(str(queued["id"]))
    factory = _worker_factory(db_session)

    with pytest.raises(SQLAlchemyError):
        await GenerationWorker(factory, TransientDatabaseProvider()).run(job_id)
    interrupted = await client.get(f"/api/v1/jobs/{job_id}")
    recovered = await GenerationWorker(
        factory, DeterministicScriptProvider()
    ).run(job_id, allow_retry=True)
    completed = await client.get(f"/api/v1/jobs/{job_id}")

    assert interrupted.json()["state"] == "generating"
    assert recovered is not None
    assert completed.json()["state"] == "succeeded"


async def test_worker_enforces_persisted_generation_contract(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="contract-binding-001")
    await GenerationWorker(_worker_factory(db_session), WrongContractProvider()).run(
        UUID(str(job["id"]))
    )

    script = await client.get(f"/api/v1/scripts/{job['result_id']}")
    stored = script.json()["versions"][0]

    assert stored["draft"]["target_duration_seconds"] == 15
    assert stored["draft"]["language"] == "en"
    assert stored["draft"]["audience"] == "General routine"
    assert stored["draft"]["snapshot_id"] == script.json()["generation"]["snapshot_id"]
    assert stored["validation_report"]["acceptable"] is False
    assert any(
        item["rule_id"] == "TIMELINE_END"
        for item in stored["validation_report"]["findings"]
    )


async def test_worker_passes_persisted_pattern_definition_to_provider(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="pattern-contract-001")
    provider = CapturingPatternProvider()

    await GenerationWorker(_worker_factory(db_session), provider).run(UUID(str(job["id"])))
    script = await client.get(f"/api/v1/scripts/{job['result_id']}")
    configuration = script.json()["generation"]["configuration"]

    definition = configuration["pattern_definition"]
    assert definition["contract_version"] == "p1.3c"
    assert definition["key"] == "problem_solution"
    assert definition["version"] == "1.3"
    assert definition["duration_seconds"] == 15
    assert [item["key"] for item in definition["phases"]] == [
        "hook",
        "solution",
        "cta",
    ]
    assert [item["phase_key"] for item in definition["shots"]] == [
        "hook",
        "solution",
        "solution",
        "cta",
    ]
    assert [item["role"] for item in definition["shots"]] == [
        "problem",
        "demo",
        "result",
        "cta",
    ]
    assert definition["audience_policy"] == {
        "mode": "server_owned_profile",
        "allowed_slots": ["visual", "action", "acceptance_shot", "titles", "tags", "shooting_list"],
        "profile_key": "general",
    }
    assert definition["cta_policy"] == {"mode": "server_generic_no_offer"}
    assert provider.request is not None
    assert provider.request.pattern_definition.contract_version == "p1.3c"
    assert provider.request.pattern_definition.phase_sequence == (
        "hook",
        "solution",
        "cta",
    )
    assert provider.request.pattern_definition.shot_roles == ("problem", "demo", "result", "cta")


async def test_worker_preserves_ordered_fact_selection_and_passes_deny_set(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id, fact_ids = await create_ready_product_with_facts(
        client,
        ["First selected fact", "Second selected fact", "Excluded fact"],
    )
    queued = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "worker-selection-contract-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [fact_ids[1], fact_ids[0]],
            "excluded_fact_ids": [fact_ids[2]],
        },
    )
    assert queued.status_code == 202
    provider = CapturingPatternProvider()

    version_id = await GenerationWorker(_worker_factory(db_session), provider).run(
        UUID(str(queued.json()["id"]))
    )

    assert version_id is not None
    assert provider.request is not None
    assert [str(fact.id) for fact in provider.request.facts] == [fact_ids[1], fact_ids[0]]
    assert [str(fact.id) for fact in provider.request.excluded_facts] == [fact_ids[2]]


async def test_fact_bound_rebind_rejects_blocked_parent_and_excluded_fact(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id, fact_ids = await create_ready_product_with_facts(
        client,
        ["Selected fact", "Excluded fact"],
    )
    queued = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "excluded-fact-contract-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [fact_ids[0]],
            "excluded_fact_ids": [fact_ids[1]],
        },
    )
    assert queued.status_code == 202
    job = queued.json()

    version_id = await GenerationWorker(
        _worker_factory(db_session), ExcludedFactProvider()
    ).run(UUID(str(job["id"])))
    assert version_id is not None
    blocked = await client.get(f"/api/v1/scripts/{job['result_id']}")
    assert blocked.json()["versions"][0]["validation_report"]["acceptable"] is False
    assert any(
        item["rule_id"] == "FACT_EXCLUDED"
        for item in blocked.json()["versions"][0]["validation_report"]["blocking"]
    )

    blocked_rebind = await client.post(
        f"/api/v1/scripts/{job['result_id']}/versions/{version_id}/derive",
        headers={"Idempotency-Key": "blocked-rebind-001"},
        json={
            "fact_bindings": [
                {"shot_index": 0, "fact_id": fact_ids[0]},
            ]
        },
    )
    assert blocked_rebind.status_code == 409
    assert blocked_rebind.json()["code"] == "SCRIPT_PARENT_NOT_ACCEPTABLE"

    clean_job = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "excluded-fact-derive-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": [fact_ids[0]],
            "excluded_fact_ids": [fact_ids[1]],
        },
    )
    assert clean_job.status_code == 202
    clean_version = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(clean_job.json()["id"])))
    assert clean_version is not None
    invalid_rebind = await client.post(
        f"/api/v1/scripts/{clean_job.json()['result_id']}/versions/{clean_version}/derive",
        headers={"Idempotency-Key": "excluded-fact-rebind-001"},
        json={
            "fact_bindings": [
                {"shot_index": index, "fact_id": fact_ids[1]}
                for index in range(4)
            ]
        },
    )

    assert invalid_rebind.status_code == 422
    assert invalid_rebind.json()["code"] == "SCRIPT_EDIT_INVALID"
    script = await client.get(f"/api/v1/scripts/{clean_job.json()['result_id']}")
    assert len(script.json()["versions"]) == 1


async def test_worker_records_provider_format_repair_attempt(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="provider-repair-attempt-001")
    await GenerationWorker(_worker_factory(db_session), RepairedProvider()).run(
        UUID(str(job["id"]))
    )

    stored = await client.get(f"/api/v1/jobs/{job['id']}")

    assert stored.json()["attempt_count"] == 2


async def test_worker_reloads_fact_status_when_saving_result(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client, lock_fact=False)
    product = await client.get(f"/api/v1/products/{product_id}")
    fact_id = UUID(product.json()["facts"][0]["id"])
    job = await _queue_generation(client, product_id, key="fact-status-toctou-001")

    version_id = await GenerationWorker(
        _worker_factory(db_session), RejectingFactProvider(db_session, fact_id)
    ).run(UUID(str(job["id"])))

    assert version_id is not None
    stored_job = await client.get(f"/api/v1/jobs/{job['id']}")
    script = await client.get(f"/api/v1/scripts/{job['result_id']}")
    findings = script.json()["versions"][0]["validation_report"]["findings"]
    assert stored_job.json()["state"] == "validation_failed"
    assert any(item["rule_id"] == "FACT_UNCONFIRMED" for item in findings)


async def test_worker_rechecks_fact_status_before_calling_provider(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client, lock_fact=False)
    product = await client.get(f"/api/v1/products/{product_id}")
    fact_id = product.json()["facts"][0]["id"]
    job = await _queue_generation(client, product_id, key="fact-preflight-001")
    rejected = await client.patch(
        f"/api/v1/products/{product_id}/facts/{fact_id}",
        json={"status": "rejected"},
    )
    assert rejected.status_code == 200
    provider = CountingProvider()

    result = await GenerationWorker(_worker_factory(db_session), provider).run(
        UUID(str(job["id"]))
    )
    stored_job = await client.get(f"/api/v1/jobs/{job['id']}")

    assert result is None
    assert provider.calls == 0
    assert stored_job.json()["state"] == "failed"
    assert stored_job.json()["error_code"] == "FACTS_NOT_READY"


async def test_worker_rechecks_promotion_before_calling_provider(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    promotion_fact_id = await create_confirmed_promotion_fact(client, product_id)
    job = await _queue_generation(
        client,
        product_id,
        key="promotion-preflight-001",
        creative_pattern_key="offer_cta",
        promotion_fact_id=promotion_fact_id,
    )
    rejected = await client.patch(
        f"/api/v1/products/{product_id}/facts/{promotion_fact_id}",
        json={"status": "rejected"},
    )
    assert rejected.status_code == 200
    provider = CountingProvider()

    result = await GenerationWorker(_worker_factory(db_session), provider).run(
        UUID(str(job["id"]))
    )
    stored_job = await client.get(f"/api/v1/jobs/{job['id']}")
    script = await client.get(f"/api/v1/scripts/{job['result_id']}")

    assert result is None
    assert provider.calls == 0
    assert stored_job.json()["state"] == "failed"
    assert stored_job.json()["error_code"] == "PROMOTION_NOT_ACTIVE"
    assert script.json()["versions"] == []


async def test_worker_rechecks_promotion_before_saving_result(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    promotion_fact_id = await create_confirmed_promotion_fact(client, product_id)
    job = await _queue_generation(
        client,
        product_id,
        key="promotion-save-toctou-001",
        creative_pattern_key="offer_cta",
        promotion_fact_id=promotion_fact_id,
    )

    result = await GenerationWorker(
        _worker_factory(db_session),
        RejectingPromotionProvider(db_session, UUID(promotion_fact_id)),
    ).run(UUID(str(job["id"])))
    stored_job = await client.get(f"/api/v1/jobs/{job['id']}")
    script = await client.get(f"/api/v1/scripts/{job['result_id']}")

    assert result is None
    assert stored_job.json()["state"] == "failed"
    assert stored_job.json()["error_code"] == "PROMOTION_NOT_ACTIVE"
    assert script.json()["versions"] == []


async def test_validation_failed_version_remains_viewable(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="validation-failed-001")
    version_id = await GenerationWorker(_worker_factory(db_session), BlockingProvider()).run(
        UUID(str(job["id"]))
    )
    assert version_id is not None

    job_response = await client.get(f"/api/v1/jobs/{job['id']}")
    script_response = await client.get(f"/api/v1/scripts/{job['result_id']}")

    assert job_response.json()["state"] == "validation_failed"
    assert script_response.status_code == 200
    assert script_response.json()["versions"][0]["validation_report"]["acceptable"] is False


async def test_fact_bound_rebind_appends_an_idempotent_acceptable_child(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id, fact_ids = await create_ready_product_with_facts(
        client,
        ["First selected fact", "Second selected fact"],
    )
    queued = await client.post(
        f"/api/v1/products/{product_id}/script-generations",
        headers={"Idempotency-Key": "derive-001"},
        json={
            "target_duration_seconds": 15,
            "language": "en",
            "audience": "general",
            "creative_pattern_key": "problem_solution",
            "selected_fact_ids": fact_ids,
            "excluded_fact_ids": [],
        },
    )
    assert queued.status_code == 202
    job = queued.json()
    first_version_id = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(job["id"])))
    assert first_version_id is not None

    extra_field = await client.post(
        f"/api/v1/scripts/{job['result_id']}/versions/{first_version_id}/derive",
        headers={"Idempotency-Key": "fact-rebind-extra-field-001"},
        json={
            "fact_bindings": [{"shot_index": index, "fact_id": fact_ids[1]} for index in range(4)],
            "title": "Client-controlled copy is not allowed",
        },
    )
    assert extra_field.status_code == 422

    incomplete = await client.post(
        f"/api/v1/scripts/{job['result_id']}/versions/{first_version_id}/derive",
        headers={"Idempotency-Key": "fact-rebind-incomplete-001"},
        json={
            "fact_bindings": [{"shot_index": index, "fact_id": fact_ids[1]} for index in range(3)]
        },
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["code"] == "SCRIPT_EDIT_INVALID"

    payload = {
        "fact_bindings": [
            {"shot_index": index, "fact_id": fact_ids[1]}
            for index in range(4)
        ]
    }
    headers = {"Idempotency-Key": "fact-rebind-001"}
    derived = await client.post(
        f"/api/v1/scripts/{job['result_id']}/versions/{first_version_id}/derive",
        headers=headers,
        json=payload,
    )

    assert derived.status_code == 201
    assert derived.json()["parent_version_id"] == str(first_version_id)
    assert derived.json()["revision_kind"] == "fact_rebind"
    assert derived.json()["actor_kind"] == "local_operator"
    assert derived.json()["reason_code"] == "fact_rebind"
    assert all(
        shot["voiceover"] == "Second selected fact"
        and shot["caption"] == "Second selected fact"
        and shot["product_claims"] == ["Second selected fact"]
        and shot["supported_fact_ids"] == [fact_ids[1]]
        for shot in derived.json()["draft"]["shots"]
    )
    assert derived.json()["validation_report"]["acceptable"] is True

    replay = await client.post(
        f"/api/v1/scripts/{job['result_id']}/versions/{first_version_id}/derive",
        headers=headers,
        json=payload,
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == derived.json()["id"]

    conflict = await client.post(
        f"/api/v1/scripts/{job['result_id']}/versions/{first_version_id}/derive",
        headers=headers,
        json={
            "fact_bindings": [
                {"shot_index": index, "fact_id": fact_ids[0]}
                for index in range(4)
            ]
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

    script = await client.get(f"/api/v1/scripts/{job['result_id']}")
    assert [item["id"] for item in script.json()["fact_contract"]["selected"]] == fact_ids
    assert [item["status"] for item in script.json()["fact_contract"]["selected"]] == [
        "confirmed",
        "confirmed",
    ]
    assert len(script.json()["versions"]) == 2
    comparison = await client.get(
        f"/api/v1/scripts/{job['result_id']}/compare?left={first_version_id}"
        f"&right={derived.json()['id']}"
    )
    assert {item["path"] for item in comparison.json()["changed"]} >= {
        "shots[0].caption",
        "shots[0].product_claims[0]",
        "shots[0].supported_fact_ids[0]",
        "shots[0].voiceover",
    }

    parent = await db_session.get(ScriptVersionRecord, first_version_id)
    assert parent is not None
    malformed = ScriptVersionRecord(
        id=uuid4(),
        generation_id=parent.generation_id,
        parent_version_id=first_version_id,
        draft=parent.draft,
        validation_report=parent.validation_report,
        revision_kind="fact_rebind",
        actor_kind="local_operator",
        reason_code=None,
        operation_key="malformed-provenance-001",
        operation_input_digest="a" * 64,
    )
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(malformed)
            await db_session.flush()


async def test_script_version_is_database_immutable(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    product_id = await create_ready_product(client)
    job = await _queue_generation(client, product_id, key="immutable-version-001")
    version_id = await GenerationWorker(
        _worker_factory(db_session), DeterministicScriptProvider()
    ).run(UUID(str(job["id"])))
    assert version_id is not None

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                update(ScriptVersionRecord)
                .where(ScriptVersionRecord.id == version_id)
                .values(draft={})
            )
