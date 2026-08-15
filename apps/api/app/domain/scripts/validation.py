import re
from collections.abc import Mapping
from uuid import UUID

from app.domain.products.entities import FactStatus, ProductFact
from app.domain.products.promotion import PromotionRender
from app.domain.scripts.creative_contract import (
    SAFE_ACCEPTANCE_SHOT,
    SAFE_ACTION,
    SAFE_PATTERN_KEYS,
    SAFE_PHASE_KEYS,
    SAFE_SHOOTING_LIST,
    SAFE_TAG,
    SAFE_TITLE_PATTERN,
    SAFE_VISUAL,
    safe_phase_purpose,
)
from app.domain.scripts.models import ScriptDraft, ValidationFinding, ValidationReport
from app.domain.scripts.patterns import CompiledPatternDefinition

_PROHIBITED_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CLAIM_GUARANTEE", re.compile(r"\bguarantee(?:d|s)?\b|保证|百分之百", re.IGNORECASE)),
    ("CLAIM_MEDICAL", re.compile(r"\b(?:cure|treat|heal)s?\b|治愈|治疗", re.IGNORECASE)),
    ("CLAIM_CERTIFICATION", re.compile(r"\bcertified\b|官方认证", re.IGNORECASE)),
    ("CLAIM_SCARCITY", re.compile(r"\blast chance\b|\bonly \d+ left\b|最后机会|仅剩\d+", re.IGNORECASE)),
    ("CLAIM_PRICE", re.compile(r"\bcheapest\b|全网最低|最低价", re.IGNORECASE)),
    ("CLAIM_COMPETITOR", re.compile(r"\bworse than\b|竞品都不如|碾压竞品", re.IGNORECASE)),
)


def _finding(rule_id: str, path: str, message: str, evidence: str | None = None) -> ValidationFinding:
    return ValidationFinding(rule_id=rule_id, path=path, message=message, evidence=evidence)


def _validate_structure(draft: ScriptDraft) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for name in ("phases", "shots", "titles", "tags", "shooting_list"):
        if not getattr(draft, name):
            findings.append(_finding("STRUCTURE_REQUIRED", name, f"{name} must not be empty"))

    phase_keys = {phase.key for phase in draft.phases}
    for index, shot in enumerate(draft.shots):
        for field in ("voiceover", "visual", "action", "acceptance_shot"):
            if not getattr(shot, field).strip():
                findings.append(
                    _finding(
                        "STRUCTURE_REQUIRED",
                        f"shots[{index}].{field}",
                        f"{field} must not be blank",
                    )
                )
        if shot.phase_key not in phase_keys:
            findings.append(
                _finding(
                    "PHASE_UNKNOWN",
                    f"shots[{index}].phase_key",
                    "shot must reference an existing phase",
                    shot.phase_key,
                )
            )
    return findings


def _spoken_units(text: str, language: str) -> int:
    if language.lower().startswith("zh"):
        return len(re.findall(r"[\u3400-\u9fff]", text))
    return len(re.findall(r"\b[\w'-]+\b", text))


def _normalize_claim(value: str) -> str:
    return " ".join(value.casefold().split())


def _validate_timeline(
    draft: ScriptDraft,
    *,
    speaking_rate_max: float | None = None,
) -> list[ValidationFinding]:
    if not draft.shots:
        return []

    findings: list[ValidationFinding] = []
    first = draft.shots[0]
    if abs(first.start_seconds) > 0.001:
        findings.append(_finding("TIMELINE_START", "shots[0].start_seconds", "timeline must start at 0"))

    for index, shot in enumerate(draft.shots):
        if shot.end_seconds <= shot.start_seconds:
            findings.append(_finding("TIMELINE_DURATION", f"shots[{index}]", "shot duration must be positive"))
            continue

        if index:
            previous = draft.shots[index - 1]
            if shot.start_seconds < previous.end_seconds:
                findings.append(_finding("TIMELINE_OVERLAP", f"shots[{index}].start_seconds", "shots must not overlap"))
            elif shot.start_seconds - previous.end_seconds > 0.1:
                findings.append(_finding("TIMELINE_GAP", f"shots[{index}].start_seconds", "shot gap must not exceed 0.1 seconds"))

        units = _spoken_units(shot.voiceover, draft.language)
        rate = speaking_rate_max or (4.0 if draft.language.lower().startswith("zh") else 2.5)
        if units / rate > shot.end_seconds - shot.start_seconds:
            findings.append(
                _finding(
                    "VOICEOVER_RATE_EXCEEDED" if speaking_rate_max is not None else "VOICEOVER_TOO_LONG",
                    f"shots[{index}].voiceover",
                    "voiceover exceeds the pattern speaking-rate budget",
                )
            )

    if abs(draft.shots[-1].end_seconds - draft.target_duration_seconds) > 0.5:
        findings.append(_finding("TIMELINE_END", f"shots[{len(draft.shots) - 1}].end_seconds", "timeline must end within 0.5 seconds of target"))
    return findings


def _validate_factuality(
    draft: ScriptDraft, facts: Mapping[UUID, ProductFact]
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for shot_index, shot in enumerate(draft.shots):
        if not shot.product_claims:
            findings.append(
                _finding(
                    "FACT_DECLARATION_REQUIRED",
                    f"shots[{shot_index}].product_claims",
                    "each shot must declare its rendered product claim",
                )
            )
            continue

        normalized_claims = {_normalize_claim(item) for item in shot.product_claims}
        for field in ("voiceover", "caption"):
            rendered = getattr(shot, field).strip()
            if rendered and _normalize_claim(rendered) not in normalized_claims:
                findings.append(
                    _finding(
                        "FACT_RENDER_MISMATCH",
                        f"shots[{shot_index}].{field}",
                        f"{field} must exactly match a declared product claim",
                        rendered,
                    )
                )

        for claim_index, claim in enumerate(shot.product_claims):
            claim_path = f"shots[{shot_index}].product_claims[{claim_index}]"
            if not shot.supported_fact_ids:
                findings.append(_finding("FACT_UNSUPPORTED", claim_path, "product claim requires a supported fact", claim))
                continue
            for fact_id in shot.supported_fact_ids:
                fact = facts.get(fact_id)
                if fact is None:
                    findings.append(_finding("FACT_NOT_FOUND", claim_path, "supported fact does not exist", str(fact_id)))
                elif draft.snapshot_id is not None and fact.snapshot_id != draft.snapshot_id:
                    findings.append(_finding("FACT_WRONG_SNAPSHOT", claim_path, "fact belongs to a different snapshot", str(fact_id)))
                elif fact.status not in {FactStatus.CONFIRMED, FactStatus.LOCKED}:
                    findings.append(_finding("FACT_UNCONFIRMED", claim_path, "fact must be confirmed or locked", str(fact_id)))
            referenced_facts = [
                fact for fact_id in shot.supported_fact_ids if (fact := facts.get(fact_id)) is not None
            ]
            if referenced_facts and all(
                _normalize_claim(fact.claim) != _normalize_claim(claim)
                for fact in referenced_facts
            ):
                findings.append(
                    _finding(
                        "FACT_CLAIM_MISMATCH",
                        claim_path,
                        "declared product claim must exactly match a referenced fact",
                        claim,
                    )
                )
    return findings


def _validate_prohibited_claims(draft: ScriptDraft) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for index, shot in enumerate(draft.shots):
        for field in ("voiceover", "visual", "action", "caption", "acceptance_shot"):
            text = getattr(shot, field)
            for rule_id, pattern in _PROHIBITED_RULES:
                match = pattern.search(text)
                if match:
                    findings.append(_finding(rule_id, f"shots[{index}].{field}", "prohibited claim detected", match.group(0)))
    for field in ("titles", "tags", "shooting_list"):
        for index, text in enumerate(getattr(draft, field)):
            for rule_id, pattern in _PROHIBITED_RULES:
                match = pattern.search(text)
                if match:
                    findings.append(
                        _finding(
                            rule_id,
                            f"{field}[{index}]",
                            "prohibited claim detected",
                            match.group(0),
                        )
                    )
    return findings


def _visible_text_fields(draft: ScriptDraft) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    fields.extend((f"phases[{index}].purpose", phase.purpose) for index, phase in enumerate(draft.phases))
    for shot_index, shot in enumerate(draft.shots):
        fields.extend(
            (f"shots[{shot_index}].{field}", getattr(shot, field))
            for field in ("voiceover", "visual", "action", "caption", "acceptance_shot")
        )
        if shot.promotion is not None:
            fields.append((f"shots[{shot_index}].promotion.text", shot.promotion.text))
        fields.extend(
            (f"shots[{shot_index}].product_claims[{claim_index}]", claim)
            for claim_index, claim in enumerate(shot.product_claims)
        )
    for field in ("titles", "tags", "shooting_list"):
        fields.extend(
            (f"{field}[{index}]", value)
            for index, value in enumerate(getattr(draft, field))
        )
    return fields


def _validate_promotion_slot(
    draft: ScriptDraft,
    *,
    promotion: PromotionRender | None,
    pattern_definition: CompiledPatternDefinition | None,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    expected_index = len(draft.shots) - 1
    allows_promotion = (
        pattern_definition is not None
        and pattern_definition.cta_policy.mode == "server_promotion_final_cta"
    )
    for index, shot in enumerate(draft.shots):
        if promotion is None:
            if shot.promotion is not None:
                findings.append(
                    _finding("PROMOTION_UNAUTHORIZED", f"shots[{index}].promotion", "no promotion is authorized")
                )
            continue
        if not allows_promotion or index != expected_index or shot.role != "cta":
            if shot.promotion is not None or (allows_promotion and index == expected_index):
                findings.append(
                    _finding("PROMOTION_SLOT_INVALID", f"shots[{index}].promotion", "promotion is permitted only in the final CTA shot")
                )
            continue
        if shot.promotion != promotion:
            findings.append(
                _finding("PROMOTION_RENDER_MISMATCH", f"shots[{index}].promotion", "promotion must match the server-rendered fact")
            )
    return findings


def _validate_excluded_facts(
    draft: ScriptDraft, excluded_facts: Mapping[UUID, ProductFact]
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    normalized_claims = {
        _normalize_claim(fact.claim): fact.claim
        for fact in excluded_facts.values()
        if _normalize_claim(fact.claim)
    }
    if not normalized_claims:
        return findings
    for path, value in _visible_text_fields(draft):
        normalized_value = _normalize_claim(value)
        for normalized_claim, claim in normalized_claims.items():
            if normalized_claim in normalized_value:
                findings.append(
                    _finding(
                        "FACT_EXCLUDED",
                        path,
                        "visible script text must not render an excluded fact",
                        claim,
                    )
                )
    return findings


def _validate_creative_contract(
    draft: ScriptDraft,
    *,
    creative_pattern_key: str | None,
    phase_sequence: tuple[str, ...] | None,
    pattern_definition: CompiledPatternDefinition | None,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if pattern_definition is not None:
        expected_phase_sequence = list(pattern_definition.phase_sequence)
        expected_shot_phase_sequence = [
            shot.phase_key for shot in pattern_definition.shots
        ]
        expected_shot_roles = list(pattern_definition.shot_roles)
        if [phase.key for phase in draft.phases] != expected_phase_sequence:
            findings.append(
                _finding(
                    "CREATIVE_PATTERN_MISMATCH",
                    "phases",
                    "phase sequence must exactly match the persisted creative pattern",
                )
            )
        if [shot.phase_key for shot in draft.shots] != expected_shot_phase_sequence:
            findings.append(
                _finding(
                    "CREATIVE_SHOT_PLAN_MISMATCH",
                    "shots",
                    "shot phase order must exactly match the compiled pattern plan",
                )
            )
        if [shot.role for shot in draft.shots] != expected_shot_roles:
            findings.append(
                _finding(
                    "CREATIVE_SHOT_PLAN_MISMATCH",
                    "shots",
                    "shot roles must exactly match the compiled pattern plan",
                )
            )
        total_weight = sum(item.budget_weight for item in pattern_definition.shots)
        for index, shot in enumerate(draft.shots):
            if index >= len(pattern_definition.shots):
                break
            expected_duration = (
                draft.target_duration_seconds
                * pattern_definition.shots[index].budget_weight
                / total_weight
            )
            if abs((shot.end_seconds - shot.start_seconds) - expected_duration) > 0.5:
                findings.append(
                    _finding(
                        "TIMELINE_BUDGET_MISMATCH",
                        f"shots[{index}]",
                        "shot duration must match the compiled pattern budget",
                    )
                )
        expected_purposes = [phase.purpose for phase in pattern_definition.phases]
        allowed_phase_keys: set[str] | frozenset[str] = set(expected_phase_sequence)
        copy = pattern_definition.server_owned_copy
        expected_shot_fields = {
            "visual": copy.visual,
            "action": copy.action,
            "acceptance_shot": copy.acceptance_shot,
        }
        allowed_tags: set[str] | frozenset[str] = {pattern_definition.key, copy.tag_suffix}
        allowed_shooting_list = set(copy.shooting_list)
    else:
        expected_purposes = []
        allowed_phase_keys = set(phase_sequence) if phase_sequence else SAFE_PHASE_KEYS
        expected_shot_fields = {
            "visual": SAFE_VISUAL,
            "action": SAFE_ACTION,
            "acceptance_shot": SAFE_ACCEPTANCE_SHOT,
        }
        allowed_tags = (
            {creative_pattern_key, SAFE_TAG}
            if creative_pattern_key is not None
            else SAFE_PATTERN_KEYS | {SAFE_TAG}
        )
        allowed_shooting_list = set(SAFE_SHOOTING_LIST)
    if pattern_definition is None and phase_sequence is not None:
        if [phase.key for phase in draft.phases] != list(phase_sequence):
            findings.append(
                _finding(
                    "CREATIVE_PATTERN_MISMATCH",
                    "phases",
                    "phase sequence must exactly match the persisted creative pattern",
                )
            )
        if [shot.phase_key for shot in draft.shots] != list(phase_sequence):
            findings.append(
                _finding(
                    "CREATIVE_PATTERN_MISMATCH",
                    "shots",
                    "shot phase order must exactly match the persisted creative pattern",
                )
            )
    for index, phase in enumerate(draft.phases):
        if phase.key not in allowed_phase_keys:
            findings.append(
                _finding(
                    "CREATIVE_FIELD_UNTRUSTED",
                    f"phases[{index}].key",
                    "phase key must come from the server-owned creative contract",
                    phase.key,
                )
            )
        elif phase.purpose != (
            expected_purposes[index]
            if pattern_definition is not None and index < len(expected_purposes)
            else safe_phase_purpose(phase.key)
        ):
            findings.append(
                _finding(
                    "CREATIVE_FIELD_UNTRUSTED",
                    f"phases[{index}].purpose",
                    "phase purpose must come from the server-owned creative contract",
                    phase.purpose,
                )
            )

    for index, shot in enumerate(draft.shots):
        for field, expected in expected_shot_fields.items():
            value = getattr(shot, field)
            if value != expected:
                findings.append(
                    _finding(
                        "CREATIVE_FIELD_UNTRUSTED",
                        f"shots[{index}].{field}",
                        f"{field} must come from the server-owned creative contract",
                        value,
                    )
                )

    for index, title in enumerate(draft.titles):
        title_is_server_owned = (
            title == pattern_definition.server_owned_copy.title
            if pattern_definition is not None
            else SAFE_TITLE_PATTERN.fullmatch(title) is not None
        )
        if not title_is_server_owned:
            findings.append(
                _finding(
                    "CREATIVE_FIELD_UNTRUSTED",
                    f"titles[{index}]",
                    "title must come from the server-owned creative contract",
                    title,
                )
            )
    for index, tag in enumerate(draft.tags):
        if tag not in allowed_tags:
            findings.append(
                _finding(
                    "CREATIVE_FIELD_UNTRUSTED",
                    f"tags[{index}]",
                    "tag must come from the server-owned creative contract",
                    tag,
                )
            )
    for index, item in enumerate(draft.shooting_list):
        if item not in allowed_shooting_list:
            findings.append(
                _finding(
                    "CREATIVE_FIELD_UNTRUSTED",
                    f"shooting_list[{index}]",
                    "shooting-list item must come from the server-owned creative contract",
                    item,
                )
            )
    return findings


def validate_script(
    draft: ScriptDraft,
    facts: Mapping[UUID, ProductFact],
    *,
    excluded_facts: Mapping[UUID, ProductFact] | None = None,
    creative_pattern_key: str | None = None,
    phase_sequence: tuple[str, ...] | None = None,
    pattern_definition: CompiledPatternDefinition | None = None,
    promotion: PromotionRender | None = None,
) -> ValidationReport:
    compiled_pattern = (
        pattern_definition
        if pattern_definition is not None and pattern_definition.is_compiled_contract
        else None
    )
    legacy_phase_sequence = (
        pattern_definition.phase_sequence
        if pattern_definition is not None and not pattern_definition.is_compiled_contract
        else phase_sequence
    )
    legacy_pattern_key = (
        pattern_definition.key
        if pattern_definition is not None and not pattern_definition.is_compiled_contract
        else creative_pattern_key
    )
    findings = [
        *_validate_structure(draft),
        *_validate_timeline(
            draft,
            speaking_rate_max=(
                compiled_pattern.speaking_rate.max
                if compiled_pattern is not None
                else None
            ),
        ),
        *_validate_factuality(draft, facts),
        *_validate_excluded_facts(draft, excluded_facts or {}),
        *_validate_creative_contract(
            draft,
            creative_pattern_key=legacy_pattern_key,
            phase_sequence=legacy_phase_sequence,
            pattern_definition=compiled_pattern,
        ),
        *_validate_promotion_slot(
            draft,
            promotion=promotion,
            pattern_definition=compiled_pattern,
        ),
        *_validate_prohibited_claims(draft),
    ]
    return ValidationReport(findings=sorted(findings, key=lambda item: (item.path, item.rule_id)))
