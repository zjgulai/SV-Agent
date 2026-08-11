from uuid import UUID

from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.ports.script_provider import ScriptGenerationRequest, SupportedFact


async def test_deterministic_provider_returns_same_script_for_same_request() -> None:
    provider = DeterministicScriptProvider()
    request = ScriptGenerationRequest(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000020"),
        title="Pulse Mix",
        facts=[
            SupportedFact(
                id=UUID("00000000-0000-0000-0000-000000000021"),
                claim="The pouch is resealable",
                claim_type="feature",
            )
        ],
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        creative_pattern_key="problem_solution",
        creative_pattern_version="1.0",
        hook_type="pain",
        phase_sequence=("hook", "problem", "solution", "cta"),
        shot_roles=("problem", "demo", "result", "cta"),
    )

    first = await provider.generate(request)
    second = await provider.generate(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.shots[0].supported_fact_ids == [request.facts[0].id]
