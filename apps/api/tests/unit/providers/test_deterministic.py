from uuid import UUID

import pytest

from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.domain.scripts.patterns import compile_pattern
from app.ports.script_provider import ScriptGenerationRequest, SupportedFact


@pytest.mark.parametrize("duration", [15, 30, 45])
async def test_deterministic_provider_returns_same_script_for_same_request(
    duration: int,
) -> None:
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
        target_duration_seconds=duration,
        language="en",
        audience="busy professionals",
        pattern_definition=compile_pattern(
            "problem_solution", duration_seconds=duration, language="en"
        ),
    )

    first = await provider.generate(request)
    second = await provider.generate(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.shots[0].supported_fact_ids == [request.facts[0].id]
    assert [phase.key for phase in first.phases] == list(request.pattern_definition.phase_sequence)
    assert [shot.phase_key for shot in first.shots] == [
        definition.phase_key for definition in request.pattern_definition.shots
    ]
    assert [shot.role for shot in first.shots] == list(
        request.pattern_definition.shot_roles
    )
    assert first.shots[0].start_seconds == 0
    assert first.shots[-1].end_seconds == pytest.approx(duration)
