from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from tools.viral_replication.artifact_contracts import (
    ArtifactValidationError,
    bind_artifact_digest,
    get_artifact_schema,
    validate_artifact,
    validate_artifact_chain,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
TASK_REF = "task-001"
RUN_REF = "run-001"
JSONDict = dict[str, Any]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def envelope(*, artifact_type: str, schema_version: str, artifact_id: str) -> JSONDict:
    return {
        "schema_version": schema_version,
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "task_ref": TASK_REF,
        "run_ref": RUN_REF,
        "version": 1,
        "status": "validated",
        "input_refs": [],
        "source_refs": [],
        "subject_binding": {
            "state": "unresolved",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "market": "US",
            "locale": "en-US",
            "limitations": ["A target Product Snapshot has not been selected."],
        },
        "evidence_level": "inference",
        "proof_level": "local",
        "limitations": ["Local artifact contract only."],
        "created_at": "2026-10-21T00:00:00Z",
        "supersedes_artifact_id": None,
    }


def artifact_ref(artifact: JSONDict) -> JSONDict:
    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact["artifact_type"],
        "task_ref": artifact["task_ref"],
        "run_ref": artifact["run_ref"],
        "version": artifact["version"],
        "content_digest": artifact["content_digest"],
    }


def external_ref(
    *, artifact_type: str, artifact_id: str, digest: str = SHA_B
) -> JSONDict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "task_ref": TASK_REF,
        "run_ref": RUN_REF,
        "version": 1,
        "content_digest": digest,
    }


def reference_bundle_payload() -> JSONDict:
    return {
        "schema_version": "sv.reference-bundle.v1",
        "artifact_id": "reference-bundle-001",
        "artifact_type": "reference_bundle",
        "task_ref": TASK_REF,
        "run_ref": RUN_REF,
        "version": 1,
        "status": "validated",
        "input_refs": [],
        "source_refs": [
            {
                "source_ref": "source-001",
                "source_kind": "public_url",
                "source_digest": SHA_A,
            }
        ],
        "subject_binding": {
            "state": "unresolved",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "market": "US",
            "locale": "en-US",
            "limitations": ["A target Product Snapshot has not been selected."],
        },
        "evidence_level": "fact",
        "proof_level": "local",
        "limitations": ["The source exposes no collection method."],
        "created_at": "2026-10-21T00:00:00Z",
        "supersedes_artifact_id": None,
        "reference_id": "reference-001",
        "source_locator": "https://example.test/video/001",
        "source_digest": SHA_A,
        "platform": "tiktok",
        "performance_window": {
            "start": "2026-10-01",
            "end": "2026-10-07",
            "timezone": "UTC",
        },
        "captured_at": "2026-10-21T00:00:00Z",
        "rights_state": "analysis_only",
        "playability_state": "playable",
        "candidate_state": "candidate",
        "observations": [
            {
                "observation_ref": "views-001",
                "metric": "views",
                "state": "observed",
                "value": 0,
                "unit": "count",
                "source_refs": ["source-001"],
            }
        ],
    }


def decomposition_payload(reference: JSONDict) -> JSONDict:
    payload = envelope(
        artifact_type="decomposition_map",
        schema_version="sv.decomposition-map.v1",
        artifact_id="decomposition-map-001",
    )
    payload["input_refs"] = [artifact_ref(reference)]
    payload.update(
        {
            "reference_bundle_ref": artifact_ref(reference),
            "timeline": [
                {
                    "start_seconds": 0,
                    "end_seconds": 2.5,
                    "dimension": "hook",
                    "observation": "The outcome is withheld during the opening beat.",
                    "availability": "observed",
                    "source_refs": ["source-001"],
                }
            ],
            "primary_mechanism": "attention-grammar",
            "secondary_mechanisms": [],
            "mechanism_observations": attention_decomposition_observations(),
            "unsupported_claims": [],
            "unknowns": ["Retention is not reported."],
        }
    )
    return payload


def attention_decomposition_observations() -> JSONDict:
    return {
        "mechanism": "attention-grammar",
        "pattern_identity": {
            "pattern_key": "delayed-reveal",
            "pattern_version": 1,
        },
        "observations": [
            {
                "component": "hook_trigger",
                "start_seconds": 0,
                "end_seconds": 2.5,
                "carrier": "opening-shot",
                "observable_function": "withhold outcome",
                "surface_modality": "visual",
                "surface_disposition": "replaceable",
                "source_refs": ["source-001"],
                "availability": "observed",
                "shot_or_phase_anchor": "shot-01",
            }
        ],
    }


def conversion_decomposition_observations() -> JSONDict:
    components = (
        "objection_resolution",
        "promotion_contract",
        "cta_invitation",
        "action_path",
    )
    return {
        "mechanism": "conversion-action",
        "reference_surface_is_target_copy": False,
        "observations": [
            {
                "component": component,
                "start_seconds": index * 2.0,
                "end_seconds": (index + 1) * 2.0,
                "observable_function": f"Observe {component} without reusing copy.",
                "surface_modality": "text",
                "surface_disposition": "replaceable",
                "availability": "observed",
                "source_refs": [f"source-{index + 1:03d}"],
                "unknowns": [],
            }
            for index, component in enumerate(components)
        ],
    }


def trend_decomposition_observations() -> JSONDict:
    components = (
        "trend_signal_binding",
        "trend_semantic_frame",
        "template_grammar",
        "audio_function",
    )
    return {
        "mechanism": "trend-native",
        "observations": [
            {
                "component": component,
                "start_seconds": index * 2.0,
                "end_seconds": (index + 1) * 2.0,
                "observable_function": f"Observe bounded {component} evidence.",
                "surface_modality": "mixed",
                "surface_disposition": "prohibited",
                "availability": "observed",
                "source_refs": [f"source-{index + 1:03d}"],
                "unknowns": [],
            }
            for index, component in enumerate(components)
        ],
        "source_reuse_boundary": {
            "source_identity": "excluded_from_target",
            "source_audio": "requires_separate_evidence",
            "source_template": "analysis_only",
            "target_execution_inclusion": False,
        },
    }


def narrative_decomposition_observations() -> JSONDict:
    return {
        "mechanism": "narrative-transformation",
        "beats": [
            {
                "role": "pain_tension",
                "start_seconds": 0,
                "end_seconds": 3,
                "observable_function": "Establish a bounded caregiving tension.",
                "surface_expression": "A caregiver pauses during the routine.",
                "surface_disposition": "replaceable",
                "availability": "observed",
                "source_refs": ["source-001"],
            }
        ],
    }


def proof_decomposition_observations() -> JSONDict:
    return {
        "mechanism": "proof-demonstration",
        "steps": [
            {
                "phase": "measurement",
                "start_seconds": 1,
                "end_seconds": 4,
                "proof_device": "visible bounded comparison",
                "observable_function": "Expose the measured difference.",
                "observed_phenomenon": "The displayed values differ.",
                "allowed_conclusion": "Only the displayed values are observable.",
                "availability": "observed",
                "source_refs": ["source-001"],
                "limitations": ["No universal performance claim."],
            }
        ],
    }


def experience_decomposition_observations() -> JSONDict:
    return {
        "mechanism": "experience-pov",
        "cues": [
            {
                "cue_type": "sensory",
                "start_seconds": 0,
                "end_seconds": 3,
                "observable_function": "Establish a quiet tactile moment.",
                "surface_expression": "Close view of a caregiver hand movement.",
                "replaceable_fields": ["performer", "setting"],
                "availability": "observed",
                "source_refs": ["source-001"],
            }
        ],
    }


def hypothesis_payload(decomposition: JSONDict) -> JSONDict:
    payload = envelope(
        artifact_type="pattern_hypothesis",
        schema_version="sv.pattern-hypothesis.v1",
        artifact_id="pattern-hypothesis-001",
    )
    payload["input_refs"] = [artifact_ref(decomposition)]
    payload.update(
        {
            "decomposition_map_ref": artifact_ref(decomposition),
            "primary_mechanism": "attention-grammar",
            "hypothesis": "Delayed reveal may increase opening attention.",
            "invariant_elements": ["withhold the outcome in the opening beat"],
            "replaceable_elements": ["setting", "performer"],
            "prohibited_elements": ["copying creator identity"],
            "adaptation_constraints": ["Preserve Product Truth boundaries."],
            "evidence_scope": ["One locally reviewed reference."],
            "unknowns": ["No retention curve is available."],
        }
    )
    return payload


def plan_payload(hypothesis: JSONDict, reference: JSONDict) -> JSONDict:
    payload = envelope(
        artifact_type="replication_plan",
        schema_version="sv.replication-plan.v1",
        artifact_id="replication-plan-001",
    )
    payload["input_refs"] = [artifact_ref(hypothesis), artifact_ref(reference)]
    payload.update(
        {
            "pattern_hypothesis_ref": artifact_ref(hypothesis),
            "control_reference_ref": artifact_ref(reference),
            "primary_mechanism": "attention-grammar",
            "selected_component": "hook_trigger",
            "control_id": "control-001",
            "variant_id": "variant-001",
            "changed_dimension": "opening reveal timing",
            "frozen_components": [
                "reveal_cadence",
                "caption_cadence",
                "visual_contrast",
                "sonic_timing",
            ],
            "target_platform": "tiktok",
            "target_duration_seconds": 20,
            "execution_budget": {
                "max_variants": 1,
                "max_iterations": 2,
                "max_duration_seconds": 30,
                "stop_on_violation": True,
            },
            "stop_conditions": ["A selected Product Truth fact becomes stale."],
            "acceptance_gates": ["Human approves the immutable contract."],
            "rights_state": "analysis_only",
            "requires_human_approval": True,
        }
    )
    return payload


def fact_map_payload(plan: JSONDict) -> JSONDict:
    payload = envelope(
        artifact_type="fact_map",
        schema_version="sv.fact-map.v1",
        artifact_id="fact-map-001",
    )
    payload["input_refs"] = [artifact_ref(plan)]
    payload["subject_binding"] = {
        "state": "exact_snapshot",
        "product_snapshot_id": "snapshot-001",
        "product_snapshot_digest": SHA_A,
        "market": "US",
        "locale": "en-US",
        "limitations": [],
    }
    payload.update(
        {
            "replication_plan_ref": artifact_ref(plan),
            "claim_scope": "product_claims",
            "product_snapshot_id": "snapshot-001",
            "product_snapshot_digest": SHA_A,
            "claim_mappings": [
                {
                    "claim_id": "claim-001",
                    "claim_text": "Use the confirmed comfort statement.",
                    "disposition": "bind",
                    "fact_id": "fact-001",
                    "fact_status": "confirmed",
                    "evidence_refs": ["fact-evidence-001"],
                    "reason": None,
                },
                {
                    "claim_id": "claim-002",
                    "claim_text": "A performance superlative from the reference.",
                    "disposition": "exclude",
                    "fact_id": "fact-002",
                    "fact_status": "unconfirmed",
                    "evidence_refs": [],
                    "reason": "The fact is not confirmed or locked.",
                },
            ],
            "selected_fact_ids": ["fact-001"],
            "excluded_fact_ids": ["fact-002"],
            "unsupported_claims": ["Performance superlative is excluded."],
        }
    )
    return payload


def no_product_fact_map_payload(plan: JSONDict) -> JSONDict:
    payload = fact_map_payload(plan)
    payload.update(
        {
            "claim_scope": "no_product_claims",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "claim_mappings": [],
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
            "unsupported_claims": [],
            "subject_binding": {
                "state": "not_applicable",
                "product_snapshot_id": None,
                "product_snapshot_digest": None,
                "market": "US",
                "locale": "en-US",
                "limitations": ["Brand Voice task has no product claims."],
            },
        }
    )
    return payload


def contract_payload(
    plan: JSONDict,
    fact_map: JSONDict,
    decomposition: JSONDict,
) -> JSONDict:
    payload = envelope(
        artifact_type="replication_contract",
        schema_version="sv.replication-contract.v1",
        artifact_id="replication-contract-001",
    )
    payload["status"] = "approved"
    payload["input_refs"] = [
        artifact_ref(plan),
        artifact_ref(fact_map),
        artifact_ref(decomposition),
    ]
    payload["subject_binding"] = fact_map["subject_binding"]
    payload.update(
        {
            "replication_plan_ref": artifact_ref(plan),
            "fact_map_ref": artifact_ref(fact_map),
            "decomposition_map_ref": artifact_ref(decomposition),
            "primary_mechanism": "attention-grammar",
            "selected_component": "hook_trigger",
            "frozen_components": [
                "reveal_cadence",
                "caption_cadence",
                "visual_contrast",
                "sonic_timing",
            ],
            "claim_scope": fact_map["claim_scope"],
            "control_id": "control-001",
            "variant_id": "variant-001",
            "changed_dimension": "opening reveal timing",
            "frozen_configuration": {
                "language": "en-US",
                "market": "US",
                "platform": "tiktok",
                "duration_seconds": 20,
                "model": "document-only",
                "material_scope": ["target-assets-only"],
                "execution_budget": {
                    "max_variants": 1,
                    "max_iterations": 2,
                    "max_duration_seconds": 30,
                    "stop_on_violation": True,
                },
            },
            "selected_fact_ids": fact_map["selected_fact_ids"],
            "excluded_fact_ids": fact_map["excluded_fact_ids"],
            "stop_conditions": ["A selected Product Truth fact becomes stale."],
            "acceptance_gates": ["Human approves the immutable contract."],
            "rights_state": "analysis_only",
            "approval_ref": "approval-001",
            "immutable": True,
        }
    )
    return payload


def adaptation_payload(contract: JSONDict) -> JSONDict:
    payload = envelope(
        artifact_type="adaptation_package",
        schema_version="sv.adaptation-package.v1",
        artifact_id="adaptation-package-001",
    )
    payload["input_refs"] = [artifact_ref(contract)]
    payload["subject_binding"] = contract["subject_binding"]
    payload.update(
        {
            "replication_contract_ref": artifact_ref(contract),
            "primary_mechanism": "attention-grammar",
            "selected_component": "hook_trigger",
            "mechanism_payload": {
                "mechanism": "attention-grammar",
                "component": "hook_trigger",
                "hook_trigger": "Open on an unresolved caregiving moment.",
                "reveal_cadence": "Reveal the practical outcome after the first beat.",
                "caption_cadence": "One short caption per beat.",
                "visual_contrast": "Calm after visible friction.",
                "sonic_timing": "Use sound only as a beat marker.",
                "frozen_components": [
                    "reveal_cadence",
                    "caption_cadence",
                    "visual_contrast",
                    "sonic_timing",
                ],
                "anchors": [
                    {
                        "component": "hook_trigger",
                        "start_seconds": 0,
                        "end_seconds": 2.5,
                        "carrier": "opening-shot",
                        "observable_function": "withhold outcome",
                        "surface_class": "visual",
                        "source_ref": "source-001",
                        "availability": "observed",
                        "shot_or_phase_anchor": "shot-01",
                    }
                ],
                "pattern_identity": {
                    "pattern_key": "delayed-reveal",
                    "pattern_version": 1,
                },
                "target_surface_substitutions": ["Use target-owned visual surfaces."],
                "sound_policy": "functional_substitution",
            },
        }
    )
    return payload


def media_integrity_payload(contract: JSONDict, adaptation: JSONDict) -> JSONDict:
    payload = envelope(
        artifact_type="media_integrity_record",
        schema_version="sv.media-integrity-record.v1",
        artifact_id="media-integrity-record-001",
    )
    payload["status"] = "final_with_limits"
    script_ref = external_ref(
        artifact_type="script_version", artifact_id="script-version-001"
    )
    payload["input_refs"] = [
        artifact_ref(contract),
        artifact_ref(adaptation),
        script_ref,
    ]
    payload["subject_binding"] = contract["subject_binding"]
    payload.update(
        {
            "replication_contract_ref": artifact_ref(contract),
            "adaptation_package_ref": artifact_ref(adaptation),
            "script_version_ref": script_ref,
            "storyboard_version_ref": None,
            "storyboard_lineage": None,
            "controlled_artifact_ref": None,
            "mode": "preflight",
            "gate_checks": [
                {
                    "gate": gate,
                    "state": "not_applicable_pending_artifact",
                    "findings": ["No rendered media artifact exists."],
                    "evidence_refs": [],
                    "blockers": [],
                    "unknowns": ["Rendered-media properties are not observable."],
                    "fallback_strategy": ["Review the controlled media artifact."],
                }
                for gate in (
                    "artifact_traceability",
                    "technical_profile",
                    "communicative_surface",
                    "target_identity_continuity",
                    "source_use_scope",
                    "originality_delta",
                )
            ],
            "disposition": "proceed_with_limits",
            "fallback_strategy": ["Require artifact review after external rendering."],
            "blockers": [],
            "unknowns": ["Rendered-media properties are not observable."],
            "evidence_limits": ["Preflight is not final media acceptance."],
        }
    )
    return payload


def reviewed_media_integrity_payload(
    contract: JSONDict, adaptation: JSONDict
) -> JSONDict:
    payload = media_integrity_payload(contract, adaptation)
    storyboard_ref = external_ref(
        artifact_type="storyboard_version", artifact_id="storyboard-version-001"
    )
    controlled_ref = external_ref(
        artifact_type="controlled_media", artifact_id="controlled-media-001"
    )
    payload["mode"] = "artifact_review"
    payload["storyboard_version_ref"] = storyboard_ref
    payload["storyboard_lineage"] = {
        "storyboard_version_ref": dict(storyboard_ref),
        "source_script_version_ref": dict(payload["script_version_ref"]),
        "evidence_scope": "declared_artifact_lineage",
    }
    payload["controlled_artifact_ref"] = controlled_ref
    payload["input_refs"].extend((storyboard_ref, controlled_ref))
    payload["disposition"] = "ready_for_next_gate"
    payload["unknowns"] = []
    payload["blockers"] = []
    for gate in payload["gate_checks"]:
        gate.update(
            {
                "state": "passed",
                "findings": ["Controlled artifact passed the gate."],
                "evidence_refs": [f"{gate['gate']}-evidence-001"],
                "blockers": [],
                "unknowns": [],
                "fallback_strategy": [],
            }
        )
    return payload


def finding_payload(
    contract: JSONDict,
    adaptation: JSONDict,
    integrity: JSONDict,
) -> JSONDict:
    payload = envelope(
        artifact_type="replication_finding",
        schema_version="sv.replication-finding.v1",
        artifact_id="replication-finding-001",
    )
    payload["status"] = "final_with_limits"
    payload["input_refs"] = [
        artifact_ref(contract),
        artifact_ref(adaptation),
        artifact_ref(integrity),
    ]
    payload["subject_binding"] = contract["subject_binding"]
    payload.update(
        {
            "replication_contract_ref": artifact_ref(contract),
            "adaptation_package_ref": artifact_ref(adaptation),
            "media_integrity_record_ref": artifact_ref(integrity),
            "conclusion_scope": "local_fixture",
            "observations": [
                {
                    "observation_ref": "fixture-check-001",
                    "metric": "contract_conformance",
                    "state": "observed",
                    "value": True,
                    "unit": None,
                    "source_refs": ["replication-contract-001"],
                }
            ],
            "bounded_inferences": ["The package is structurally conformant."],
            "unknowns": ["No rendered media or live outcome was inspected."],
            "anomalies": [],
            "next_actions": ["Run artifact review after external rendering."],
            "causal_claim": False,
            "production_acceptance": False,
        }
    )
    return payload


class ArtifactContractTests(unittest.TestCase):
    def test_task_and_run_refs_are_required(self) -> None:
        payload = reference_bundle_payload()
        payload["task_ref"] = None
        payload["run_ref"] = None

        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)

        self.assertEqual(caught.exception.code, "ARTIFACT_TASK_RUN_REQUIRED")

        reference = bind_artifact_digest(reference_bundle_payload())
        nested = decomposition_payload(reference)
        nested["input_refs"][0]["task_ref"] = ""
        nested["reference_bundle_ref"]["task_ref"] = ""
        with self.assertRaises(ArtifactValidationError) as nested_error:
            bind_artifact_digest(nested)
        self.assertEqual(nested_error.exception.code, "ARTIFACT_TASK_RUN_REQUIRED")

    def test_direct_refs_require_the_expected_type_and_same_task_run(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())

        wrong_type = decomposition_payload(reference)
        wrong_type["reference_bundle_ref"]["artifact_type"] = "fact_map"
        with self.assertRaises(ArtifactValidationError) as type_error:
            bind_artifact_digest(wrong_type)
        self.assertEqual(type_error.exception.code, "DIRECT_REF_TYPE_INVALID")

        wrong_scope = decomposition_payload(reference)
        wrong_scope["reference_bundle_ref"]["run_ref"] = "run-other"
        with self.assertRaises(ArtifactValidationError) as scope_error:
            bind_artifact_digest(wrong_scope)
        self.assertEqual(scope_error.exception.code, "ARTIFACT_REF_SCOPE_MISMATCH")

    def test_reference_bundle_binds_and_validates_a_canonical_digest(self) -> None:
        artifact = bind_artifact_digest(reference_bundle_payload())

        validated = validate_artifact(artifact, expected_type="reference_bundle")
        schema = get_artifact_schema("reference_bundle")

        self.assertEqual(validated["content_digest"], artifact["content_digest"])
        self.assertEqual(len(str(artifact["content_digest"])), 64)
        self.assertEqual(validated["task_ref"], TASK_REF)
        self.assertEqual(validated["run_ref"], RUN_REF)
        self.assertEqual(validated["observations"][0]["state"], "observed")
        self.assertEqual(schema["additionalProperties"], False)

    def test_decomposition_map_retains_timed_observations_and_one_primary_mechanism(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        payload = decomposition_payload(reference)
        payload["mechanism_observations"] = attention_decomposition_observations()
        artifact = bind_artifact_digest(payload)

        self.assertEqual(
            validate_artifact(artifact)["primary_mechanism"], "attention-grammar"
        )
        self.assertEqual(
            artifact["mechanism_observations"]["observations"][0]["carrier"],
            "opening-shot",
        )

        del payload["mechanism_observations"]["pattern_identity"]
        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)
        self.assertEqual(caught.exception.code, "DECOMPOSITION_OBSERVATIONS_INVALID")

    def test_decomposition_ambiguous_route_has_no_mechanism_observations(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        ambiguous = decomposition_payload(reference)
        ambiguous["primary_mechanism"] = None
        ambiguous["mechanism_observations"] = None

        artifact = bind_artifact_digest(ambiguous)
        self.assertIsNone(artifact["mechanism_observations"])

        missing = decomposition_payload(reference)
        missing["mechanism_observations"] = None
        with self.assertRaises(ArtifactValidationError) as missing_error:
            bind_artifact_digest(missing)
        self.assertEqual(
            missing_error.exception.code, "DECOMPOSITION_MECHANISM_MISMATCH"
        )

        ambiguous["mechanism_observations"] = attention_decomposition_observations()
        with self.assertRaises(ArtifactValidationError) as ambiguous_error:
            bind_artifact_digest(ambiguous)
        self.assertEqual(
            ambiguous_error.exception.code, "DECOMPOSITION_MECHANISM_MISMATCH"
        )

    def test_conversion_decomposition_separates_all_four_components(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        payload = decomposition_payload(reference)
        payload["primary_mechanism"] = "conversion-action"
        payload["mechanism_observations"] = conversion_decomposition_observations()

        artifact = bind_artifact_digest(payload)
        components = {
            observation["component"]
            for observation in artifact["mechanism_observations"]["observations"]
        }
        self.assertEqual(
            components,
            {
                "objection_resolution",
                "promotion_contract",
                "cta_invitation",
                "action_path",
            },
        )

        payload["mechanism_observations"]["observations"].pop()
        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)
        self.assertEqual(caught.exception.code, "DECOMPOSITION_OBSERVATIONS_INVALID")

    def test_trend_decomposition_closes_reuse_and_execution_boundaries(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        payload = decomposition_payload(reference)
        payload["primary_mechanism"] = "trend-native"
        payload["mechanism_observations"] = trend_decomposition_observations()

        artifact = bind_artifact_digest(payload)
        self.assertFalse(
            artifact["mechanism_observations"]["source_reuse_boundary"][
                "target_execution_inclusion"
            ]
        )

        payload["mechanism_observations"]["source_reuse_boundary"][
            "target_execution_inclusion"
        ] = True
        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)
        self.assertEqual(caught.exception.code, "DECOMPOSITION_OBSERVATIONS_INVALID")

        duplicate = decomposition_payload(reference)
        duplicate["primary_mechanism"] = "trend-native"
        duplicate["mechanism_observations"] = trend_decomposition_observations()
        duplicate["mechanism_observations"]["observations"][-1]["component"] = (
            "template_grammar"
        )
        with self.assertRaises(ArtifactValidationError) as duplicate_error:
            bind_artifact_digest(duplicate)
        self.assertEqual(
            duplicate_error.exception.code, "DECOMPOSITION_OBSERVATIONS_INVALID"
        )

    def test_narrative_proof_and_experience_use_closed_decomposition_payloads(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        cases = (
            ("narrative-transformation", narrative_decomposition_observations()),
            ("proof-demonstration", proof_decomposition_observations()),
            ("experience-pov", experience_decomposition_observations()),
        )
        for mechanism, observations in cases:
            with self.subTest(mechanism=mechanism):
                payload = decomposition_payload(reference)
                payload["artifact_id"] = f"decomposition-{mechanism}"
                payload["primary_mechanism"] = mechanism
                payload["mechanism_observations"] = observations
                artifact = bind_artifact_digest(payload)
                self.assertEqual(
                    artifact["mechanism_observations"]["mechanism"], mechanism
                )

        mismatch = decomposition_payload(reference)
        mismatch["primary_mechanism"] = "proof-demonstration"
        mismatch["mechanism_observations"] = narrative_decomposition_observations()
        with self.assertRaises(ArtifactValidationError) as mismatch_error:
            bind_artifact_digest(mismatch)
        self.assertEqual(
            mismatch_error.exception.code, "DECOMPOSITION_MECHANISM_MISMATCH"
        )

        free_form = decomposition_payload(reference)
        free_form["mechanism_observations"] = {
            "mechanism": "attention-grammar",
            "summary": "free-form evidence is not allowed",
        }
        with self.assertRaises(ArtifactValidationError) as free_form_error:
            bind_artifact_digest(free_form)
        self.assertEqual(
            free_form_error.exception.code, "DECOMPOSITION_OBSERVATIONS_INVALID"
        )

    def test_all_nine_canonical_artifacts_have_closed_machine_readable_schemas(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))
        integrity = bind_artifact_digest(
            reviewed_media_integrity_payload(contract, adaptation)
        )
        finding = bind_artifact_digest(finding_payload(contract, adaptation, integrity))
        artifacts = (
            reference,
            decomposition,
            hypothesis,
            plan,
            fact_map,
            contract,
            adaptation,
            integrity,
            finding,
        )

        self.assertEqual(
            {str(artifact["artifact_type"]) for artifact in artifacts},
            {
                "reference_bundle",
                "decomposition_map",
                "pattern_hypothesis",
                "replication_plan",
                "fact_map",
                "replication_contract",
                "adaptation_package",
                "media_integrity_record",
                "replication_finding",
            },
        )
        for artifact in artifacts:
            with self.subTest(artifact_type=artifact["artifact_type"]):
                artifact_type = str(artifact["artifact_type"])
                self.assertEqual(validate_artifact(artifact), artifact)
                self.assertFalse(
                    get_artifact_schema(artifact_type)["additionalProperties"]
                )

    def test_adaptation_package_accepts_exactly_one_matching_typed_payload(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        payload = adaptation_payload(contract)

        artifact = bind_artifact_digest(payload)

        self.assertEqual(
            artifact["mechanism_payload"]["mechanism"], "attention-grammar"
        )
        payload["secondary_payload"] = payload["mechanism_payload"]
        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)
        self.assertEqual(
            caught.exception.code, "ADAPTATION_PAYLOAD_CARDINALITY_INVALID"
        )

    def test_attention_payload_requires_closed_anchor_and_pattern_identity(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))

        artifact = bind_artifact_digest(adaptation_payload(contract))

        self.assertEqual(
            artifact["mechanism_payload"]["pattern_identity"]["pattern_key"],
            "delayed-reveal",
        )

    def test_each_primary_mechanism_has_a_closed_typed_adaptation_payload(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        payloads: dict[str, JSONDict] = {
            "narrative-transformation": {
                "mechanism": "narrative-transformation",
                "component": "narrative_arc",
                "frozen_components": [],
                "source_arc": ["tension", "reveal"],
                "transformed_arc": ["care moment", "bounded resolution"],
                "preserved_truths": ["confirmed fact only"],
            },
            "proof-demonstration": {
                "mechanism": "proof-demonstration",
                "component": "proof_device",
                "frozen_components": [],
                "proof_setup": "Show a bounded, observable setup.",
                "observable_result": "Record only what the artifact visibly supports.",
                "boundary_disclosures": ["Not a universal outcome."],
            },
            "experience-pov": {
                "mechanism": "experience-pov",
                "component": "experience_pov",
                "frozen_components": [],
                "pov_actor": "caregiver",
                "moment": "night routine",
                "sensory_cues": ["quiet room"],
            },
            "attention-grammar": {
                "mechanism": "attention-grammar",
                "component": "hook_trigger",
                "frozen_components": [
                    "reveal_cadence",
                    "caption_cadence",
                    "visual_contrast",
                    "sonic_timing",
                ],
                "hook_trigger": "Open on an unresolved moment.",
                "reveal_cadence": "Reveal after the first beat.",
                "caption_cadence": "One caption per beat.",
                "visual_contrast": "Friction then calm.",
                "sonic_timing": "Sound marks the reveal.",
                "anchors": [
                    {
                        "component": "hook_trigger",
                        "start_seconds": 0,
                        "end_seconds": 2.5,
                        "carrier": "opening-shot",
                        "observable_function": "withhold outcome",
                        "surface_class": "visual",
                        "source_ref": "source-001",
                        "availability": "observed",
                        "shot_or_phase_anchor": "shot-01",
                    }
                ],
                "pattern_identity": {
                    "pattern_key": "delayed-reveal",
                    "pattern_version": 1,
                },
                "target_surface_substitutions": ["Target-owned surfaces only."],
                "sound_policy": "functional_substitution",
            },
            "conversion-action": {
                "mechanism": "conversion-action",
                "component": "cta_invitation",
                "frozen_components": [
                    "objection_resolution",
                    "promotion_contract",
                    "action_path",
                ],
                "objection_resolution": "Answer one confirmed concern.",
                "promotion_contract": {
                    "state": "not_applicable",
                    "promotion_fact_id": None,
                    "promotion_fact_digest": None,
                    "value_digest": None,
                    "database_time_valid_at": None,
                    "product_snapshot_id": None,
                    "product_snapshot_digest": None,
                },
                "cta_invitation": "Invite a fact-bound next step.",
                "action_path": "Reviewed destination only.",
                "cta_policy": {
                    "pattern_policy": "One bounded invitation.",
                    "final_cta_role": "informational next step",
                    "visible_copy_owner": "server",
                    "provider_may_write_visible_cta": False,
                },
                "action_path_binding": {
                    "state": "not_applicable",
                    "destination_ref": None,
                    "external_execution": False,
                },
                "provider_exclusion": {
                    "excluded_surfaces": ["visible_cta", "promotion_copy"],
                    "provider_may_write_visible_copy": False,
                    "evidence_refs": ["provider-contract-001"],
                },
            },
            "trend-native": {
                "mechanism": "trend-native",
                "component": "template_grammar",
                "frozen_components": [
                    "trend_signal_binding",
                    "trend_semantic_frame",
                    "audio_function",
                ],
                "trend_signal_binding": "Bind the dated signal.",
                "trend_semantic_frame": "Use the meaning, not creator identity.",
                "template_grammar": "Preserve only the abstract beat structure.",
                "audio_function": "Describe timing without claiming audio rights.",
                "admission": {
                    "evidence_scope": ["One dated platform observation."],
                    "freshness_window_days": 7,
                    "source_refs": ["source-001"],
                    "limitations": ["No ranking or live trend claim."],
                    "analysis_evidence_state": "confirmed",
                    "adaptation_evidence_state": "confirmed",
                    "source_audio_evidence_state": "not_applicable",
                    "template_evidence_state": "confirmed",
                    "platform_constraints": ["TikTok observation only."],
                    "market_constraints": ["US observation only."],
                    "locale_constraints": ["en-US observation only."],
                    "assessment_state": "admitted_with_limits",
                    "execution_capability": "not_implemented",
                    "external_action_requested": False,
                    "target_text_substitutions": ["Use target-owned text."],
                    "target_visual_substitutions": ["Use target-owned visuals."],
                    "target_audio_substitutions": ["Use licensed target audio."],
                    "source_identity_exclusions": ["creator identity"],
                    "originality_handoff": ["Review originality_delta separately."],
                },
            },
        }

        for mechanism, mechanism_payload in payloads.items():
            with self.subTest(mechanism=mechanism):
                payload = adaptation_payload(contract)
                payload["artifact_id"] = f"adaptation-{mechanism}"
                payload["primary_mechanism"] = mechanism
                payload["selected_component"] = mechanism_payload["component"]
                payload["mechanism_payload"] = mechanism_payload
                artifact = bind_artifact_digest(payload)
                self.assertEqual(artifact["mechanism_payload"]["mechanism"], mechanism)

        unsafe_conversion = adaptation_payload(contract)
        unsafe_conversion["primary_mechanism"] = "conversion-action"
        unsafe_conversion["selected_component"] = "cta_invitation"
        unsafe_conversion["mechanism_payload"] = payloads["conversion-action"]
        unsafe_conversion["mechanism_payload"]["cta_policy"][
            "provider_may_write_visible_cta"
        ] = True
        with self.assertRaises(ArtifactValidationError) as conversion_error:
            bind_artifact_digest(unsafe_conversion)
        self.assertEqual(
            conversion_error.exception.code, "MECHANISM_SAFETY_FIELDS_INVALID"
        )

        unsafe_trend = adaptation_payload(contract)
        unsafe_trend["primary_mechanism"] = "trend-native"
        unsafe_trend["selected_component"] = "template_grammar"
        unsafe_trend["mechanism_payload"] = payloads["trend-native"]
        unsafe_trend["mechanism_payload"]["admission"]["external_action_requested"] = (
            True
        )
        with self.assertRaises(ArtifactValidationError) as trend_error:
            bind_artifact_digest(unsafe_trend)
        self.assertEqual(trend_error.exception.code, "MECHANISM_SAFETY_FIELDS_INVALID")

    def test_conversion_promotion_binding_requires_same_snapshot_and_provider_evidence(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        payload = adaptation_payload(contract)
        payload["primary_mechanism"] = "conversion-action"
        payload["selected_component"] = "promotion_contract"
        payload["mechanism_payload"] = {
            "mechanism": "conversion-action",
            "component": "promotion_contract",
            "frozen_components": [
                "objection_resolution",
                "cta_invitation",
                "action_path",
            ],
            "objection_resolution": "Answer one confirmed concern.",
            "promotion_contract": {
                "state": "eligible",
                "promotion_fact_id": "promotion-fact-001",
                "promotion_fact_digest": SHA_B,
                "value_digest": SHA_A,
                "database_time_valid_at": "2026-10-21T00:00:00Z",
                "product_snapshot_id": "snapshot-001",
                "product_snapshot_digest": SHA_A,
            },
            "cta_invitation": "Invite a fact-bound next step.",
            "action_path": "Reviewed destination only.",
            "cta_policy": {
                "pattern_policy": "One bounded invitation.",
                "final_cta_role": "informational next step",
                "visible_copy_owner": "server",
                "provider_may_write_visible_cta": False,
            },
            "action_path_binding": {
                "state": "not_applicable",
                "destination_ref": None,
                "external_execution": False,
            },
            "provider_exclusion": {
                "excluded_surfaces": ["visible_cta", "promotion_copy"],
                "provider_may_write_visible_copy": False,
                "evidence_refs": ["provider-contract-001"],
            },
        }

        bind_artifact_digest(payload)

        payload["mechanism_payload"]["promotion_contract"]["product_snapshot_id"] = (
            "snapshot-002"
        )
        with self.assertRaises(ArtifactValidationError) as snapshot_error:
            bind_artifact_digest(payload)
        self.assertEqual(
            snapshot_error.exception.code, "MECHANISM_SAFETY_FIELDS_INVALID"
        )

        payload["mechanism_payload"]["promotion_contract"]["product_snapshot_id"] = (
            "snapshot-001"
        )
        payload["mechanism_payload"]["provider_exclusion"]["evidence_refs"] = []
        with self.assertRaises(ArtifactValidationError) as evidence_error:
            bind_artifact_digest(payload)
        self.assertEqual(
            evidence_error.exception.code, "MECHANISM_SAFETY_FIELDS_INVALID"
        )

    def test_mechanism_and_component_must_match_across_plan_and_adaptation(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        bad_plan = plan_payload(hypothesis, reference)
        bad_plan["selected_component"] = "cta_invitation"

        with self.assertRaises(ArtifactValidationError) as plan_error:
            bind_artifact_digest(bad_plan)
        self.assertEqual(plan_error.exception.code, "MECHANISM_COMPONENT_INVALID")

        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        bad_adaptation = adaptation_payload(contract)
        bad_adaptation["primary_mechanism"] = "proof-demonstration"

        with self.assertRaises(ArtifactValidationError) as adaptation_error:
            bind_artifact_digest(bad_adaptation)
        self.assertEqual(
            adaptation_error.exception.code, "ADAPTATION_MECHANISM_MISMATCH"
        )

    def test_fact_map_rejects_unconfirmed_bound_facts_and_overlapping_sets(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        bad_status = fact_map_payload(plan)
        bad_status["claim_mappings"][0]["fact_status"] = "unconfirmed"

        with self.assertRaises(ArtifactValidationError) as status_error:
            bind_artifact_digest(bad_status)
        self.assertEqual(status_error.exception.code, "FACT_BINDING_INVALID")

        overlap = fact_map_payload(plan)
        overlap["excluded_fact_ids"].append("fact-001")
        with self.assertRaises(ArtifactValidationError) as overlap_error:
            bind_artifact_digest(overlap)
        self.assertEqual(overlap_error.exception.code, "FACT_SETS_OVERLAP")

    def test_brand_voice_fact_map_has_a_closed_no_product_claim_path(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        payload = no_product_fact_map_payload(plan)

        artifact = bind_artifact_digest(payload)
        self.assertEqual(artifact["claim_scope"], "no_product_claims")

        payload["selected_fact_ids"] = ["fact-001"]
        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)
        self.assertEqual(caught.exception.code, "CLAIM_SCOPE_INVALID")

    def test_replication_contract_requires_typed_frozen_configuration(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        payload = contract_payload(plan, fact_map, decomposition)
        payload["frozen_configuration"] = {}

        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)

        self.assertEqual(caught.exception.code, "CONTRACT_CONFIGURATION_INVALID")

    def test_no_product_claim_contract_preserves_not_applicable_binding(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(no_product_fact_map_payload(plan))

        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))

        self.assertEqual(contract["claim_scope"], "no_product_claims")
        self.assertEqual(contract["subject_binding"]["state"], "not_applicable")
        self.assertEqual(contract["selected_fact_ids"], [])
        self.assertEqual(contract["excluded_fact_ids"], [])

    def test_chain_resolves_real_artifacts_and_external_media_refs(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))
        integrity = bind_artifact_digest(
            reviewed_media_integrity_payload(contract, adaptation)
        )
        finding = bind_artifact_digest(finding_payload(contract, adaptation, integrity))

        validated = validate_artifact_chain(
            (
                reference,
                decomposition,
                hypothesis,
                plan,
                fact_map,
                contract,
                adaptation,
                integrity,
                finding,
            ),
            external_refs=(
                integrity["script_version_ref"],
                integrity["storyboard_version_ref"],
                integrity["controlled_artifact_ref"],
            ),
        )

        self.assertEqual(len(validated), 9)

    def test_chain_rejects_preflight_as_a_completed_finding_input(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))
        preflight = bind_artifact_digest(media_integrity_payload(contract, adaptation))
        finding = bind_artifact_digest(finding_payload(contract, adaptation, preflight))

        with self.assertRaises(ArtifactValidationError) as caught:
            validate_artifact_chain(
                (
                    reference,
                    decomposition,
                    hypothesis,
                    plan,
                    fact_map,
                    contract,
                    adaptation,
                    preflight,
                    finding,
                ),
                external_refs=(preflight["script_version_ref"],),
            )
        self.assertEqual(caught.exception.code, "CHAIN_INCOMPLETE_PREFLIGHT")

    def test_chain_rejects_digest_and_mechanism_drift(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        bad_decomposition_payload = decomposition_payload(reference)
        bad_decomposition_payload["input_refs"][0]["content_digest"] = SHA_B
        bad_decomposition_payload["reference_bundle_ref"]["content_digest"] = SHA_B
        bad_decomposition = bind_artifact_digest(bad_decomposition_payload)

        with self.assertRaises(ArtifactValidationError) as digest_error:
            validate_artifact_chain((reference, bad_decomposition))
        self.assertEqual(digest_error.exception.code, "CHAIN_REF_DIGEST_MISMATCH")

        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        bad_contract_payload = contract_payload(plan, fact_map, decomposition)
        bad_contract_payload.update(
            {
                "primary_mechanism": "proof-demonstration",
                "selected_component": "proof_device",
                "frozen_components": [],
            }
        )
        bad_contract = bind_artifact_digest(bad_contract_payload)

        with self.assertRaises(ArtifactValidationError) as mechanism_error:
            validate_artifact_chain(
                (reference, decomposition, hypothesis, plan, fact_map, bad_contract)
            )
        self.assertEqual(mechanism_error.exception.code, "CHAIN_MECHANISM_MISMATCH")

    def test_chain_rejects_early_artifact_lineage_drift(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())

        wrong_mechanism_payload = decomposition_payload(reference)
        wrong_mechanism_payload["primary_mechanism"] = "narrative-transformation"
        wrong_mechanism_payload["mechanism_observations"] = (
            narrative_decomposition_observations()
        )
        wrong_mechanism = bind_artifact_digest(wrong_mechanism_payload)
        hypothesis = bind_artifact_digest(hypothesis_payload(wrong_mechanism))
        with self.assertRaises(ArtifactValidationError) as mechanism_error:
            validate_artifact_chain((reference, wrong_mechanism, hypothesis))
        self.assertEqual(mechanism_error.exception.code, "CHAIN_MECHANISM_MISMATCH")

        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        other_reference_payload = reference_bundle_payload()
        other_reference_payload["artifact_id"] = "reference-bundle-002"
        other_reference_payload["reference_id"] = "reference-002"
        other_reference_payload["source_locator"] = "https://example.test/video/002"
        other_reference = bind_artifact_digest(other_reference_payload)
        mismatched_plan = bind_artifact_digest(
            plan_payload(hypothesis, other_reference)
        )
        with self.assertRaises(ArtifactValidationError) as control_error:
            validate_artifact_chain(
                (
                    reference,
                    other_reference,
                    decomposition,
                    hypothesis,
                    mismatched_plan,
                )
            )
        self.assertEqual(control_error.exception.code, "CHAIN_LINEAGE_MISMATCH")

        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        other_plan_payload = plan_payload(hypothesis, reference)
        other_plan_payload["artifact_id"] = "replication-plan-002"
        other_plan_payload["variant_id"] = "variant-002"
        other_plan = bind_artifact_digest(other_plan_payload)
        fact_map = bind_artifact_digest(fact_map_payload(other_plan))
        mismatched_contract = bind_artifact_digest(
            contract_payload(plan, fact_map, decomposition)
        )
        with self.assertRaises(ArtifactValidationError) as fact_map_error:
            validate_artifact_chain(
                (
                    reference,
                    decomposition,
                    hypothesis,
                    plan,
                    other_plan,
                    fact_map,
                    mismatched_contract,
                )
            )
        self.assertEqual(fact_map_error.exception.code, "CHAIN_LINEAGE_MISMATCH")

        other_decomposition_payload = decomposition_payload(reference)
        other_decomposition_payload["artifact_id"] = "decomposition-map-002"
        other_decomposition = bind_artifact_digest(other_decomposition_payload)
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        mismatched_contract = bind_artifact_digest(
            contract_payload(plan, fact_map, other_decomposition)
        )
        with self.assertRaises(ArtifactValidationError) as decomposition_error:
            validate_artifact_chain(
                (
                    reference,
                    decomposition,
                    other_decomposition,
                    hypothesis,
                    plan,
                    fact_map,
                    mismatched_contract,
                )
            )
        self.assertEqual(decomposition_error.exception.code, "CHAIN_LINEAGE_MISMATCH")

    def test_chain_rejects_downstream_subject_binding_drift(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        bad_adaptation_payload = adaptation_payload(contract)
        bad_adaptation_payload["subject_binding"] = {
            "state": "unresolved",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "market": "US",
            "locale": "en-US",
            "limitations": ["Drifted after the contract was frozen."],
        }
        bad_adaptation = bind_artifact_digest(bad_adaptation_payload)

        with self.assertRaises(ArtifactValidationError) as caught:
            validate_artifact_chain(
                (
                    reference,
                    decomposition,
                    hypothesis,
                    plan,
                    fact_map,
                    contract,
                    bad_adaptation,
                )
            )
        self.assertEqual(caught.exception.code, "CHAIN_SUBJECT_BINDING_MISMATCH")

    def test_missing_states_and_observed_zero_do_not_collapse(self) -> None:
        missing_states = (
            "unknown",
            "not_reported",
            "not_collected",
            "unavailable",
            "quarantined",
        )
        for state in missing_states:
            with self.subTest(state=state):
                payload = reference_bundle_payload()
                observation = payload["observations"][0]
                observation["state"] = state
                observation["value"] = None
                observation["source_refs"] = ["source-001"]
                artifact = bind_artifact_digest(payload)
                self.assertEqual(artifact["observations"][0]["state"], state)
                self.assertIsNone(artifact["observations"][0]["value"])

        invalid = reference_bundle_payload()
        invalid["observations"][0].update({"state": "unavailable", "value": 0})
        with self.assertRaises(ArtifactValidationError) as missing_error:
            bind_artifact_digest(invalid)
        self.assertEqual(missing_error.exception.code, "MISSING_SEMANTICS_INVALID")

        collapsed_zero = reference_bundle_payload()
        collapsed_zero["observations"][0].update({"state": "observed", "value": 0})
        observed_zero = bind_artifact_digest(collapsed_zero)
        self.assertEqual(observed_zero["observations"][0]["state"], "observed")
        self.assertEqual(observed_zero["observations"][0]["value"], 0)

    def test_existing_measurement_fixture_preserves_zero_and_ambiguous_values(
        self,
    ) -> None:
        fixture = json.loads(
            (
                PROJECT_ROOT
                / ".agents/workflows/viral-replication/fixtures/VR-P3-002-measurement-semantics.json"
            ).read_text(encoding="utf-8")
        )
        payload = reference_bundle_payload()
        payload["evidence_level"] = "inference"
        payload["observations"] = [
            {
                "observation_ref": record["measurement_id"],
                "metric": record["metric"],
                "state": record["state"],
                "value": record["value"],
                "unit": record["unit"],
                "source_refs": (
                    [record["source_ref"]] if record["source_ref"] is not None else []
                ),
            }
            for record in fixture["measurement_records"]
        ]

        artifact = bind_artifact_digest(payload)

        by_ref = {
            observation["observation_ref"]: observation
            for observation in artifact["observations"]
        }
        self.assertEqual(by_ref["m-observed-zero"]["state"], "observed")
        self.assertEqual(by_ref["m-observed-zero"]["value"], 0)
        self.assertEqual(by_ref["m-source-ambiguous"]["value"], 10)

        payload["evidence_level"] = "fact"
        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)
        self.assertEqual(caught.exception.code, "MISSING_SEMANTICS_INVALID")

    def test_chain_keeps_source_ambiguous_measurements_out_of_fact_bindings(
        self,
    ) -> None:
        reference_payload = reference_bundle_payload()
        reference_payload["evidence_level"] = "inference"
        reference_payload["observations"][0].update(
            {"state": "source_ambiguous", "value": 10}
        )
        reference = bind_artifact_digest(reference_payload)
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_payload = fact_map_payload(plan)
        fact_payload["claim_mappings"][0]["evidence_refs"] = ["views-001"]
        fact_map = bind_artifact_digest(fact_payload)

        with self.assertRaises(ArtifactValidationError) as caught:
            validate_artifact_chain(
                (reference, decomposition, hypothesis, plan, fact_map)
            )
        self.assertEqual(caught.exception.code, "SOURCE_AMBIGUOUS_NOT_FACT")

    def test_digest_canonicalizes_numeric_zero_and_rejects_non_finite_numbers(
        self,
    ) -> None:
        digests: set[str] = set()
        for value in (0, 0.0, -0.0):
            payload = reference_bundle_payload()
            payload["observations"][0]["value"] = value
            digests.add(str(bind_artifact_digest(payload)["content_digest"]))
        self.assertEqual(len(digests), 1)

        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                payload = reference_bundle_payload()
                payload["observations"][0]["value"] = value
                with self.assertRaises(ArtifactValidationError) as caught:
                    bind_artifact_digest(payload)
                self.assertEqual(caught.exception.code, "ARTIFACT_NUMBER_NON_FINITE")

    def test_reference_locator_rejects_absolute_and_file_paths(self) -> None:
        for locator in (
            "/Users/example/private/reference.mov",
            "file:///Users/example/private/reference.mov",
        ):
            with self.subTest(locator=locator):
                payload = reference_bundle_payload()
                payload["source_locator"] = locator
                with self.assertRaises(ArtifactValidationError) as caught:
                    bind_artifact_digest(payload)
                self.assertEqual(caught.exception.code, "SOURCE_LOCATOR_INVALID")

        opaque = reference_bundle_payload()
        opaque["source_locator"] = "media:reference-001"
        self.assertEqual(
            bind_artifact_digest(opaque)["source_locator"], "media:reference-001"
        )

    def test_digest_status_and_preflight_scope_return_stable_failure_codes(
        self,
    ) -> None:
        artifact = bind_artifact_digest(reference_bundle_payload())
        artifact["limitations"].append("Tampered after digest binding.")
        with self.assertRaises(ArtifactValidationError) as digest_error:
            validate_artifact(artifact)
        self.assertEqual(digest_error.exception.code, "ARTIFACT_DIGEST_MISMATCH")

        bad_status = reference_bundle_payload()
        bad_status["status"] = "done"
        with self.assertRaises(ArtifactValidationError) as status_error:
            bind_artifact_digest(bad_status)
        self.assertEqual(status_error.exception.code, "ARTIFACT_STATUS_INVALID")

        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))
        preflight = media_integrity_payload(contract, adaptation)
        preflight["gate_checks"][0]["state"] = "passed"
        preflight["gate_checks"][0]["evidence_refs"] = ["evidence-001"]
        preflight["gate_checks"][0]["unknowns"] = []
        with self.assertRaises(ArtifactValidationError) as integrity_error:
            bind_artifact_digest(preflight)
        self.assertEqual(
            integrity_error.exception.code, "MEDIA_INTEGRITY_SCOPE_INVALID"
        )

    def test_blocked_media_integrity_gates_cannot_report_ready(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))
        payload = reviewed_media_integrity_payload(contract, adaptation)
        payload["blockers"] = []
        payload["unknowns"] = []
        for gate in payload["gate_checks"]:
            gate["state"] = "blocked"
            gate["blockers"] = [f"{gate['gate']}_blocked"]
            gate["unknowns"] = []
            gate["fallback_strategy"] = ["Stop and request human review."]
            payload["blockers"].append(f"{gate['gate']}_blocked")

        with self.assertRaises(ArtifactValidationError) as caught:
            bind_artifact_digest(payload)

        self.assertEqual(caught.exception.code, "MEDIA_INTEGRITY_DISPOSITION_INVALID")

    def test_media_integrity_supports_bounded_preflight_and_controlled_review(
        self,
    ) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))

        preflight = media_integrity_payload(contract, adaptation)
        for gate in preflight["gate_checks"]:
            if gate["gate"] == "source_use_scope":
                gate.update(
                    {
                        "state": "passed",
                        "findings": ["Source use is within the reviewed scope."],
                        "evidence_refs": ["source-use-review-001"],
                        "unknowns": [],
                        "fallback_strategy": [],
                    }
                )
        preflight_artifact = bind_artifact_digest(preflight)
        self.assertEqual(
            next(
                gate["state"]
                for gate in preflight_artifact["gate_checks"]
                if gate["gate"] == "source_use_scope"
            ),
            "passed",
        )

        missing_script_and_storyboard = media_integrity_payload(contract, adaptation)
        missing_script_and_storyboard["script_version_ref"] = None
        missing_script_and_storyboard["input_refs"] = [
            artifact_ref(contract),
            artifact_ref(adaptation),
        ]
        with self.assertRaises(ArtifactValidationError) as ref_error:
            bind_artifact_digest(missing_script_and_storyboard)
        self.assertEqual(
            ref_error.exception.code, "MEDIA_INTEGRITY_ARTIFACT_REFS_INVALID"
        )

        storyboard_only = media_integrity_payload(contract, adaptation)
        storyboard_ref = external_ref(
            artifact_type="storyboard_version", artifact_id="storyboard-version-001"
        )
        storyboard_only["script_version_ref"] = None
        storyboard_only["storyboard_version_ref"] = storyboard_ref
        storyboard_only["storyboard_lineage"] = None
        storyboard_only["input_refs"][-1] = storyboard_ref
        self.assertEqual(
            bind_artifact_digest(storyboard_only)["storyboard_version_ref"][
                "artifact_id"
            ],
            "storyboard-version-001",
        )

        review = reviewed_media_integrity_payload(contract, adaptation)
        reviewed_artifact = bind_artifact_digest(review)
        self.assertEqual(reviewed_artifact["disposition"], "ready_for_next_gate")

    def test_storyboard_lineage_binds_storyboard_to_its_source_script(self) -> None:
        reference = bind_artifact_digest(reference_bundle_payload())
        decomposition = bind_artifact_digest(decomposition_payload(reference))
        hypothesis = bind_artifact_digest(hypothesis_payload(decomposition))
        plan = bind_artifact_digest(plan_payload(hypothesis, reference))
        fact_map = bind_artifact_digest(fact_map_payload(plan))
        contract = bind_artifact_digest(contract_payload(plan, fact_map, decomposition))
        adaptation = bind_artifact_digest(adaptation_payload(contract))
        review = reviewed_media_integrity_payload(contract, adaptation)
        review["storyboard_lineage"] = {
            "storyboard_version_ref": dict(review["storyboard_version_ref"]),
            "source_script_version_ref": dict(review["script_version_ref"]),
            "evidence_scope": "declared_artifact_lineage",
        }

        artifact = bind_artifact_digest(review)
        self.assertEqual(
            artifact["storyboard_lineage"]["source_script_version_ref"]["artifact_id"],
            "script-version-001",
        )

        missing_lineage = reviewed_media_integrity_payload(contract, adaptation)
        missing_lineage["storyboard_lineage"] = None
        with self.assertRaises(ArtifactValidationError) as missing_error:
            bind_artifact_digest(missing_lineage)
        self.assertEqual(missing_error.exception.code, "STORYBOARD_LINEAGE_MISMATCH")

        incomplete_review = media_integrity_payload(contract, adaptation)
        incomplete_review["mode"] = "artifact_review"
        controlled_ref = external_ref(
            artifact_type="controlled_media", artifact_id="controlled-media-002"
        )
        incomplete_review["controlled_artifact_ref"] = controlled_ref
        incomplete_review["input_refs"].append(controlled_ref)
        with self.assertRaises(ArtifactValidationError) as incomplete_error:
            bind_artifact_digest(incomplete_review)
        self.assertEqual(
            incomplete_error.exception.code, "MEDIA_INTEGRITY_ARTIFACT_REFS_INVALID"
        )

        review["storyboard_lineage"]["source_script_version_ref"]["content_digest"] = (
            SHA_A
        )
        with self.assertRaises(ArtifactValidationError) as mismatch_error:
            bind_artifact_digest(review)
        self.assertEqual(mismatch_error.exception.code, "STORYBOARD_LINEAGE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
