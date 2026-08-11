import re

from app.domain.scripts.models import ScriptDraft
from app.domain.scripts.patterns import CREATIVE_PATTERNS

SAFE_VISUAL = "Show the product clearly."
SAFE_ACTION = "Demonstrate the referenced product fact."
SAFE_ACCEPTANCE_SHOT = "The product and action are clearly visible."
SAFE_TITLE = "Fact-led product script"
SAFE_TAG = "product-demo"
SAFE_SHOOTING_LIST: tuple[str, ...] = (
    "product",
    "clean background",
    "close-up detail",
)
SAFE_PATTERN_KEYS = frozenset(item.key for item in CREATIVE_PATTERNS)
SAFE_PHASE_KEYS = frozenset(
    phase_key for pattern in CREATIVE_PATTERNS for phase_key in pattern.phase_sequence
)
SAFE_TITLE_PATTERN = re.compile(rf"^{re.escape(SAFE_TITLE)}(?: · Version [1-9][0-9]*)?$")
UNTRUSTED_PHASE_KEY = "__untrusted__"


def safe_phase_purpose(phase_key: str) -> str:
    return phase_key.replace("_", " ").title()


def enforce_creative_contract(
    draft: ScriptDraft,
    *,
    pattern_key: str,
    phase_sequence: tuple[str, ...],
) -> ScriptDraft:
    """Replace provider-controlled non-claim copy with server-owned safe templates."""
    if not pattern_key.strip() or not phase_sequence:
        raise ValueError(f"unknown creative pattern: {pattern_key}")

    phase_mapping: dict[str, str] = {}
    phases = []
    for index, phase in enumerate(draft.phases):
        safe_key = (
            phase_sequence[index]
            if index < len(phase_sequence)
            else UNTRUSTED_PHASE_KEY
        )
        phase_mapping.setdefault(phase.key, safe_key)
        phases.append(
            phase.model_copy(
                update={"key": safe_key, "purpose": safe_phase_purpose(safe_key)}
            )
        )

    shots = [
        shot.model_copy(
            update={
                "phase_key": phase_mapping.get(shot.phase_key, UNTRUSTED_PHASE_KEY),
                "visual": SAFE_VISUAL,
                "action": SAFE_ACTION,
                "acceptance_shot": SAFE_ACCEPTANCE_SHOT,
            }
        )
        for shot in draft.shots
    ]
    return draft.model_copy(
        update={
            "phases": phases,
            "shots": shots,
            "titles": [SAFE_TITLE],
            "tags": [pattern_key, SAFE_TAG],
            "shooting_list": list(SAFE_SHOOTING_LIST),
        }
    )
