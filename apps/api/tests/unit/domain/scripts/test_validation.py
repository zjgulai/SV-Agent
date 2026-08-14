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
from app.domain.scripts.validation import validate_script

FACT_ID = UUID("00000000-0000-0000-0000-000000000010")
EXCLUDED_FACT_ID = UUID("00000000-0000-0000-0000-000000000011")
SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000020")
OTHER_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000021")


def test_validator_blocks_claim_without_supported_fact() -> None:
    draft = ScriptDraft(
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        phases=[ScriptPhase(key="hook", purpose="Hook", start_seconds=0, end_seconds=15)],
        shots=[
            ScriptShot(
                start_seconds=0,
                end_seconds=15,
                phase_key="hook",
                voiceover="This guarantees an energy boost.",
                visual=SAFE_VISUAL,
                action=SAFE_ACTION,
                caption="",
                acceptance_shot=SAFE_ACCEPTANCE_SHOT,
                supported_fact_ids=[],
                product_claims=["This guarantees an energy boost."],
            )
        ],
        titles=[SAFE_TITLE],
        tags=[SAFE_TAG],
        shooting_list=list(SAFE_SHOOTING_LIST),
    )

    report = validate_script(draft, facts={})

    assert report.acceptable is False
    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("FACT_UNSUPPORTED", "shots[0].product_claims[0]"),
        ("CLAIM_GUARANTEE", "shots[0].voiceover"),
    ]


def _confirmed_fact(*, snapshot_id: UUID = SNAPSHOT_ID) -> ProductFact:
    return ProductFact.create(
        id=FACT_ID,
        snapshot_id=snapshot_id,
        claim_type="feature",
        claim="The pouch is resealable",
        value={"resealable": True},
        evidence_kind="source_field",
        evidence_locator="additionalProperty.resealable",
        evidence_excerpt="Resealable pouch",
        confidence=1,
        status=FactStatus.CONFIRMED,
    )


def _excluded_fact() -> ProductFact:
    return ProductFact.create(
        id=EXCLUDED_FACT_ID,
        snapshot_id=SNAPSHOT_ID,
        claim_type="feature",
        claim="The drink is blue",
        value={"color": "blue"},
        evidence_kind="source_field",
        evidence_locator="color",
        evidence_excerpt="Blue drink",
        confidence=1,
        status=FactStatus.CONFIRMED,
    )


def _valid_draft(*, shots: list[ScriptShot] | None = None) -> ScriptDraft:
    return ScriptDraft(
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        snapshot_id=SNAPSHOT_ID,
        phases=[ScriptPhase(key="demo", purpose="Demo", start_seconds=0, end_seconds=15)],
        shots=shots
        or [
            ScriptShot(
                start_seconds=0,
                end_seconds=15,
                phase_key="demo",
                voiceover="The pouch is resealable",
                visual=SAFE_VISUAL,
                action=SAFE_ACTION,
                caption="The pouch is resealable",
                acceptance_shot=SAFE_ACCEPTANCE_SHOT,
                supported_fact_ids=[FACT_ID],
                product_claims=["The pouch is resealable"],
            )
        ],
        titles=[SAFE_TITLE],
        tags=[SAFE_TAG],
        shooting_list=list(SAFE_SHOOTING_LIST),
    )


def test_validator_accepts_complete_supported_script() -> None:
    report = validate_script(_valid_draft(), facts={FACT_ID: _confirmed_fact()})

    assert report.acceptable is True
    assert report.findings == []


def test_validator_blocks_an_excluded_fact_in_every_visible_script_field() -> None:
    excluded_claim = _excluded_fact().claim
    shot = _valid_draft().shots[0].model_copy(
        update={
            "voiceover": excluded_claim,
            "visual": excluded_claim,
            "action": excluded_claim,
            "caption": excluded_claim,
            "acceptance_shot": excluded_claim,
            "product_claims": [excluded_claim],
        }
    )
    draft = _valid_draft(shots=[shot]).model_copy(
        update={
            "phases": [
                ScriptPhase(
                    key="demo",
                    purpose=excluded_claim,
                    start_seconds=0,
                    end_seconds=15,
                )
            ],
            "titles": [excluded_claim],
            "tags": [excluded_claim],
            "shooting_list": [excluded_claim],
        }
    )

    report = validate_script(
        draft,
        facts={FACT_ID: _confirmed_fact()},
        excluded_facts={EXCLUDED_FACT_ID: _excluded_fact()},
    )

    assert {
        finding.path
        for finding in report.blocking
        if finding.rule_id == "FACT_EXCLUDED"
    } == {
        "phases[0].purpose",
        "shots[0].voiceover",
        "shots[0].visual",
        "shots[0].action",
        "shots[0].caption",
        "shots[0].acceptance_shot",
        "shots[0].product_claims[0]",
        "titles[0]",
        "tags[0]",
        "shooting_list[0]",
    }


def test_validator_uses_persisted_pattern_definition() -> None:
    draft = _valid_draft().model_copy(
        update={
            "phases": [
                ScriptPhase(
                    key="legacy_phase",
                    purpose="Legacy Phase",
                    start_seconds=0,
                    end_seconds=15,
                )
            ],
            "shots": [
                _valid_draft().shots[0].model_copy(
                    update={"phase_key": "legacy_phase"}
                )
            ],
            "tags": ["legacy_pattern", SAFE_TAG],
        }
    )

    report = validate_script(
        draft,
        facts={FACT_ID: _confirmed_fact()},
        creative_pattern_key="legacy_pattern",
        phase_sequence=("legacy_phase",),
    )

    assert report.acceptable is True


def test_validator_requires_complete_pattern_phase_order() -> None:
    draft = _valid_draft().model_copy(
        update={
            "phases": [
                ScriptPhase(
                    key="solution",
                    purpose="Solution",
                    start_seconds=0,
                    end_seconds=15,
                )
            ],
            "shots": [
                _valid_draft().shots[0].model_copy(update={"phase_key": "solution"})
            ],
            "tags": ["problem_solution", SAFE_TAG],
        }
    )

    report = validate_script(
        draft,
        facts={FACT_ID: _confirmed_fact()},
        creative_pattern_key="problem_solution",
        phase_sequence=("hook", "problem", "solution", "cta"),
    )

    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("CREATIVE_PATTERN_MISMATCH", "phases"),
        ("CREATIVE_PATTERN_MISMATCH", "shots"),
    ]


def test_validator_blocks_undeclared_spoken_claim() -> None:
    shot = _valid_draft().shots[0].model_copy(
        update={
            "voiceover": "Clinically proven to improve sleep quality.",
            "supported_fact_ids": [],
            "product_claims": [],
        }
    )

    report = validate_script(_valid_draft(shots=[shot]), facts={FACT_ID: _confirmed_fact()})

    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("FACT_DECLARATION_REQUIRED", "shots[0].product_claims")
    ]


def test_validator_blocks_claim_that_does_not_match_referenced_fact() -> None:
    unsupported = "Clinically proven to improve sleep quality"
    shot = _valid_draft().shots[0].model_copy(
        update={"voiceover": unsupported, "caption": unsupported, "product_claims": [unsupported]}
    )

    report = validate_script(_valid_draft(shots=[shot]), facts={FACT_ID: _confirmed_fact()})

    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("FACT_CLAIM_MISMATCH", "shots[0].product_claims[0]")
    ]


def test_validator_blocks_rendered_text_not_declared_as_a_fact_claim() -> None:
    shot = _valid_draft().shots[0].model_copy(
        update={"voiceover": "Clinically proven to improve sleep quality"}
    )

    report = validate_script(_valid_draft(shots=[shot]), facts={FACT_ID: _confirmed_fact()})

    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("FACT_RENDER_MISMATCH", "shots[0].voiceover")
    ]


def test_validator_scans_all_visible_script_fields_for_prohibited_claims() -> None:
    shot = _valid_draft().shots[0].model_copy(
        update={"visual": "Show how this cures fatigue", "action": "Display officially certified"}
    )
    draft = _valid_draft(shots=[shot]).model_copy(
        update={"titles": ["Guaranteed results"], "tags": ["cheapest"]}
    )

    report = validate_script(draft, facts={FACT_ID: _confirmed_fact()})

    assert [
        (item.rule_id, item.path)
        for item in report.blocking
        if item.rule_id.startswith("CLAIM_")
    ] == [
        ("CLAIM_CERTIFICATION", "shots[0].action"),
        ("CLAIM_MEDICAL", "shots[0].visual"),
        ("CLAIM_PRICE", "tags[0]"),
        ("CLAIM_GUARANTEE", "titles[0]"),
    ]


def test_validator_blocks_untrusted_non_claim_fields() -> None:
    shot = _valid_draft().shots[0].model_copy(
        update={
            "visual": "Clinically proven to improve sleep quality",
            "action": "Demonstrate ten hours of relief",
            "acceptance_shot": "The improvement claim is readable",
        }
    )
    draft = _valid_draft(shots=[shot]).model_copy(
        update={
            "titles": ["Improve sleep quality tonight"],
            "tags": ["sleep-improvement"],
            "shooting_list": ["ten-hour proof card"],
        }
    )

    report = validate_script(draft, facts={FACT_ID: _confirmed_fact()})

    assert {
        (item.rule_id, item.path)
        for item in report.blocking
        if item.rule_id == "CREATIVE_FIELD_UNTRUSTED"
    } == {
        ("CREATIVE_FIELD_UNTRUSTED", "shooting_list[0]"),
        ("CREATIVE_FIELD_UNTRUSTED", "shots[0].acceptance_shot"),
        ("CREATIVE_FIELD_UNTRUSTED", "shots[0].action"),
        ("CREATIVE_FIELD_UNTRUSTED", "shots[0].visual"),
        ("CREATIVE_FIELD_UNTRUSTED", "tags[0]"),
        ("CREATIVE_FIELD_UNTRUSTED", "titles[0]"),
    }


def test_validator_reports_overlapping_shots() -> None:
    shots = [
        ScriptShot(
            start_seconds=0,
            end_seconds=8,
            phase_key="demo",
            voiceover="The pouch is resealable",
            visual=SAFE_VISUAL,
            action=SAFE_ACTION,
            caption="",
            acceptance_shot=SAFE_ACCEPTANCE_SHOT,
            supported_fact_ids=[FACT_ID],
            product_claims=["The pouch is resealable"],
        ),
        ScriptShot(
            start_seconds=7.5,
            end_seconds=15,
            phase_key="demo",
            voiceover="The pouch is resealable",
            visual=SAFE_VISUAL,
            action=SAFE_ACTION,
            caption="",
            acceptance_shot=SAFE_ACCEPTANCE_SHOT,
            supported_fact_ids=[FACT_ID],
            product_claims=["The pouch is resealable"],
        ),
    ]

    report = validate_script(_valid_draft(shots=shots), facts={FACT_ID: _confirmed_fact()})

    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("TIMELINE_OVERLAP", "shots[1].start_seconds")
    ]


def test_validator_rejects_fact_from_another_snapshot() -> None:
    report = validate_script(
        _valid_draft(),
        facts={FACT_ID: _confirmed_fact(snapshot_id=OTHER_SNAPSHOT_ID)},
    )

    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("FACT_WRONG_SNAPSHOT", "shots[0].product_claims[0]")
    ]
