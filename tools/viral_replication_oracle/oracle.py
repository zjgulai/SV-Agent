from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

CLOSED_DISPOSITIONS = frozenset(
    {"blocked", "proceed_with_limits", "ready_for_next_gate"}
)
PRIMARY_MECHANISMS = (
    "narrative-transformation",
    "proof-demonstration",
    "experience-pov",
    "attention-grammar",
    "conversion-action",
    "trend-native",
)
CASE_KINDS = frozenset({"positive", "ambiguous", "blocked"})
_FAILURE_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class Failure:
    layer: str
    code: str
    path: str
    fixture_id: str | None = None
    case_id: str | None = None
    detail: str = ""

    def render(self) -> str:
        parts = [f"layer={self.layer}", f"code={self.code}", f"path={self.path}"]
        if self.fixture_id:
            parts.append(f"fixture={self.fixture_id}")
        if self.case_id:
            parts.append(f"case={self.case_id}")
        if self.detail:
            parts.append(f"detail={self.detail}")
        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class Evaluation:
    disposition: str
    failure_codes: tuple[str, ...]


@dataclass(slots=True)
class FixtureFileResult:
    path: Path
    json_readable: bool = False
    schema_valid: bool = False
    fixture_id: str | None = None
    expectation_total: int = 0
    expectation_passed: int = 0
    failures: list[Failure] = field(default_factory=list)
    coverage: set[tuple[str, str]] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class OracleReport:
    root: Path
    total_files: int
    json_readable: int
    schema_valid: int
    expectation_total: int
    expectation_passed: int
    coverage: Mapping[str, frozenset[str]]
    failures: tuple[Failure, ...]

    @property
    def ok(self) -> bool:
        return not self.failures

    def render_text(self) -> str:
        result = "pass" if self.ok else "fail"
        lines = [
            (
                "fixture-oracle/v1 "
                f"result={result} files={self.total_files} json={self.json_readable} "
                f"fixture_schema={self.schema_valid} expectations={self.expectation_passed}/{self.expectation_total} "
                f"mechanisms={len(self.coverage)}/{len(PRIMARY_MECHANISMS)}"
            )
        ]
        lines.extend(failure.render() for failure in self.failures)
        return "\n".join(lines)


def _failure(
    result: FixtureFileResult,
    *,
    layer: str,
    code: str,
    case_id: str | None = None,
    detail: str = "",
) -> None:
    result.failures.append(
        Failure(
            layer=layer,
            code=code,
            path=result.path.name,
            fixture_id=result.fixture_id,
            case_id=case_id,
            detail=detail,
        )
    )


def _expected_contract(
    value: Any,
    *,
    result: FixtureFileResult,
    case_id: str | None,
) -> tuple[str, tuple[str, ...]] | None:
    if not isinstance(value, dict):
        _failure(
            result, layer="schema", code="EXPECTED_CONTRACT_INVALID", case_id=case_id
        )
        return None
    disposition = value.get("disposition")
    if disposition not in CLOSED_DISPOSITIONS:
        _failure(
            result, layer="schema", code="EXPECTED_DISPOSITION_INVALID", case_id=case_id
        )
        return None
    blockers = value.get("blockers", [])
    if (
        not isinstance(blockers, list)
        or any(
            not isinstance(code, str) or not _FAILURE_CODE.fullmatch(code)
            for code in blockers
        )
        or len(blockers) != len(set(blockers))
    ):
        _failure(
            result,
            layer="schema",
            code="EXPECTED_FAILURE_CODES_INVALID",
            case_id=case_id,
        )
        return None
    return disposition, tuple(blockers)


_MECHANISM_GUARDS: Mapping[str, tuple[str, str, str]] = {
    "narrative-transformation": (
        "narrative_arc_state",
        "problem_intervention_result_bound",
        "narrative_arc_incomplete",
    ),
    "proof-demonstration": (
        "proof_claim_state",
        "observed_and_claim_separated",
        "proof_claim_boundary_unresolved",
    ),
    "experience-pov": (
        "identity_continuity_state",
        "target_identity_confirmed",
        "experience_identity_continuity_unresolved",
    ),
    "attention-grammar": (
        "attention_component_state",
        "single_component_bound",
        "attention_component_ambiguous",
    ),
    "conversion-action": (
        "promotion_cta_state",
        "server_owned_or_not_applicable",
        "conversion_cta_ownership_unresolved",
    ),
    "trend-native": (
        "trend_admission_state",
        "bounded_no_external_execution",
        "trend_admission_unresolved",
    ),
}


def _evaluate_oracle_case(case: Mapping[str, Any]) -> Evaluation:
    mechanism = case["primary_mechanism"]
    reference = case["reference"]
    routing = case["routing"]
    contract = case["contract"]
    codes: list[str] = []

    if reference.get("source_identity") != "resolved":
        codes.append("source_identity_unresolved")
    if reference.get("source_digest") != "present":
        codes.append("source_digest_missing")
    if reference.get("playability") != "reproducible":
        codes.append("playability_not_reproducible")
    if reference.get("rights_state") != "analysis_and_adaptation_confirmed":
        codes.append("reference_rights_scope_unresolved")

    candidates = routing.get("candidate_mechanisms")
    if not isinstance(candidates, list) or len(candidates) != 1:
        codes.append("primary_mechanism_ambiguous")
    elif candidates[0] != mechanism or routing.get("declared_primary") != mechanism:
        codes.append("primary_mechanism_mismatch")

    changed = contract.get("changed_dimensions")
    declared = contract.get("declared_changed_dimension")
    if not isinstance(changed, list) or len(changed) != 1:
        codes.append("multiple_changed_dimensions")
    elif changed[0] != declared:
        codes.append("declared_dimension_does_not_match_actual_drift")
    if contract.get("facts_state") != "confirmed_locked_only":
        codes.append("product_fact_gate_blocked")
    if contract.get("rights_state") != "confirmed":
        codes.append("contract_rights_scope_unresolved")

    field_name, allowed_value, failure_code = _MECHANISM_GUARDS[mechanism]
    if contract.get(field_name) != allowed_value:
        codes.append(failure_code)

    return Evaluation(
        disposition="ready_for_next_gate" if not codes else "blocked",
        failure_codes=tuple(codes),
    )


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _p3_001(data: Mapping[str, Any]) -> Evaluation:
    bundle = data.get("reference_bundle", {})
    playability = bundle.get("playability", {})
    codes: list[str] = []
    if not bundle.get("source_refs"):
        codes.append("source_identity_unresolved")
    if not bundle.get("source_digest"):
        codes.append("source_digest_missing")
    if not playability.get("reproducible_capture"):
        codes.append("playability_not_reproducible")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _p3_002(data: Mapping[str, Any]) -> Evaluation:
    records = data.get("measurement_records", [])
    ambiguous = any(
        item.get("state") == "source_ambiguous"
        for item in records
        if isinstance(item, dict)
    )
    codes = (
        ("source_ambiguous_measurement_cannot_enter_claim_mapping",)
        if ambiguous
        else ()
    )
    return Evaluation("proceed_with_limits" if codes else "ready_for_next_gate", codes)


def _p3_003(data: Mapping[str, Any]) -> Evaluation:
    facts = {
        item.get("fact_id"): item
        for item in data.get("product_snapshot", {}).get("facts", [])
    }
    claims = data.get("claim_candidates", [])
    unsupported = any(not item.get("fact_refs") for item in claims)
    excluded = any(
        any(
            facts.get(fact_id, {}).get("status") == "excluded"
            for fact_id in item.get("fact_refs", [])
        )
        for item in claims
    )
    codes: list[str] = []
    if unsupported:
        codes.append("unsupported_claim")
    if excluded:
        codes.append("excluded_fact_resurrection")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _p3_004(data: Mapping[str, Any]) -> Evaluation:
    contract = data.get("replication_contract", {})
    control = contract.get("control", {})
    variant = contract.get("variant", {})
    changed = [
        key
        for key in sorted(set(control) | set(variant))
        if control.get(key) != variant.get(key)
    ]
    declared = contract.get("declared_changed_dimension")
    normalized_declared = (
        "visual_proof_device" if declared == "proof_device" else declared
    )
    codes = []
    if len(changed) != 1:
        codes.append("multiple_changed_dimensions")
    if changed != [normalized_declared]:
        codes.append("declared_dimension_does_not_match_actual_drift")
    if any(
        token in str(contract.get("evaluation_request", ""))
        for token in ("causal", "winner")
    ):
        codes.append("causal_request_exceeds_contract")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _p3_005(data: Mapping[str, Any]) -> Evaluation:
    bundle = data.get("reference_bundle", {})
    action = str(data.get("requested_action", ""))
    codes = []
    if bundle.get("rights_state") == "unknown":
        codes.append("rights_state_unknown")
    if bundle.get("usage_scope") is None:
        codes.append("usage_scope_missing")
    if "republish" in action:
        codes.append("republish_permission_missing")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _attention_f1(data: Mapping[str, Any]) -> Evaluation:
    window = data.get("reference_bundle", {}).get("performance_window", {})
    requested = str(data.get("requested_conclusion", ""))
    codes = []
    if window.get("retention_rate", {}).get("state") == "not_reported":
        codes.append("retention_not_reported")
    if any(
        window.get(key) == "unknown"
        for key in (
            "account_size",
            "posting_time",
            "paid_distribution",
            "recommendation_effect",
        )
    ):
        codes.append("critical_control_variables_unknown")
    if "证明" in requested or "留存" in requested:
        codes.append("causal_attention_claim_unsupported")
    if "默认 Pattern" in requested:
        codes.append("default_pattern_promotion_unsupported")
    return Evaluation(
        "proceed_with_limits" if codes else "ready_for_next_gate", tuple(codes)
    )


def _attention_f2(data: Mapping[str, Any]) -> Evaluation:
    bundle = data.get("reference_bundle", {})
    plan = data.get("attention_adaptation_plan", {})
    substitutions = plan.get("target_substitutions", {})
    codes = []
    if any("reference" in str(value) for value in substitutions.values()):
        codes.append("protected_surface_copy")
    if bundle.get("usage_scope") == "analysis_only":
        codes.append("adaptation_scope_exceeds_rights_scope")
    if plan.get("prohibited_surface_copy") and any(
        "reference" in str(value) for value in substitutions.values()
    ):
        codes.append("prohibited_surface_copy_ignored")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _attention_f3(data: Mapping[str, Any]) -> Evaluation:
    contract = data.get("replication_contract", {})
    control = contract.get("control", {})
    variant = contract.get("variant", {})
    changed = [key for key in control if control.get(key) != variant.get(key)]
    attention = {
        "hook_trigger",
        "reveal_cadence",
        "caption_cadence",
        "visual_contrast",
        "sonic_timing",
    }
    codes = []
    if len(attention.intersection(changed)) > 1:
        codes.append("multiple_changed_attention_components")
    if "duration_seconds" in changed:
        codes.append("duration_drift")
    if "sonic_timing" in changed:
        codes.append("sound_policy_drift")
    if set(changed) != {contract.get("declared_changed_dimension")}:
        codes.append("declared_dimension_does_not_match_actual_drift")
    if "attribute" in str(contract.get("evaluation_request", "")):
        codes.append("causal_request_exceeds_contract")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _attention_f4(data: Mapping[str, Any]) -> Evaluation:
    mapping = data.get("decomposition_map", {})
    dependency = mapping.get("trend_dependency", {})
    codes: list[str] = []
    if mapping.get("proposed_primary_mechanism") == "attention-grammar" and any(
        dependency.get(key)
        for key in ("platform_template_required", "named_audio_required")
    ):
        codes.extend(("primary_mechanism_misrouted", "trend_native_dependency"))
    if dependency.get("usage_rights_state") == "unknown":
        codes.append("trend_audio_rights_unknown")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _attention_f5(data: Mapping[str, Any]) -> Evaluation:
    observation = data.get("performance_observation", {})
    metrics = observation.get("metrics", [])
    requested = str(data.get("requested_conclusion", ""))
    codes = []
    if (
        any(item.get("state") == "observed_zero" for item in metrics)
        and "表现差" in requested
    ):
        codes.append("observed_zero_cannot_mean_attention_failure")
    if any(item.get("state") in {"not_reported", "not_collected"} for item in metrics):
        codes.append("observation_availability_unresolved")
    if observation.get("performance_subject_binding") == "unresolved":
        codes.extend(
            (
                "performance_subject_binding_unresolved",
                "cross_subject_generalization_blocked",
            )
        )
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _conversion_f1(data: Mapping[str, Any]) -> Evaluation:
    contract = data.get("generation_contract", {})
    promotion_id = contract.get("promotion_fact_id")
    codes: list[str] = []
    if promotion_id in contract.get(
        "selected_fact_ids", []
    ) or promotion_id in contract.get("excluded_fact_ids", []):
        codes.extend(
            (
                "promotion_fact_in_selected_or_excluded_set",
                "promotion_must_use_separate_field",
            )
        )
    if "promotion" in contract.get("provider_input_fields", []):
        codes.append("promotion_provider_leakage")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _conversion_f2(data: Mapping[str, Any]) -> Evaluation:
    fact = data.get("promotion_fact", {})
    value = fact.get("value", {})
    database_time = _parse_time(fact.get("database_time"))
    start = _parse_time(value.get("effective_from"))
    end = _parse_time(value.get("effective_to"))
    inactive = (
        not database_time or not start or not end or not (start <= database_time < end)
    )
    codes = (
        (
            "promotion_not_active_at_database_time",
            "expired_promotion_cannot_render",
            "time_bound_offer_unavailable",
        )
        if inactive
        else ()
    )
    return Evaluation("blocked" if codes else "ready_for_next_gate", codes)


def _conversion_f3(data: Mapping[str, Any]) -> Evaluation:
    contract = data.get("generation_contract", {})
    pattern = contract.get("creative_pattern", {})
    slots = contract.get("requested_promotion_slots", [])
    codes = []
    if (
        contract.get("promotion_fact_id")
        and pattern.get("cta_policy") != "server_promotion_final_cta"
    ):
        codes.append("promotion_cta_policy_mismatch")
    if "promotion" in contract.get("provider_input_fields", []):
        codes.append("promotion_provider_leakage")
    if slots != ["cta"]:
        codes.append("promotion_slot_not_final_cta")
    if (
        contract.get("promotion_fact_id")
        and pattern.get("cta_policy") == "server_generic_no_offer"
    ):
        codes.append("generic_and_promotion_cta_conflated")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _conversion_f4(data: Mapping[str, Any]) -> Evaluation:
    plan = data.get("conversion_action_plan", {})
    path = plan.get("action_path", {})
    codes = []
    if path.get("binding_state") == "unresolved":
        codes.append("action_path_unresolved")
    if path.get("reference_url"):
        codes.extend(
            ("external_action_out_of_scope", "unmodeled_external_action_destination")
        )
    if "action_destination" in plan.get("provider_input_fields", []):
        codes.append("provider_action_destination_leakage")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _conversion_f5(data: Mapping[str, Any]) -> Evaluation:
    mapping = data.get("decomposition_map", {})
    misrouted = mapping.get(
        "proposed_primary_mechanism"
    ) == "conversion-action" and bool(mapping.get("proof_observations"))
    codes = (
        (
            "primary_mechanism_misrouted",
            "conversion_component_not_primary",
            "proof_demonstration_primary",
        )
        if misrouted
        else ()
    )
    return Evaluation("blocked" if codes else "ready_for_next_gate", codes)


def _trend_f1(data: Mapping[str, Any]) -> Evaluation:
    mapping = data.get("decomposition_map", {})
    misrouted = mapping.get("proposed_primary_mechanism") == "trend-native" and bool(
        mapping.get("proof_observations")
    )
    codes = (
        (
            "primary_mechanism_misrouted",
            "trend_dependency_not_primary",
            "proof_demonstration_primary",
        )
        if misrouted
        else ()
    )
    return Evaluation("blocked" if codes else "ready_for_next_gate", codes)


def _trend_f2(data: Mapping[str, Any]) -> Evaluation:
    binding = data.get("trend_signal_binding", {})
    codes = []
    if not binding.get("trend_observation_id") or not binding.get("source_refs"):
        codes.append("trend_signal_identity_unresolved")
    if not binding.get("observation_window") or not binding.get("observed_at"):
        codes.append("trend_observation_window_unbounded")
    if "当前热门" in str(binding.get("request", "")):
        codes.append("current_trend_claim_unsupported")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _trend_f3(data: Mapping[str, Any]) -> Evaluation:
    plan = data.get("trend_native_plan", {})
    audio = plan.get("audio_function", {})
    codes = []
    if audio.get("source_audio_reuse_state") == "not_permitted":
        codes.append("reference_audio_reuse_not_permitted")
    if "near_duplicate" in str(audio.get("target_sound_policy_variant", "")):
        codes.append("audio_substitution_provenance_unresolved")
    if audio.get("target_sound_policy_control") != audio.get(
        "target_sound_policy_variant"
    ):
        codes.extend(
            (
                "audio_function_not_frozen",
                "declared_dimension_does_not_match_actual_drift",
            )
        )
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _trend_f4(data: Mapping[str, Any]) -> Evaluation:
    plan = data.get("trend_native_plan", {})
    template = plan.get("template_grammar", {})
    admission = plan.get("trend_admission", {})
    rights = admission.get("rights_scope", {})
    delta = admission.get("originality_delta", {})
    codes = []
    if template.get("availability_state") == "visible_in_reference":
        codes.append("template_availability_unverified")
    if rights.get("template_usage_state") == "unknown":
        codes.append("template_adaptation_scope_unconfirmed")
    if not delta.get("source_identity_exclusions"):
        codes.append("template_identity_copy_not_separated")
    if delta.get("review_state") == "not_collected":
        codes.append("originality_delta_unreviewable")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _trend_f5(data: Mapping[str, Any]) -> Evaluation:
    compatibility = data.get("trend_admission", {}).get("platform_compatibility", {})
    codes = []
    if compatibility.get(
        "assessment_state"
    ) == "platform_compatible" and compatibility.get("observed_constraints"):
        codes.append("platform_compatibility_unverified")
    if compatibility.get("execution_capability") == "not_implemented":
        codes.append("platform_execution_capability_not_implemented")
    if compatibility.get("external_action_requested"):
        codes.append("external_platform_action_out_of_scope")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _media_f1(data: Mapping[str, Any]) -> Evaluation:
    record = data.get("media_integrity_record", {})
    trace = record.get("artifact_traceability", {})
    profile = record.get("technical_profile", {})
    codes = []
    if record.get("contract_digest") != trace.get("config_digest"):
        codes.append("artifact_contract_digest_mismatch")
    if trace.get("provenance_state") != "reconciled":
        codes.append("artifact_provenance_unreconciled")
    if trace.get("artifact_id") != profile.get("observed_artifact_id"):
        codes.append("technical_profile_not_bound_to_artifact")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _media_f2(data: Mapping[str, Any]) -> Evaluation:
    surface = data.get("media_integrity_record", {}).get("communicative_surface", {})
    codes = []
    if surface.get("excluded_occurrence_count", 0) > 0:
        codes.append("excluded_claim_detected_in_media_surface")
    if surface.get("asr_status") == "unavailable" and not surface.get("human_fallback"):
        codes.extend(
            ("audible_surface_unreviewed", "communicative_surface_evidence_incomplete")
        )
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _media_f3(data: Mapping[str, Any]) -> Evaluation:
    identity = data.get("media_integrity_record", {}).get(
        "target_identity_continuity", {}
    )
    required = identity.get("required_identity", {})
    observations = identity.get("observations", [])
    drift = any(
        any(item.get(key) != required.get(key) for key in required)
        for item in observations
    )
    codes = []
    if drift:
        codes.append("target_identity_drift_detected")
    if identity.get("independent_review_state") != "completed":
        codes.append("cross_shot_continuity_unverified")
    if (
        identity.get("model_similarity_score") is not None
        and identity.get("independent_review_state") != "completed"
    ):
        codes.append("model_similarity_not_sufficient_for_identity_gate")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _media_f4(data: Mapping[str, Any]) -> Evaluation:
    record = data.get("media_integrity_record", {})
    trace = record.get("artifact_traceability", {})
    scopes = record.get("source_use_scope", [])
    codes = []
    if any(
        item.get("evidence_state") == "confirmed_for_internal_analysis_only"
        and "reuse" in str(item.get("intended_use"))
        for item in scopes
    ):
        codes.append("planned_use_exceeds_source_use_scope")
    if trace.get("target_asset_bundle_state") == "structurally_valid":
        codes.append("asset_traceability_not_usage_entitlement")
    if trace.get("commercial_approval", {}).get("availability") != "available":
        codes.append("commercial_approval_unavailable")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


def _media_f5(data: Mapping[str, Any]) -> Evaluation:
    delta = data.get("media_integrity_record", {}).get("originality_delta", {})
    codes = []
    if delta.get("unexcluded_source_surfaces"):
        codes.append("source_identity_exclusion_incomplete")
    if delta.get("comparison_method") == "model_similarity_summary_only":
        codes.append("originality_review_not_independent")
    if delta.get("review_state") == "claimed_passed":
        codes.append("originality_approval_overclaim")
    return Evaluation("blocked" if codes else "ready_for_next_gate", tuple(codes))


_LEGACY_ADAPTERS: Mapping[str, Callable[[Mapping[str, Any]], Evaluation]] = {
    "VR-P3-001": _p3_001,
    "VR-P3-002": _p3_002,
    "VR-P3-003": _p3_003,
    "VR-P3-004": _p3_004,
    "VR-P3-005": _p3_005,
    "VR-P4-001-F1": _attention_f1,
    "VR-P4-001-F2": _attention_f2,
    "VR-P4-001-F3": _attention_f3,
    "VR-P4-001-F4": _attention_f4,
    "VR-P4-001-F5": _attention_f5,
    "VR-P4-002-F1": _conversion_f1,
    "VR-P4-002-F2": _conversion_f2,
    "VR-P4-002-F3": _conversion_f3,
    "VR-P4-002-F4": _conversion_f4,
    "VR-P4-002-F5": _conversion_f5,
    "VR-P4-003-F1": _trend_f1,
    "VR-P4-003-F2": _trend_f2,
    "VR-P4-003-F3": _trend_f3,
    "VR-P4-003-F4": _trend_f4,
    "VR-P4-003-F5": _trend_f5,
    "VR-P4-004-F1": _media_f1,
    "VR-P4-004-F2": _media_f2,
    "VR-P4-004-F3": _media_f3,
    "VR-P4-004-F4": _media_f4,
    "VR-P4-004-F5": _media_f5,
}

_LEGACY_SHAPE_RULES: Mapping[str, tuple[tuple[tuple[str, ...], str], ...]] = {
    "VR-P3-001": (
        (("reference_bundle",), "mapping"),
        (("reference_bundle", "playability"), "mapping"),
        (("reference_bundle", "source_refs"), "list"),
    ),
    "VR-P3-002": ((("measurement_records",), "mapping_list"),),
    "VR-P3-003": (
        (("product_snapshot",), "mapping"),
        (("product_snapshot", "facts"), "mapping_list"),
        (("claim_candidates",), "claim_mapping_list"),
    ),
    "VR-P3-004": (
        (("replication_contract",), "mapping"),
        (("replication_contract", "control"), "mapping"),
        (("replication_contract", "variant"), "mapping"),
    ),
    "VR-P3-005": ((("reference_bundle",), "mapping"),),
    "VR-P4-001-F1": (
        (("reference_bundle",), "mapping"),
        (("reference_bundle", "performance_window"), "mapping"),
        (("reference_bundle", "performance_window", "retention_rate"), "mapping"),
    ),
    "VR-P4-001-F2": (
        (("reference_bundle",), "mapping"),
        (("attention_adaptation_plan",), "mapping"),
        (("attention_adaptation_plan", "target_substitutions"), "mapping"),
    ),
    "VR-P4-001-F3": (
        (("replication_contract",), "mapping"),
        (("replication_contract", "control"), "mapping"),
        (("replication_contract", "variant"), "mapping"),
    ),
    "VR-P4-001-F4": (
        (("decomposition_map",), "mapping"),
        (("decomposition_map", "trend_dependency"), "mapping"),
    ),
    "VR-P4-001-F5": (
        (("performance_observation",), "mapping"),
        (("performance_observation", "metrics"), "mapping_list"),
    ),
    "VR-P4-002-F1": (
        (("generation_contract",), "mapping"),
        (("generation_contract", "selected_fact_ids"), "list"),
        (("generation_contract", "excluded_fact_ids"), "list"),
        (("generation_contract", "provider_input_fields"), "list"),
    ),
    "VR-P4-002-F2": (
        (("promotion_fact",), "mapping"),
        (("promotion_fact", "value"), "mapping"),
    ),
    "VR-P4-002-F3": (
        (("generation_contract",), "mapping"),
        (("generation_contract", "creative_pattern"), "mapping"),
        (("generation_contract", "requested_promotion_slots"), "list"),
        (("generation_contract", "provider_input_fields"), "list"),
    ),
    "VR-P4-002-F4": (
        (("conversion_action_plan",), "mapping"),
        (("conversion_action_plan", "action_path"), "mapping"),
        (("conversion_action_plan", "provider_input_fields"), "list"),
    ),
    "VR-P4-002-F5": (
        (("decomposition_map",), "mapping"),
        (("decomposition_map", "proof_observations"), "list"),
    ),
    "VR-P4-003-F1": (
        (("decomposition_map",), "mapping"),
        (("decomposition_map", "proof_observations"), "list"),
    ),
    "VR-P4-003-F2": (
        (("trend_signal_binding",), "mapping"),
        (("trend_signal_binding", "source_refs"), "list"),
        (("trend_signal_binding", "observation_window"), "mapping_or_none"),
    ),
    "VR-P4-003-F3": (
        (("trend_native_plan",), "mapping"),
        (("trend_native_plan", "audio_function"), "mapping"),
    ),
    "VR-P4-003-F4": (
        (("trend_native_plan",), "mapping"),
        (("trend_native_plan", "template_grammar"), "mapping"),
        (("trend_native_plan", "trend_admission"), "mapping"),
        (("trend_native_plan", "trend_admission", "rights_scope"), "mapping"),
        (
            ("trend_native_plan", "trend_admission", "originality_delta"),
            "mapping",
        ),
        (
            (
                "trend_native_plan",
                "trend_admission",
                "originality_delta",
                "source_identity_exclusions",
            ),
            "list",
        ),
    ),
    "VR-P4-003-F5": (
        (("trend_admission",), "mapping"),
        (("trend_admission", "platform_compatibility"), "mapping"),
        (
            ("trend_admission", "platform_compatibility", "observed_constraints"),
            "list",
        ),
    ),
    "VR-P4-004-F1": (
        (("media_integrity_record",), "mapping"),
        (("media_integrity_record", "artifact_traceability"), "mapping"),
        (("media_integrity_record", "technical_profile"), "mapping"),
    ),
    "VR-P4-004-F2": (
        (("media_integrity_record",), "mapping"),
        (("media_integrity_record", "communicative_surface"), "mapping"),
    ),
    "VR-P4-004-F3": (
        (("media_integrity_record",), "mapping"),
        (("media_integrity_record", "target_identity_continuity"), "mapping"),
        (
            (
                "media_integrity_record",
                "target_identity_continuity",
                "required_identity",
            ),
            "mapping",
        ),
        (
            (
                "media_integrity_record",
                "target_identity_continuity",
                "observations",
            ),
            "mapping_list",
        ),
    ),
    "VR-P4-004-F4": (
        (("media_integrity_record",), "mapping"),
        (("media_integrity_record", "artifact_traceability"), "mapping"),
        (
            (
                "media_integrity_record",
                "artifact_traceability",
                "commercial_approval",
            ),
            "mapping",
        ),
        (("media_integrity_record", "source_use_scope"), "mapping_list"),
    ),
    "VR-P4-004-F5": (
        (("media_integrity_record",), "mapping"),
        (("media_integrity_record", "originality_delta"), "mapping"),
        (
            (
                "media_integrity_record",
                "originality_delta",
                "unexcluded_source_surfaces",
            ),
            "list",
        ),
    ),
}

_MISSING = object()


def _value_at_path(data: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = data
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _shape_matches(value: Any, kind: str) -> bool:
    if kind == "mapping":
        return isinstance(value, Mapping)
    if kind == "mapping_or_none":
        return value is None or isinstance(value, Mapping)
    if kind == "list":
        return isinstance(value, list)
    if kind == "mapping_list":
        return isinstance(value, list) and all(
            isinstance(item, Mapping) for item in value
        )
    if kind == "claim_mapping_list":
        return (
            isinstance(value, list)
            and all(isinstance(item, Mapping) for item in value)
            and all(isinstance(item.get("fact_refs"), list) for item in value)
        )
    raise AssertionError(f"Unknown legacy shape kind: {kind}")


def _validate_legacy_shape(
    data: Mapping[str, Any], *, fixture_id: str, result: FixtureFileResult
) -> bool:
    rules = _LEGACY_SHAPE_RULES.get(fixture_id)
    if rules is None:
        _failure(result, layer="schema", code="LEGACY_SHAPE_CONTRACT_MISSING")
        return False
    for path, kind in rules:
        value = _value_at_path(data, path)
        if value is _MISSING or not _shape_matches(value, kind):
            _failure(
                result,
                layer="schema",
                code="LEGACY_FIXTURE_SHAPE_INVALID",
                detail=f"field={'.'.join(path)},expected={kind}",
            )
            return False
    return True


def _compare_expectation(
    *,
    result: FixtureFileResult,
    case_id: str | None,
    expected: tuple[str, tuple[str, ...]],
    actual: Evaluation,
) -> None:
    result.expectation_total += 1
    expected_disposition, expected_codes = expected
    passed = True
    if actual.disposition != expected_disposition:
        passed = False
        _failure(
            result,
            layer="expectation",
            code="EXPECTATION_DISPOSITION_MISMATCH",
            case_id=case_id,
            detail=f"expected={expected_disposition},actual={actual.disposition}",
        )
    if actual.failure_codes != expected_codes:
        passed = False
        _failure(
            result,
            layer="expectation",
            code="EXPECTATION_FAILURE_CODES_MISMATCH",
            case_id=case_id,
            detail=f"expected={','.join(expected_codes)},actual={','.join(actual.failure_codes)}",
        )
    if passed:
        result.expectation_passed += 1


def _case_kind_matches_actual(case_kind: str, actual: Evaluation) -> bool:
    if case_kind == "positive":
        return actual.disposition == "ready_for_next_gate" and not actual.failure_codes
    if case_kind == "ambiguous":
        return (
            actual.disposition == "blocked"
            and "primary_mechanism_ambiguous" in actual.failure_codes
        )
    return actual.disposition == "blocked" and any(
        code != "primary_mechanism_ambiguous" for code in actual.failure_codes
    )


def _validate_oracle_case(case: Any, *, result: FixtureFileResult) -> None:
    if not isinstance(case, dict):
        _failure(result, layer="schema", code="ORACLE_CASE_INVALID")
        return
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        _failure(result, layer="schema", code="ORACLE_CASE_ID_INVALID")
        return
    mechanism = case.get("primary_mechanism")
    if mechanism not in PRIMARY_MECHANISMS:
        _failure(
            result, layer="schema", code="PRIMARY_MECHANISM_INVALID", case_id=case_id
        )
        return
    case_kind = case.get("case_kind")
    if case_kind not in CASE_KINDS:
        _failure(result, layer="schema", code="CASE_KIND_INVALID", case_id=case_id)
        return
    if any(
        not isinstance(case.get(key), dict)
        for key in ("reference", "routing", "contract")
    ):
        _failure(
            result, layer="schema", code="ORACLE_CASE_CONTRACT_INVALID", case_id=case_id
        )
        return
    expected = _expected_contract(case.get("expected"), result=result, case_id=case_id)
    if expected is None:
        return
    actual = _evaluate_oracle_case(case)
    _compare_expectation(
        result=result,
        case_id=case_id,
        expected=expected,
        actual=actual,
    )
    if _case_kind_matches_actual(case_kind, actual):
        result.coverage.add((mechanism, case_kind))
    else:
        _failure(
            result,
            layer="coverage",
            code="CASE_KIND_SEMANTICS_MISMATCH",
            case_id=case_id,
            detail=(
                f"case_kind={case_kind},actual={actual.disposition},"
                f"codes={','.join(actual.failure_codes)}"
            ),
        )


def evaluate_fixture(path: Path) -> FixtureFileResult:
    result = FixtureFileResult(path=path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _failure(
            result, layer="json", code="JSON_NOT_READABLE", detail=type(error).__name__
        )
        return result
    result.json_readable = True
    if not isinstance(data, dict):
        _failure(result, layer="schema", code="FIXTURE_ROOT_INVALID")
        return result
    fixture_id = data.get("fixture_id")
    if not isinstance(fixture_id, str) or not fixture_id:
        _failure(result, layer="schema", code="FIXTURE_ID_INVALID")
        return result
    result.fixture_id = fixture_id
    if not isinstance(data.get("scenario"), str) or not data["scenario"].strip():
        _failure(result, layer="schema", code="SCENARIO_INVALID")
        return result

    if "oracle_cases" in data:
        cases = data["oracle_cases"]
        if not isinstance(cases, list) or not cases:
            _failure(result, layer="schema", code="ORACLE_CASES_INVALID")
            return result
        for case in cases:
            _validate_oracle_case(case, result=result)
    else:
        expected = _expected_contract(data.get("expected"), result=result, case_id=None)
        adapter = _LEGACY_ADAPTERS.get(fixture_id)
        if adapter is None:
            _failure(result, layer="schema", code="LEGACY_ADAPTER_UNSUPPORTED")
        elif expected is not None and _validate_legacy_shape(
            data, fixture_id=fixture_id, result=result
        ):
            try:
                actual = adapter(data)
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                _failure(
                    result,
                    layer="schema",
                    code="LEGACY_ADAPTER_INPUT_INVALID",
                    detail=type(error).__name__,
                )
            else:
                _compare_expectation(
                    result=result, case_id=None, expected=expected, actual=actual
                )

    result.schema_valid = not any(
        failure.layer in {"json", "schema"} for failure in result.failures
    )
    return result


def _root_failure_report(root: Path, code: str) -> OracleReport:
    return OracleReport(
        root=root,
        total_files=0,
        json_readable=0,
        schema_valid=0,
        expectation_total=0,
        expectation_passed=0,
        coverage={},
        failures=(Failure(layer="root", code=code, path=root.name or "."),),
    )


def run_oracle(root: Path) -> OracleReport:
    if not root.exists():
        return _root_failure_report(root, "FIXTURE_ROOT_NOT_FOUND")
    if not root.is_dir():
        return _root_failure_report(root, "FIXTURE_ROOT_NOT_DIRECTORY")
    paths = sorted(root.rglob("*.json"))
    if not paths:
        return _root_failure_report(root, "FIXTURE_ROOT_NO_JSON")
    results = [evaluate_fixture(path) for path in paths]
    failures = [failure for result in results for failure in result.failures]

    ids: dict[str, int] = {}
    for result in results:
        if result.fixture_id:
            ids[result.fixture_id] = ids.get(result.fixture_id, 0) + 1
    for fixture_id, count in sorted(ids.items()):
        if count > 1:
            failures.append(
                Failure(
                    layer="schema",
                    code="DUPLICATE_FIXTURE_ID",
                    path=root.name,
                    fixture_id=fixture_id,
                    detail=f"count={count}",
                )
            )

    coverage_mutable: dict[str, set[str]] = {}
    for result in results:
        for mechanism, case_kind in result.coverage:
            coverage_mutable.setdefault(mechanism, set()).add(case_kind)
    for mechanism in PRIMARY_MECHANISMS:
        missing = sorted(CASE_KINDS - coverage_mutable.get(mechanism, set()))
        if missing:
            failures.append(
                Failure(
                    layer="coverage",
                    code="COVERAGE_MISSING",
                    path=root.name,
                    fixture_id=mechanism,
                    detail=f"missing={','.join(missing)}",
                )
            )

    failures.sort(
        key=lambda item: (
            item.path,
            item.fixture_id or "",
            item.case_id or "",
            item.layer,
            item.code,
        )
    )
    return OracleReport(
        root=root,
        total_files=len(paths),
        json_readable=sum(result.json_readable for result in results),
        schema_valid=sum(result.schema_valid for result in results),
        expectation_total=sum(result.expectation_total for result in results),
        expectation_passed=sum(result.expectation_passed for result in results),
        coverage={
            key: frozenset(value) for key, value in sorted(coverage_mutable.items())
        },
        failures=tuple(failures),
    )
