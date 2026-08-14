from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.common.canonical import canonical_digest
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.scripts.models import (
    ScriptDraft,
    ScriptPhase,
    ScriptShot,
    ValidationReport,
)


class StoryboardFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    claim_type: str
    claim: str
    evidence_kind: str
    evidence_excerpt: str
    status: FactStatus

    @classmethod
    def from_fact(cls, fact: ProductFact) -> "StoryboardFact":
        return cls(
            id=fact.id,
            claim_type=fact.claim_type,
            claim=fact.claim,
            evidence_kind=fact.evidence_kind,
            evidence_excerpt=fact.evidence_excerpt,
            status=fact.status,
        )


class StoryboardPreflight(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "blocked"]
    script_id: UUID
    version_id: UUID
    snapshot_id: UUID
    pattern_key: str
    input_digest: str
    selected_facts: list[StoryboardFact]
    excluded_facts: list[StoryboardFact]
    phases: list[ScriptPhase]
    shots: list[ScriptShot]
    validation_report: ValidationReport


class StoryboardPreviewShot(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    start_seconds: float
    end_seconds: float
    phase_key: str
    voiceover: str
    caption: str
    visual: str
    action: str
    acceptance_shot: str
    supported_fact_ids: list[UUID]


class StoryboardPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    storyboard_id: UUID
    storyboard_digest: str
    preview_digest: str
    preview_contract_version: str
    image_indexes: list[int]
    shots: list[StoryboardPreviewShot]


def compile_storyboard_preflight(
    *,
    script_id: UUID,
    version_id: UUID,
    input_digest: str,
    pattern_key: str,
    snapshot_id: UUID,
    selected_facts: Sequence[ProductFact],
    excluded_facts: Sequence[ProductFact],
    draft: ScriptDraft,
    validation_report: ValidationReport,
) -> StoryboardPreflight:
    """Project an already validated script into a read-only render preflight.

    This is intentionally not a render job or a persistent storyboard version.
    It preserves the fact contract and existing typed script fields exactly.
    """

    return StoryboardPreflight(
        status="ready" if validation_report.acceptable else "blocked",
        script_id=script_id,
        version_id=version_id,
        snapshot_id=snapshot_id,
        pattern_key=pattern_key,
        input_digest=input_digest,
        selected_facts=[StoryboardFact.from_fact(item) for item in selected_facts],
        excluded_facts=[StoryboardFact.from_fact(item) for item in excluded_facts],
        phases=draft.phases,
        shots=draft.shots,
        validation_report=validation_report,
    )


def storyboard_preflight_digest(
    preflight: StoryboardPreflight,
    *,
    pattern_version: str,
    phase_sequence: Sequence[str],
) -> str:
    return canonical_digest(
        {
            "script_version_id": preflight.version_id,
            "snapshot_id": preflight.snapshot_id,
            "input_digest": preflight.input_digest,
            "pattern_key": preflight.pattern_key,
            "pattern_version": pattern_version,
            "phase_sequence": list(phase_sequence),
            "selected_facts": [item.model_dump(mode="json") for item in preflight.selected_facts],
            "excluded_facts": [item.model_dump(mode="json") for item in preflight.excluded_facts],
            "phases": [item.model_dump(mode="json") for item in preflight.phases],
            "shots": [item.model_dump(mode="json") for item in preflight.shots],
            "validation_report": preflight.validation_report.model_dump(mode="json"),
        }
    )


def storyboard_digest(
    *,
    preflight: StoryboardPreflight,
    preflight_digest: str,
    pattern_version: str,
    phase_sequence: Sequence[str],
) -> str:
    return canonical_digest(
        {
            "script_id": preflight.script_id,
            "version_id": preflight.version_id,
            "preflight_digest": preflight_digest,
            "pattern_version": pattern_version,
            "phase_sequence": list(phase_sequence),
            "preview_contract_version": "p2.0-animatic-v1",
        }
    )


def compile_storyboard_preview(
    *,
    storyboard_id: UUID,
    storyboard_digest: str,
    phases: Sequence[ScriptPhase],
    shots: Sequence[ScriptShot],
    image_count: int,
) -> StoryboardPreview:
    preview_shots = [
        StoryboardPreviewShot(
            index=index,
            start_seconds=shot.start_seconds,
            end_seconds=shot.end_seconds,
            phase_key=shot.phase_key,
            voiceover=shot.voiceover,
            caption=shot.caption,
            visual=shot.visual,
            action=shot.action,
            acceptance_shot=shot.acceptance_shot,
            supported_fact_ids=shot.supported_fact_ids,
        )
        for index, shot in enumerate(shots, start=1)
    ]
    preview_digest = canonical_digest(
        {
            "storyboard_digest": storyboard_digest,
            "preview_contract_version": "p2.0-animatic-v1",
            "phases": [item.model_dump(mode="json") for item in phases],
            "shots": [item.model_dump(mode="json") for item in preview_shots],
            "image_indexes": list(range(image_count)),
        }
    )
    return StoryboardPreview(
        storyboard_id=storyboard_id,
        storyboard_digest=storyboard_digest,
        preview_digest=preview_digest,
        preview_contract_version="p2.0-animatic-v1",
        image_indexes=list(range(image_count)),
        shots=preview_shots,
    )
