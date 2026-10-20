#!/usr/bin/env python3
"""Validate the machine-readable handoff for viral-video-deep-insight.

This is a deliberately small, dependency-free contract check.  It validates
scope, evidence semantics, mechanism routing, claim binding, and decision
vocabulary; it does not decide whether a creative hypothesis is true.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

STATUS = {"blocked", "proceed_with_limits", "ready_for_next_gate"}
ACTIONS = {"revise", "collect_evidence", "test", "hold", "stop"}
PROOF_LEVELS = {"local", "CI", "private", "deployment", "live", "production"}
EVIDENCE_LEVELS = {"Fact", "Inference", "Unknown"}
MECHANISMS = {
    "narrative-transformation",
    "proof-demonstration",
    "experience-pov",
    "attention-grammar",
    "conversion-action",
    "trend-native",
}
MEASUREMENT_STATES = {
    "observed",
    "missing",
    "unknown",
    "not_reported",
    "not_collected",
    "source_ambiguous",
    "not_applicable",
    "redacted",
}
SUBJECT_RELATIONS = {
    "exact_snapshot",
    "reviewed_snapshot_selection",
    "reviewed_family_context",
    "unresolved",
    "conflict",
}
DIMENSION_STATES = {"observed", "inferred", "unknown", "blocked"}
TRANSFERABILITY = {"portable_function", "context_bound", "surface_bound", "unknown"}
DISPOSITIONS = {"cite", "recompute", "test", "reject"}
MEDIA_GATES = {
    "artifact_traceability",
    "technical_profile",
    "communicative_surface",
    "target_identity_continuity",
    "source_use_scope",
    "originality_delta",
}
MEDIA_GATE_STATES = {
    "not_applicable_pending_artifact",
    "preflight_evidence_collected",
    "evidence_collected_pending_artifact_review",
    "evidence_collected_for_internal_analysis_only",
    "blocked",
    "unavailable",
    "ready_for_next_gate",
}
CLAIM_STATES = {
    "confirmed",
    "locked",
    "reported_product_claim",
    "unsupported",
    "excluded",
    "unknown",
    "exact",
    "approved_paraphrase",
    "expired_promotion",
    "ambiguous",
    "not_a_product_claim",
}
REQUIRED_DIMENSIONS = {
    "source_context",
    "performance_signal",
    "audience_tension",
    "attention_grammar",
    "narrative_transformation",
    "proof_demonstration",
    "experience_pov",
    "conversion_action",
    "trend_native",
    "product_truth",
    "surface_originality",
    "experimentability",
    "media_integrity",
}

# These words are not banned when explicitly negated or scoped.  The check is
# intentionally conservative: an unqualified occurrence in an inference is a
# reason to edit the brief, not proof that the underlying work is wrong.
OVERCLAIM_TERMS = (
    "winner",
    "causal lift",
    "guaranteed",
    "viral formula",
    "必爆",
    "爆款公式",
    "因果提升",
    "普遍赢家",
)
QUALIFIERS = (
    "not",
    "no",
    "unproven",
    "hypothesis",
    "bounded",
    "仅",
    "只",
    "不",
    "未",
    "无法",
    "不能",
    "不得",
    "尚未",
    "未证",
    "不支持",
)


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def nonempty(value: Any, field: str) -> None:
    require(isinstance(value, str) and bool(value.strip()), f"{field} must be a non-empty string")


def check_overclaim(text: str, field: str) -> None:
    lowered = text.lower()
    for term in OVERCLAIM_TERMS:
        if term.lower() in lowered:
            # Look at a small local window so a sentence such as
            # “not a winner” remains allowed while “the winner” is rejected.
            index = lowered.index(term.lower())
            window = lowered[max(0, index - 28) : index + len(term) + 28]
            if not any(qualifier.lower() in window for qualifier in QUALIFIERS):
                raise ValidationError(f"{field} contains an unqualified overclaim: {term}")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON: {exc}") from exc
    require(isinstance(value, dict), "brief root must be an object")
    return value


def validate(data: dict[str, Any]) -> list[str]:
    required = {
        "schema_version",
        "status",
        "action",
        "decision_question",
        "evidence_level",
        "proof_level",
        "subject",
        "performance_window",
        "observations",
        "inferences",
        "primary_mechanism",
        "dimensions",
        "claims",
        "media_gates",
        "unknowns",
        "guardrails",
        "source_refs",
        "limitations",
    }
    missing = sorted(required - data.keys())
    require(not missing, f"missing top-level fields: {', '.join(missing)}")
    require(data["schema_version"] == "viral-video-deep-insight-v1", "unsupported schema_version")
    require(data["status"] in STATUS, f"status must be one of {sorted(STATUS)}")
    require(data["action"] in ACTIONS, f"action must be one of {sorted(ACTIONS)}")
    nonempty(data["decision_question"], "decision_question")
    require(data["evidence_level"] in EVIDENCE_LEVELS, f"evidence_level must be one of {sorted(EVIDENCE_LEVELS)}")
    require(data["proof_level"] in PROOF_LEVELS, f"proof_level must be one of {sorted(PROOF_LEVELS)}")

    subject = data["subject"]
    require(isinstance(subject, dict), "subject must be an object")
    for key in ("brand", "market", "product_family", "model", "variant", "binding_state"):
        require(key in subject, f"subject.{key} is required")
        nonempty(subject[key], f"subject.{key}")
    relation = subject["binding_state"]
    require(relation in SUBJECT_RELATIONS, f"subject.binding_state must be one of {sorted(SUBJECT_RELATIONS)}")
    if relation == "conflict":
        require(data["status"] == "blocked", "conflicting subject binding requires status=blocked")

    window = data["performance_window"]
    require(isinstance(window, dict), "performance_window must be an object")
    for key in ("platform", "start", "end", "source_ref", "source_digest"):
        require(key in window, f"performance_window.{key} is required")
    nonempty(window["source_ref"], "performance_window.source_ref")
    nonempty(window["source_digest"], "performance_window.source_digest")

    observations = data["observations"]
    require(isinstance(observations, list) and observations, "observations must be a non-empty list")
    observation_ids: set[str] = set()
    require(isinstance(data["source_refs"], list) and data["source_refs"], "source_refs must be a non-empty list")
    require(all(isinstance(ref, str) and ref.strip() for ref in data["source_refs"]), "source_refs must contain non-empty strings")
    source_refs = set(data["source_refs"])
    for index, observation in enumerate(observations):
        require(isinstance(observation, dict), f"observations[{index}] must be an object")
        for key in ("id", "text", "source_ref", "availability"):
            require(key in observation, f"observations[{index}].{key} is required")
        nonempty(observation["id"], f"observations[{index}].id")
        nonempty(observation["text"], f"observations[{index}].text")
        require(observation["id"] not in observation_ids, f"duplicate observation id: {observation['id']}")
        observation_ids.add(observation["id"])
        require(
            observation["availability"] != "observed_zero",
            "use availability=observed and value=0; observed_zero is prose only",
        )
        require(observation["availability"] in MEASUREMENT_STATES, f"observations[{index}].availability is invalid")
        require(observation["source_ref"] in source_refs, f"observations[{index}] references undeclared source_ref")
        if observation["availability"] == "observed":
            require("value" in observation and observation["value"] is not None, f"observations[{index}] observed values need value (0 is valid)")
        elif "value" in observation:
            require(observation["value"] is None, f"observations[{index}] non-observed value must be null")

    inferences = data["inferences"]
    require(isinstance(inferences, list) and inferences, "inferences must be a non-empty list")
    inference_ids: set[str] = set()
    for index, inference in enumerate(inferences):
        require(isinstance(inference, dict), f"inferences[{index}] must be an object")
        for key in ("id", "text", "supporting_observation_ids", "disposition", "alternative_explanation"):
            require(key in inference, f"inferences[{index}].{key} is required")
        nonempty(inference["id"], f"inferences[{index}].id")
        require(inference["id"] not in inference_ids, f"duplicate inference id: {inference['id']}")
        inference_ids.add(inference["id"])
        nonempty(inference["text"], f"inferences[{index}].text")
        check_overclaim(inference["text"], f"inferences[{index}].text")
        require(inference["disposition"] in DISPOSITIONS, f"inferences[{index}].disposition is invalid")
        require(isinstance(inference["supporting_observation_ids"], list) and inference["supporting_observation_ids"], f"inferences[{index}] needs supporting observations")
        require(set(inference["supporting_observation_ids"]).issubset(observation_ids), f"inferences[{index}] references unknown observation")
        nonempty(inference["alternative_explanation"], f"inferences[{index}].alternative_explanation")

    mechanism = data["primary_mechanism"]
    require(mechanism in MECHANISMS or mechanism == "primary_mechanism_ambiguous", "invalid primary_mechanism")
    if mechanism == "primary_mechanism_ambiguous":
        require(data["status"] == "blocked", "ambiguous primary mechanism requires status=blocked")

    dimensions = data["dimensions"]
    require(isinstance(dimensions, list), "dimensions must be a list")
    dimension_map: dict[str, dict[str, Any]] = {}
    for index, dimension in enumerate(dimensions):
        require(isinstance(dimension, dict), f"dimensions[{index}] must be an object")
        for key in ("key", "evidence_state", "transferability", "next_test"):
            require(key in dimension, f"dimensions[{index}].{key} is required")
        key = dimension["key"]
        require(key in REQUIRED_DIMENSIONS, f"unknown dimension key: {key}")
        require(key not in dimension_map, f"duplicate dimension key: {key}")
        dimension_map[key] = dimension
        require(dimension["evidence_state"] in DIMENSION_STATES, f"dimensions[{index}].evidence_state is invalid")
        require(dimension["transferability"] in TRANSFERABILITY, f"dimensions[{index}].transferability is invalid")
        nonempty(dimension["next_test"], f"dimensions[{index}].next_test")
    require(REQUIRED_DIMENSIONS.issubset(dimension_map), f"missing dimensions: {', '.join(sorted(REQUIRED_DIMENSIONS - dimension_map.keys()))}")
    if data["status"] == "ready_for_next_gate":
        require(not any(item["evidence_state"] == "blocked" for item in dimensions), "ready_for_next_gate cannot contain blocked dimensions")

    media_gates = data["media_gates"]
    require(isinstance(media_gates, list), "media_gates must be a list")
    media_gate_map: dict[str, dict[str, Any]] = {}
    for index, gate in enumerate(media_gates):
        require(isinstance(gate, dict), f"media_gates[{index}] must be an object")
        for key in ("key", "state", "evidence"):
            require(key in gate, f"media_gates[{index}].{key} is required")
        require(gate["key"] in MEDIA_GATES, f"unknown media gate: {gate['key']}")
        require(gate["key"] not in media_gate_map, f"duplicate media gate: {gate['key']}")
        media_gate_map[gate["key"]] = gate
        require(gate["state"] in MEDIA_GATE_STATES, f"media_gates[{index}].state is invalid")
        nonempty(gate["evidence"], f"media_gates[{index}].evidence")
    require(MEDIA_GATES.issubset(media_gate_map), f"missing media gates: {', '.join(sorted(MEDIA_GATES - media_gate_map.keys()))}")
    if data["status"] == "ready_for_next_gate":
        require(
            relation not in {"unresolved", "conflict"},
            "ready_for_next_gate requires a reviewed subject relation",
        )
        require(
            not any(gate["state"] in {"blocked", "unavailable"} for gate in media_gates),
            "ready_for_next_gate cannot contain blocked or unavailable media gates",
        )

    claims = data["claims"]
    require(isinstance(claims, list), "claims must be a list")
    accepted_snapshot_ids: set[str] = set()
    for index, claim in enumerate(claims):
        require(isinstance(claim, dict), f"claims[{index}] must be an object")
        for key in ("id", "state"):
            require(key in claim, f"claims[{index}].{key} is required")
        require(claim["state"] in CLAIM_STATES, f"claims[{index}].state is invalid")
        if claim["state"] in {"confirmed", "locked", "approved_paraphrase", "exact"}:
            nonempty(claim.get("fact_id"), f"claims[{index}].fact_id")
            nonempty(claim.get("snapshot_id"), f"claims[{index}].snapshot_id")
            accepted_snapshot_ids.add(claim["snapshot_id"])
    require(
        len(accepted_snapshot_ids) <= 1,
        "accepted product claims must bind to one Product Snapshot",
    )
    if data["status"] == "ready_for_next_gate":
        require(
            not any(claim["state"] in {"unsupported", "excluded", "expired_promotion", "ambiguous"} for claim in claims),
            "ready_for_next_gate cannot contain unresolved product claims",
        )

    require(isinstance(data["unknowns"], list), "unknowns must be a list")
    require(isinstance(data["guardrails"], list) and data["guardrails"], "guardrails must be a non-empty list")
    require(isinstance(data["limitations"], list), "limitations must be a list")
    changed_dimension = data.get("changed_creative_dimension", "")
    if data["action"] == "test":
        nonempty(changed_dimension, "changed_creative_dimension")
    require(changed_dimension != "ship", "ship is not an allowed action or creative dimension")

    # Reject accidental private material in machine handoff.
    serialised = json.dumps(data, ensure_ascii=False).lower()
    for marker in ("file://", "authorization:", "cookie:", "api_key", "secret_key", "private_url"):
        require(marker not in serialised, f"machine handoff contains prohibited sensitive marker: {marker}")

    return [
        "schema and required fields",
        "subject/window and measurement semantics",
        "single primary mechanism and complete dimension matrix",
        "claim binding and evidence-scoped action",
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_insight_brief.py <brief.json>", file=sys.stderr)
        return 2
    try:
        checks = validate(load(Path(argv[1])))
    except ValidationError as exc:
        print(f"INVALID: {exc}")
        return 1
    print("VALID: " + "; ".join(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
