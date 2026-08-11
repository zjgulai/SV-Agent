from app.domain.scripts.creative_contract import (
    SAFE_ACCEPTANCE_SHOT,
    SAFE_ACTION,
    SAFE_SHOOTING_LIST,
    SAFE_TAG,
    SAFE_TITLE,
    SAFE_VISUAL,
)
from app.domain.scripts.models import ScriptDraft, ScriptPhase, ScriptShot
from app.ports.script_provider import ScriptGenerationRequest


class DeterministicScriptProvider:
    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft:
        if not request.phase_sequence:
            raise ValueError(f"unknown creative pattern: {request.creative_pattern_key}")

        phase_keys = request.phase_sequence
        duration = request.target_duration_seconds
        phases: list[ScriptPhase] = []
        shots: list[ScriptShot] = []
        for index, phase_key in enumerate(phase_keys):
            start = duration * index / len(phase_keys)
            end = duration * (index + 1) / len(phase_keys)
            fact = request.facts[index % len(request.facts)]
            phases.append(
                ScriptPhase(
                    key=phase_key,
                    purpose=phase_key.replace("_", " ").title(),
                    start_seconds=start,
                    end_seconds=end,
                )
            )
            shots.append(
                ScriptShot(
                    start_seconds=start,
                    end_seconds=end,
                    phase_key=phase_key,
                    voiceover=fact.claim,
                    visual=SAFE_VISUAL,
                    action=SAFE_ACTION,
                    caption=fact.claim,
                    acceptance_shot=SAFE_ACCEPTANCE_SHOT,
                    supported_fact_ids=[fact.id],
                    product_claims=[fact.claim],
                )
            )

        return ScriptDraft(
            target_duration_seconds=duration,
            language=request.language,
            audience=request.audience,
            snapshot_id=request.snapshot_id,
            phases=phases,
            shots=shots,
            titles=[SAFE_TITLE],
            tags=[request.creative_pattern_key, SAFE_TAG],
            shooting_list=list(SAFE_SHOOTING_LIST),
        )
