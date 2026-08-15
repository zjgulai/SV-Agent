import re

from app.domain.products.promotion import PromotionRender
from app.domain.scripts.models import ScriptDraft
from app.domain.scripts.patterns import (
    CREATIVE_PATTERNS,
    DEFAULT_SERVER_OWNED_COPY,
    CompiledPatternDefinition,
)

SAFE_VISUAL = DEFAULT_SERVER_OWNED_COPY.visual
SAFE_ACTION = DEFAULT_SERVER_OWNED_COPY.action
SAFE_ACCEPTANCE_SHOT = DEFAULT_SERVER_OWNED_COPY.acceptance_shot
SAFE_TITLE = DEFAULT_SERVER_OWNED_COPY.title
SAFE_TAG = DEFAULT_SERVER_OWNED_COPY.tag_suffix
SAFE_SHOOTING_LIST = DEFAULT_SERVER_OWNED_COPY.shooting_list
SAFE_PATTERN_KEYS = frozenset(item.key for item in CREATIVE_PATTERNS)
SAFE_PHASE_KEYS = frozenset(
    phase_key for pattern in CREATIVE_PATTERNS for phase_key in pattern.all_phase_keys
)
SAFE_TITLE_PATTERN = re.compile(rf"^{re.escape(SAFE_TITLE)}(?: · Version [1-9][0-9]*)?$")
UNTRUSTED_PHASE_KEY = "__untrusted__"
UNTRUSTED_SHOT_ROLE = "__untrusted__"


def safe_phase_purpose(phase_key: str) -> str:
    return phase_key.replace("_", " ").title()


def enforce_creative_contract(
    draft: ScriptDraft,
    *,
    pattern: CompiledPatternDefinition,
    promotion: PromotionRender | None = None,
) -> ScriptDraft:
    """Replace provider-controlled non-claim copy using the frozen pattern contract."""
    phases = []
    for index, phase in enumerate(draft.phases):
        definition = pattern.phases[index] if index < len(pattern.phases) else None
        phases.append(
            phase.model_copy(
                update={
                    "key": definition.key if definition else UNTRUSTED_PHASE_KEY,
                    "purpose": definition.purpose if definition else UNTRUSTED_PHASE_KEY,
                }
            )
        )

    copy = pattern.server_owned_copy
    shots = []
    final_cta_index = len(pattern.shots) - 1
    for index, shot in enumerate(draft.shots):
        shot_definition = pattern.shots[index] if index < len(pattern.shots) else None
        shots.append(
            shot.model_copy(
                update={
                    "phase_key": (
                        shot_definition.phase_key
                        if shot_definition
                        else UNTRUSTED_PHASE_KEY
                    ),
                    "role": (
                        shot_definition.role
                        if shot_definition
                        else UNTRUSTED_SHOT_ROLE
                    ),
                    "visual": copy.visual,
                    "action": copy.action,
                    "acceptance_shot": copy.acceptance_shot,
                    "promotion": (
                        promotion
                        if promotion is not None
                        and pattern.cta_policy.mode == "server_promotion_final_cta"
                        and index == final_cta_index
                        and shot_definition is not None
                        and shot_definition.role == "cta"
                        else None
                    ),
                }
            )
        )
    return draft.model_copy(
        update={
            "phases": phases,
            "shots": shots,
            "titles": [copy.title],
            "tags": [pattern.key, copy.tag_suffix],
            "shooting_list": list(copy.shooting_list),
        }
    )
