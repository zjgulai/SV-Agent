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
        pattern = request.pattern_definition
        if not pattern.shots:
            raise ValueError(f"unknown creative pattern: {pattern.key}")

        duration = request.target_duration_seconds
        phases: list[ScriptPhase] = []
        shots: list[ScriptShot] = []
        total_weight = sum(shot.budget_weight for shot in pattern.shots)
        timed_shots: list[tuple[float, float]] = []
        elapsed = 0.0
        for index, shot_definition in enumerate(pattern.shots):
            start = elapsed
            end = elapsed + duration * shot_definition.budget_weight / total_weight
            elapsed = end
            timed_shots.append((start, end))
            fact = request.facts[index % len(request.facts)]
            shots.append(
                ScriptShot(
                    start_seconds=start,
                    end_seconds=end,
                    phase_key=shot_definition.phase_key,
                    role=shot_definition.role,
                    voiceover=fact.claim,
                    visual=SAFE_VISUAL,
                    action=SAFE_ACTION,
                    caption=fact.claim,
                    acceptance_shot=SAFE_ACCEPTANCE_SHOT,
                    supported_fact_ids=[fact.id],
                    product_claims=[fact.claim],
                )
            )

        for phase_definition in pattern.phases:
            phase_windows = [
                window
                for shot_definition, window in zip(pattern.shots, timed_shots)
                if shot_definition.phase_key == phase_definition.key
            ]
            if not phase_windows:
                raise ValueError(
                    f"pattern phase has no shots: {phase_definition.key}"
                )
            phases.append(
                ScriptPhase(
                    key=phase_definition.key,
                    purpose=phase_definition.purpose,
                    start_seconds=phase_windows[0][0],
                    end_seconds=phase_windows[-1][1],
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
            tags=[pattern.key, SAFE_TAG],
            shooting_list=list(SAFE_SHOOTING_LIST),
        )
