from uuid import UUID

from app.domain.products.entities import FactStatus, ProductFact
from app.domain.scripts.creative_contract import (
    SAFE_ACCEPTANCE_SHOT,
    SAFE_ACTION,
    SAFE_SHOOTING_LIST,
    SAFE_TAG,
    SAFE_TITLE,
    SAFE_VISUAL,
)
from app.domain.scripts.models import ScriptDraft, ScriptPhase, ScriptShot
from app.domain.scripts.storyboard import (
    compile_storyboard_preflight,
    compile_storyboard_preview,
    storyboard_preflight_digest,
)
from app.domain.scripts.validation import validate_script

FIRST_FACT_ID = UUID("00000000-0000-0000-0000-000000000101")
SECOND_FACT_ID = UUID("00000000-0000-0000-0000-000000000102")
EXCLUDED_FACT_ID = UUID("00000000-0000-0000-0000-000000000103")
SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000120")
SCRIPT_ID = UUID("00000000-0000-0000-0000-000000000130")
VERSION_ID = UUID("00000000-0000-0000-0000-000000000140")


def _fact(identifier: UUID, claim: str) -> ProductFact:
    return ProductFact.create(
        id=identifier,
        snapshot_id=SNAPSHOT_ID,
        claim_type="feature",
        claim=claim,
        value={"claim": claim},
        evidence_kind="source_field",
        evidence_locator="product.feature",
        evidence_excerpt=claim,
        confidence=1,
        status=FactStatus.CONFIRMED,
    )


def _draft(voiceover: str = "Second fact") -> ScriptDraft:
    return ScriptDraft(
        target_duration_seconds=15,
        language="en",
        audience="buyers",
        snapshot_id=SNAPSHOT_ID,
        phases=[ScriptPhase(key="demo", purpose="Demo", start_seconds=0, end_seconds=15)],
        shots=[
            ScriptShot(
                start_seconds=0,
                end_seconds=15,
                phase_key="demo",
                voiceover=voiceover,
                visual=SAFE_VISUAL,
                action=SAFE_ACTION,
                caption=voiceover,
                acceptance_shot=SAFE_ACCEPTANCE_SHOT,
                supported_fact_ids=[SECOND_FACT_ID],
                product_claims=[voiceover],
            )
        ],
        titles=[SAFE_TITLE],
        tags=[SAFE_TAG],
        shooting_list=list(SAFE_SHOOTING_LIST),
    )


def test_storyboard_preflight_preserves_frozen_fact_order_and_shot_bindings() -> None:
    first = _fact(FIRST_FACT_ID, "First fact")
    second = _fact(SECOND_FACT_ID, "Second fact")
    excluded = _fact(EXCLUDED_FACT_ID, "Excluded fact")
    draft = _draft()
    report = validate_script(
        draft,
        {FIRST_FACT_ID: first, SECOND_FACT_ID: second},
        excluded_facts={EXCLUDED_FACT_ID: excluded},
        creative_pattern_key="demo_first",
        phase_sequence=("demo",),
    )

    preflight = compile_storyboard_preflight(
        script_id=SCRIPT_ID,
        version_id=VERSION_ID,
        input_digest="a" * 64,
        pattern_key="demo_first",
        snapshot_id=SNAPSHOT_ID,
        selected_facts=[second, first],
        excluded_facts=[excluded],
        draft=draft,
        validation_report=report,
    )

    assert preflight.status == "ready"
    assert [fact.id for fact in preflight.selected_facts] == [SECOND_FACT_ID, FIRST_FACT_ID]
    assert [fact.claim for fact in preflight.excluded_facts] == ["Excluded fact"]
    assert preflight.shots[0].supported_fact_ids == [SECOND_FACT_ID]


def test_storyboard_preflight_is_blocked_when_an_excluded_fact_is_visible() -> None:
    selected = _fact(SECOND_FACT_ID, "Second fact")
    excluded = _fact(EXCLUDED_FACT_ID, "Excluded fact")
    draft = _draft(excluded.claim)
    report = validate_script(
        draft,
        {SECOND_FACT_ID: selected},
        excluded_facts={EXCLUDED_FACT_ID: excluded},
        creative_pattern_key="demo_first",
        phase_sequence=("demo",),
    )

    preflight = compile_storyboard_preflight(
        script_id=SCRIPT_ID,
        version_id=VERSION_ID,
        input_digest="a" * 64,
        pattern_key="demo_first",
        snapshot_id=SNAPSHOT_ID,
        selected_facts=[selected],
        excluded_facts=[excluded],
        draft=draft,
        validation_report=report,
    )

    assert preflight.status == "blocked"
    assert {item.rule_id for item in preflight.validation_report.blocking} >= {"FACT_EXCLUDED"}


def test_storyboard_digest_and_preview_preserve_contract_not_image_urls() -> None:
    selected = _fact(SECOND_FACT_ID, "Second fact")
    draft = _draft()
    report = validate_script(
        draft,
        {SECOND_FACT_ID: selected},
        creative_pattern_key="demo_first",
        phase_sequence=("demo",),
    )
    preflight = compile_storyboard_preflight(
        script_id=SCRIPT_ID,
        version_id=VERSION_ID,
        input_digest="a" * 64,
        pattern_key="demo_first",
        snapshot_id=SNAPSHOT_ID,
        selected_facts=[selected],
        excluded_facts=[],
        draft=draft,
        validation_report=report,
    )

    first_digest = storyboard_preflight_digest(
        preflight, pattern_version="1.0", phase_sequence=("demo",)
    )
    changed_version = preflight.model_copy(update={"version_id": FIRST_FACT_ID})
    second_digest = storyboard_preflight_digest(
        changed_version, pattern_version="1.0", phase_sequence=("demo",)
    )
    preview = compile_storyboard_preview(
        storyboard_id=FIRST_FACT_ID,
        storyboard_digest="b" * 64,
        phases=draft.phases,
        shots=draft.shots,
        image_count=2,
    )

    assert first_digest != second_digest
    assert preview.image_indexes == [0, 1]
    assert "image_urls" not in preview.model_dump()
