import json
from uuid import UUID

import httpx
import pytest

from app.adapters.providers.openai_compatible import OpenAICompatibleScriptProvider
from app.domain.scripts.models import ScriptDraft, ScriptPhase, ScriptShot
from app.ports.script_provider import (
    ProviderOutputInvalid,
    ProviderRateLimited,
    ProviderUnavailable,
    ScriptGenerationRequest,
    SupportedFact,
)

SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000020")
FACT_ID = UUID("00000000-0000-0000-0000-000000000021")


def _request() -> ScriptGenerationRequest:
    return ScriptGenerationRequest(
        snapshot_id=SNAPSHOT_ID,
        title="Pulse Mix",
        facts=[SupportedFact(id=FACT_ID, claim="The pouch is resealable", claim_type="feature")],
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        creative_pattern_key="problem_solution",
        creative_pattern_version="1.0",
        hook_type="pain",
        phase_sequence=("hook", "problem", "solution", "cta"),
        shot_roles=("problem", "demo", "result", "cta"),
    )


def _draft() -> ScriptDraft:
    return ScriptDraft(
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        snapshot_id=SNAPSHOT_ID,
        phases=[ScriptPhase(key="demo", purpose="Demo", start_seconds=0, end_seconds=15)],
        shots=[
            ScriptShot(
                start_seconds=0,
                end_seconds=15,
                phase_key="demo",
                voiceover="The pouch is resealable.",
                visual="Show the pouch.",
                action="Reseal the pouch.",
                caption="Resealable",
                acceptance_shot="The closed seal is visible.",
                supported_fact_ids=[FACT_ID],
                product_claims=["The pouch is resealable"],
            )
        ],
        titles=["A practical pouch"],
        tags=["demo"],
        shooting_list=["pouch"],
    )


def _provider(transport: httpx.AsyncBaseTransport) -> OpenAICompatibleScriptProvider:
    return OpenAICompatibleScriptProvider(
        client=httpx.AsyncClient(transport=transport),
        base_url="https://provider.example/v1",
        model="script-model",
        api_key="test-secret",
    )


async def test_openai_compatible_provider_parses_structured_draft() -> None:
    captured_schema: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        captured_schema.update(payload["response_format"]["json_schema"]["schema"])
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(_draft().model_dump(mode="json"))}}
                ]
            },
        )

    provider = _provider(httpx.MockTransport(handler))

    result = await provider.generate(_request())

    assert result == _draft()

    def assert_strict_objects(value: object) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                assert value.get("additionalProperties") is False
                assert set(value.get("required", [])) == set(properties)
            for item in value.values():
                assert_strict_objects(item)
        elif isinstance(value, list):
            for item in value:
                assert_strict_objects(item)

    assert_strict_objects(captured_schema)


async def test_openai_compatible_provider_maps_rate_limit() -> None:
    provider = _provider(httpx.MockTransport(lambda _request: httpx.Response(429)))

    with pytest.raises(ProviderRateLimited):
        await provider.generate(_request())


async def test_openai_compatible_provider_maps_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    provider = _provider(httpx.MockTransport(handler))

    with pytest.raises(ProviderUnavailable):
        await provider.generate(_request())


async def test_openai_compatible_provider_rejects_invalid_output_after_repair() -> None:
    provider = _provider(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"choices": [{"message": {"content": "not-json"}}]},
            )
        )
    )

    with pytest.raises(ProviderOutputInvalid) as failure:
        await provider.generate(_request())

    assert failure.value.attempt_count == 2


async def test_openai_compatible_provider_records_successful_format_repair() -> None:
    responses = iter(["not-json", json.dumps(_draft().model_dump(mode="json"))])
    provider = _provider(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"choices": [{"message": {"content": next(responses)}}]},
            )
        )
    )

    result = await provider.generate(_request())

    assert result == _draft()
    assert provider.last_attempt_count == 2
