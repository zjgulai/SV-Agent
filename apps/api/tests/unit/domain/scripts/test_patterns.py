import pytest

from app.domain.scripts.patterns import (
    CREATIVE_PATTERNS,
    PatternCompileError,
    compile_pattern,
    load_persisted_pattern_definition,
)

_DURATION_COUNTS = {
    15: (3, 4),
    30: (4, 6),
    45: (5, 8),
}


@pytest.mark.parametrize("pattern", CREATIVE_PATTERNS, ids=lambda item: item.key)
@pytest.mark.parametrize("duration", _DURATION_COUNTS)
@pytest.mark.parametrize("language", ["en", "zh-CN"])
def test_pattern_compiler_freezes_every_supported_pattern_duration_and_language(
    pattern: object,
    duration: int,
    language: str,
) -> None:
    key = pattern.key
    compiled = compile_pattern(key, duration_seconds=duration, language=language)

    expected_phase_count, expected_shot_count = _DURATION_COUNTS[duration]
    assert compiled.contract_version == "p1.3c"
    assert compiled.key == key
    assert compiled.duration_seconds == duration
    assert compiled.language == language
    assert len(compiled.phases) == expected_phase_count
    assert len(compiled.shots) == expected_shot_count
    assert len({phase.key for phase in compiled.phases}) == expected_phase_count
    assert {shot.phase_key for shot in compiled.shots} == {
        phase.key for phase in compiled.phases
    }
    assert sum(shot.budget_weight for shot in compiled.shots) == duration
    assert all(phase.fact_role == "required_selected" for phase in compiled.phases)
    assert all(shot.fact_role == "required_selected" for shot in compiled.shots)
    assert compiled.audience_policy.mode == "server_owned_profile"
    assert compiled.audience_policy.profile_key == "general"
    assert compiled.audience_policy.allowed_slots == (
        "visual", "action", "acceptance_shot", "titles", "tags", "shooting_list"
    )
    assert compiled.cta_policy.mode == (
        "server_promotion_final_cta" if key == "offer_cta" else "server_generic_no_offer"
    )


@pytest.mark.parametrize(
    ("duration", "phase_keys", "shot_phase_keys", "weights"),
    [
        (15, ("hook", "solution", "cta"), ("hook", "solution", "solution", "cta"), (2, 4, 5, 4)),
        (30, ("hook", "problem", "solution", "cta"), ("hook", "problem", "problem", "solution", "solution", "cta"), (3, 5, 5, 6, 6, 5)),
        (45, ("hook", "problem", "solution", "proof", "cta"), ("hook", "problem", "problem", "solution", "solution", "proof", "proof", "cta"), (4, 5, 6, 7, 7, 6, 5, 5)),
    ],
)
def test_problem_solution_uses_the_approved_duration_layouts(
    duration: int,
    phase_keys: tuple[str, ...],
    shot_phase_keys: tuple[str, ...],
    weights: tuple[int, ...],
) -> None:
    compiled = compile_pattern("problem_solution", duration_seconds=duration, language="en")

    assert compiled.phase_sequence == phase_keys
    assert tuple(shot.phase_key for shot in compiled.shots) == shot_phase_keys
    assert tuple(shot.budget_weight for shot in compiled.shots) == weights


def test_pattern_compiler_rejects_unknown_duration_and_language() -> None:
    with pytest.raises(PatternCompileError):
        compile_pattern("missing", duration_seconds=15, language="en")
    with pytest.raises(PatternCompileError):
        compile_pattern("problem_solution", duration_seconds=60, language="en")
    with pytest.raises(PatternCompileError):
        compile_pattern("problem_solution", duration_seconds=15, language="fr")


def test_audience_profile_changes_only_frozen_server_owned_copy() -> None:
    general = compile_pattern("problem_solution", duration_seconds=15, language="en")
    work = compile_pattern(
        "problem_solution",
        duration_seconds=15,
        language="en",
        audience_profile_key="work_routine",
    )

    assert general.shots == work.shots
    assert general.phases == work.phases
    assert general.speaking_rate == work.speaking_rate
    assert general.server_owned_copy != work.server_owned_copy
    assert work.audience_policy.profile_key == "work_routine"


def test_legacy_pattern_definition_keeps_its_persisted_phase_and_role_plan() -> None:
    compiled = load_persisted_pattern_definition(
        {
            "hook_type": "legacy-hook",
            "phase_sequence": ["legacy_open", "legacy_close"],
            "shot_roles": ["intro", "outro"],
            "supported_durations": [15],
        },
        pattern_key="legacy_pattern",
        pattern_version="1.0",
        duration_seconds=15,
        language="en",
    )

    assert compiled.contract_version == "legacy-v1.0"
    assert [phase.key for phase in compiled.phases] == ["legacy_open", "legacy_close"]
    assert [shot.role for shot in compiled.shots] == ["intro", "outro"]


def test_p13a_definition_remains_compiled_without_registry_reinterpretation() -> None:
    current = compile_pattern("problem_solution", duration_seconds=30, language="en")
    historic = current.model_dump(mode="json")
    historic["contract_version"] = "p1.3a"
    historic["version"] = "1.1"
    historic["phases"] = [
        {
            "key": key,
            "purpose": key.title(),
            "shot_role": role,
            "fact_role": "required_selected",
        }
        for key, role in (
            ("hook", "problem"),
            ("problem", "demo"),
            ("solution", "result"),
            ("cta", "cta"),
        )
    ]
    historic["shots"] = [
        {
            "phase_key": key,
            "role": role,
            "fact_role": "required_selected",
            "budget_weight": 1,
        }
        for key, role in (
            ("hook", "problem"),
            ("problem", "demo"),
            ("solution", "result"),
            ("cta", "cta"),
        )
    ]

    loaded = load_persisted_pattern_definition(
        historic,
        pattern_key="problem_solution",
        pattern_version="1.1",
        duration_seconds=30,
        language="en",
    )

    assert loaded.contract_version == "p1.3a"
    assert loaded.model_dump(mode="json") == historic
    assert loaded.phase_sequence == ("hook", "problem", "solution", "cta")
