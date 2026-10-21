from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Annotated, Any, Literal, NoReturn
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

ArtifactStatus = Literal[
    "draft",
    "validated",
    "awaiting_approval",
    "blocked",
    "approved",
    "stale",
    "superseded",
    "final_with_limits",
]
EvidenceLevel = Literal["fact", "inference", "unknown"]
ProofLevel = Literal["local", "ci", "private", "deployment", "live", "production"]
ObservationState = Literal[
    "observed",
    "unknown",
    "not_reported",
    "not_collected",
    "source_ambiguous",
    "unavailable",
    "quarantined",
]
PrimaryMechanism = Literal[
    "narrative-transformation",
    "proof-demonstration",
    "experience-pov",
    "attention-grammar",
    "conversion-action",
    "trend-native",
]
MechanismComponent = Literal[
    "narrative_arc",
    "proof_device",
    "experience_pov",
    "hook_trigger",
    "reveal_cadence",
    "caption_cadence",
    "visual_contrast",
    "sonic_timing",
    "objection_resolution",
    "promotion_contract",
    "cta_invitation",
    "action_path",
    "trend_signal_binding",
    "trend_semantic_frame",
    "template_grammar",
    "audio_function",
]
AttentionComponent = Literal[
    "hook_trigger",
    "reveal_cadence",
    "caption_cadence",
    "visual_contrast",
    "sonic_timing",
]
ConversionComponent = Literal[
    "objection_resolution",
    "promotion_contract",
    "cta_invitation",
    "action_path",
]
TrendComponent = Literal[
    "trend_signal_binding",
    "trend_semantic_frame",
    "template_grammar",
    "audio_function",
]
DecompositionAvailability = Literal[
    "observed",
    "not_present",
    "unknown",
    "unavailable",
    "source_ambiguous",
]
SurfaceModality = Literal["text", "visual", "audio", "motion", "mixed"]
SurfaceDisposition = Literal["replaceable", "frozen", "prohibited", "unknown"]

_MECHANISM_COMPONENTS: dict[str, frozenset[str]] = {
    "narrative-transformation": frozenset({"narrative_arc"}),
    "proof-demonstration": frozenset({"proof_device"}),
    "experience-pov": frozenset({"experience_pov"}),
    "attention-grammar": frozenset(
        {
            "hook_trigger",
            "reveal_cadence",
            "caption_cadence",
            "visual_contrast",
            "sonic_timing",
        }
    ),
    "conversion-action": frozenset(
        {
            "objection_resolution",
            "promotion_contract",
            "cta_invitation",
            "action_path",
        }
    ),
    "trend-native": frozenset(
        {
            "trend_signal_binding",
            "trend_semantic_frame",
            "template_grammar",
            "audio_function",
        }
    ),
}

_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"


class ArtifactValidationError(ValueError):
    """Stable public validation failure independent of Pydantic internals."""

    def __init__(self, code: str, *, path: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.path = path
        self.detail = detail


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactRef(_FrozenModel):
    artifact_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    artifact_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    task_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    run_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    version: int = Field(ge=1)
    content_digest: str = Field(pattern=_DIGEST_PATTERN)


class SourceRef(_FrozenModel):
    source_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    source_kind: Literal[
        "public_url",
        "local_media",
        "reviewed_package",
        "product_truth",
        "experiment",
        "asset_bundle",
        "human_observation",
        "other",
    ]
    source_digest: str | None = Field(pattern=_DIGEST_PATTERN)


class SubjectBinding(_FrozenModel):
    state: Literal[
        "exact_snapshot",
        "reviewed_snapshot_selection",
        "reviewed_family_context",
        "unresolved",
        "conflict",
        "not_applicable",
    ]
    product_snapshot_id: str | None
    product_snapshot_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    market: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    locale: str | None = Field(default=None, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    limitations: tuple[str, ...]

    @model_validator(mode="after")
    def validate_snapshot_binding(self) -> SubjectBinding:
        has_identity = self.product_snapshot_id is not None
        has_digest = self.product_snapshot_digest is not None
        if has_identity != has_digest:
            raise ValueError("subject_binding_incomplete")
        if self.state in {"exact_snapshot", "reviewed_snapshot_selection"} and not has_identity:
            raise ValueError("subject_binding_incomplete")
        if self.state in {"unresolved", "conflict", "not_applicable"} and has_identity:
            raise ValueError("subject_binding_state_conflict")
        return self


class ObservationValue(_FrozenModel):
    observation_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    metric: str = Field(min_length=1, max_length=128)
    state: ObservationState
    value: str | int | float | bool | None
    unit: str | None = Field(default=None, max_length=64)
    source_refs: tuple[str, ...]

    @model_validator(mode="after")
    def preserve_missing_semantics(self) -> ObservationValue:
        missing_states = {
            "unknown",
            "not_reported",
            "not_collected",
            "unavailable",
            "quarantined",
        }
        if self.state in missing_states and self.value is not None:
            raise ValueError("missing_semantics_invalid")
        if self.state == "observed" and self.value is None:
            raise ValueError("missing_semantics_invalid")
        if self.state == "source_ambiguous" and not self.source_refs:
            raise ValueError("missing_semantics_invalid")
        return self


class PerformanceWindow(_FrozenModel):
    start: date
    end: date
    timezone: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_window(self) -> PerformanceWindow:
        if self.end < self.start:
            raise ValueError("performance_window_invalid")
        return self


class ArtifactEnvelope(_FrozenModel):
    schema_version: str = Field(pattern=r"^sv\.[a-z0-9-]+\.v[1-9][0-9]*$")
    artifact_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    artifact_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    task_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    run_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    version: int = Field(ge=1)
    status: ArtifactStatus
    input_refs: tuple[ArtifactRef, ...]
    source_refs: tuple[SourceRef, ...]
    subject_binding: SubjectBinding
    content_digest: str = Field(pattern=_DIGEST_PATTERN)
    evidence_level: EvidenceLevel
    proof_level: ProofLevel
    limitations: tuple[str, ...]
    created_at: datetime
    supersedes_artifact_id: str | None = Field(pattern=_IDENTIFIER_PATTERN)

    @model_validator(mode="after")
    def validate_input_ref_scope(self) -> ArtifactEnvelope:
        if any(
            ref.task_ref != self.task_ref or ref.run_ref != self.run_ref for ref in self.input_refs
        ):
            raise ValueError("artifact_ref_scope_mismatch")
        return self

    @model_validator(mode="after")
    def validate_content_digest(self, info: ValidationInfo) -> ArtifactEnvelope:
        if (info.context or {}).get("skip_digest"):
            return self
        if canonical_artifact_digest(self.model_dump(mode="json")) != self.content_digest:
            raise ValueError("artifact_digest_mismatch")
        return self


def _validate_direct_refs(
    artifact: ArtifactEnvelope,
    refs: tuple[tuple[ArtifactRef, str], ...],
) -> None:
    for ref, expected_type in refs:
        if ref.artifact_type != expected_type:
            raise ValueError("direct_ref_type_invalid")
        if ref.task_ref != artifact.task_ref or ref.run_ref != artifact.run_ref:
            raise ValueError("artifact_ref_scope_mismatch")
        if not any(
            candidate.model_dump(mode="json") == ref.model_dump(mode="json")
            for candidate in artifact.input_refs
        ):
            raise ValueError("direct_ref_input_missing")


class ReferenceBundle(ArtifactEnvelope):
    schema_version: Literal["sv.reference-bundle.v1"]
    artifact_type: Literal["reference_bundle"]
    reference_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    source_locator: str = Field(min_length=1, max_length=2048)
    source_digest: str = Field(pattern=_DIGEST_PATTERN)
    platform: Literal["tiktok", "instagram", "youtube", "other", "unknown"]
    performance_window: PerformanceWindow
    captured_at: datetime
    rights_state: Literal[
        "confirmed_for_analysis",
        "analysis_only",
        "unknown",
        "restricted",
        "blocked",
    ]
    playability_state: Literal["playable", "unavailable", "quarantined", "unknown"]
    candidate_state: Literal["candidate", "not_candidate", "unknown"]
    observations: tuple[ObservationValue, ...]

    @field_validator("source_locator")
    @classmethod
    def validate_source_locator(cls, value: str) -> str:
        if re.fullmatch(r"media:[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", value):
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.hostname.lower() == "localhost"
        ):
            raise ValueError("source_locator_invalid")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            return value
        if not address.is_global:
            raise ValueError("source_locator_invalid")
        return value

    @model_validator(mode="after")
    def validate_observation_evidence(self) -> ReferenceBundle:
        if self.evidence_level == "fact" and any(
            observation.state == "source_ambiguous" for observation in self.observations
        ):
            raise ValueError("missing_semantics_invalid")
        return self


class TimelineObservation(_FrozenModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    dimension: Literal[
        "hook",
        "pain_tension",
        "narrative_beat",
        "proof_device",
        "experience_cue",
        "visual",
        "audio",
        "text",
        "cta",
        "claim_candidate",
        "unknown",
    ]
    observation: str = Field(min_length=1, max_length=2000)
    availability: ObservationState
    source_refs: tuple[str, ...]

    @model_validator(mode="after")
    def validate_time_range(self) -> TimelineObservation:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("timeline_range_invalid")
        return self


class PatternIdentity(_FrozenModel):
    pattern_key: str = Field(pattern=_IDENTIFIER_PATTERN)
    pattern_version: int = Field(ge=1)


class DecompositionAttentionObservation(_FrozenModel):
    component: AttentionComponent
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    carrier: str = Field(min_length=1, max_length=256)
    observable_function: str = Field(min_length=1, max_length=1000)
    surface_modality: SurfaceModality
    surface_disposition: SurfaceDisposition
    source_refs: tuple[str, ...] = Field(min_length=1)
    availability: DecompositionAvailability
    shot_or_phase_anchor: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_time_range(self) -> DecompositionAttentionObservation:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("decomposition_observations_invalid")
        return self


class AttentionDecompositionObservations(_FrozenModel):
    mechanism: Literal["attention-grammar"]
    pattern_identity: PatternIdentity
    observations: tuple[DecompositionAttentionObservation, ...] = Field(min_length=1)


class NarrativeBeatObservation(_FrozenModel):
    role: Literal["hook", "pain_tension", "intervention", "result", "cta", "other"]
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    observable_function: str = Field(min_length=1, max_length=1000)
    surface_expression: str = Field(min_length=1, max_length=2000)
    surface_disposition: SurfaceDisposition
    availability: DecompositionAvailability
    source_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> NarrativeBeatObservation:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("decomposition_observations_invalid")
        return self


class NarrativeDecompositionObservations(_FrozenModel):
    mechanism: Literal["narrative-transformation"]
    beats: tuple[NarrativeBeatObservation, ...] = Field(min_length=1)


class ProofStepObservation(_FrozenModel):
    phase: Literal["setup", "intervention", "comparison", "measurement", "result", "limitation"]
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    proof_device: str = Field(min_length=1, max_length=1000)
    observable_function: str = Field(min_length=1, max_length=1000)
    observed_phenomenon: str = Field(min_length=1, max_length=2000)
    allowed_conclusion: str = Field(min_length=1, max_length=2000)
    availability: DecompositionAvailability
    source_refs: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...]

    @model_validator(mode="after")
    def validate_time_range(self) -> ProofStepObservation:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("decomposition_observations_invalid")
        return self


class ProofDecompositionObservations(_FrozenModel):
    mechanism: Literal["proof-demonstration"]
    steps: tuple[ProofStepObservation, ...] = Field(min_length=1)


class ExperienceCueObservation(_FrozenModel):
    cue_type: Literal["pov", "sensory", "action_continuity", "daily_context", "emotional_tone"]
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    observable_function: str = Field(min_length=1, max_length=1000)
    surface_expression: str = Field(min_length=1, max_length=2000)
    replaceable_fields: tuple[str, ...]
    availability: DecompositionAvailability
    source_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> ExperienceCueObservation:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("decomposition_observations_invalid")
        return self


class ExperienceDecompositionObservations(_FrozenModel):
    mechanism: Literal["experience-pov"]
    cues: tuple[ExperienceCueObservation, ...] = Field(min_length=1)


class DecompositionComponentObservation(_FrozenModel):
    start_seconds: float | None = Field(ge=0)
    end_seconds: float | None = Field(gt=0)
    observable_function: str = Field(min_length=1, max_length=1000)
    surface_modality: SurfaceModality
    surface_disposition: SurfaceDisposition
    availability: DecompositionAvailability
    source_refs: tuple[str, ...] = Field(min_length=1)
    unknowns: tuple[str, ...]

    @model_validator(mode="after")
    def validate_optional_time_range(self) -> DecompositionComponentObservation:
        start_seconds = self.start_seconds
        end_seconds = self.end_seconds
        has_start = start_seconds is not None
        has_end = end_seconds is not None
        if has_start != has_end:
            raise ValueError("decomposition_observations_invalid")
        if self.availability != "not_present" and not has_start:
            raise ValueError("decomposition_observations_invalid")
        if start_seconds is not None and end_seconds is not None and end_seconds <= start_seconds:
            raise ValueError("decomposition_observations_invalid")
        return self


class ConversionDecompositionObservation(DecompositionComponentObservation):
    component: ConversionComponent


class ConversionDecompositionObservations(_FrozenModel):
    mechanism: Literal["conversion-action"]
    observations: tuple[ConversionDecompositionObservation, ...]
    reference_surface_is_target_copy: Literal[False]

    @model_validator(mode="after")
    def validate_component_partition(self) -> ConversionDecompositionObservations:
        components = [observation.component for observation in self.observations]
        expected = {
            "objection_resolution",
            "promotion_contract",
            "cta_invitation",
            "action_path",
        }
        if len(components) != len(expected) or set(components) != expected:
            raise ValueError("decomposition_observations_invalid")
        return self


class TrendDecompositionObservation(DecompositionComponentObservation):
    component: TrendComponent


class TrendSourceReuseBoundary(_FrozenModel):
    source_identity: Literal["excluded_from_target", "not_present", "unknown"]
    source_audio: Literal[
        "analysis_only",
        "not_present",
        "requires_separate_evidence",
        "unknown",
    ]
    source_template: Literal[
        "analysis_only",
        "not_present",
        "requires_separate_evidence",
        "unknown",
    ]
    target_execution_inclusion: Literal[False]


class TrendDecompositionObservations(_FrozenModel):
    mechanism: Literal["trend-native"]
    observations: tuple[TrendDecompositionObservation, ...]
    source_reuse_boundary: TrendSourceReuseBoundary

    @model_validator(mode="after")
    def validate_component_partition(self) -> TrendDecompositionObservations:
        components = [observation.component for observation in self.observations]
        expected = {
            "trend_signal_binding",
            "trend_semantic_frame",
            "template_grammar",
            "audio_function",
        }
        if len(components) != len(expected) or set(components) != expected:
            raise ValueError("decomposition_observations_invalid")
        return self


DecompositionMechanismObservations = Annotated[
    NarrativeDecompositionObservations
    | ProofDecompositionObservations
    | ExperienceDecompositionObservations
    | AttentionDecompositionObservations
    | ConversionDecompositionObservations
    | TrendDecompositionObservations,
    Field(discriminator="mechanism"),
]


class DecompositionMap(ArtifactEnvelope):
    schema_version: Literal["sv.decomposition-map.v1"]
    artifact_type: Literal["decomposition_map"]
    reference_bundle_ref: ArtifactRef
    timeline: tuple[TimelineObservation, ...] = Field(min_length=1)
    primary_mechanism: PrimaryMechanism | None
    secondary_mechanisms: tuple[PrimaryMechanism, ...]
    mechanism_observations: DecompositionMechanismObservations | None
    unsupported_claims: tuple[str, ...]
    unknowns: tuple[str, ...]

    @model_validator(mode="after")
    def validate_direct_refs(self) -> DecompositionMap:
        _validate_direct_refs(self, ((self.reference_bundle_ref, "reference_bundle"),))
        if self.primary_mechanism is None:
            if self.mechanism_observations is not None:
                raise ValueError("decomposition_mechanism_mismatch")
        elif (
            self.mechanism_observations is None
            or self.mechanism_observations.mechanism != self.primary_mechanism
        ):
            raise ValueError("decomposition_mechanism_mismatch")
        return self


class PatternHypothesis(ArtifactEnvelope):
    schema_version: Literal["sv.pattern-hypothesis.v1"]
    artifact_type: Literal["pattern_hypothesis"]
    decomposition_map_ref: ArtifactRef
    primary_mechanism: PrimaryMechanism
    hypothesis: str = Field(min_length=1, max_length=4000)
    invariant_elements: tuple[str, ...] = Field(min_length=1)
    replaceable_elements: tuple[str, ...]
    prohibited_elements: tuple[str, ...]
    adaptation_constraints: tuple[str, ...]
    evidence_scope: tuple[str, ...] = Field(min_length=1)
    unknowns: tuple[str, ...]

    @model_validator(mode="after")
    def validate_direct_refs(self) -> PatternHypothesis:
        _validate_direct_refs(self, ((self.decomposition_map_ref, "decomposition_map"),))
        return self


class ExecutionBudget(_FrozenModel):
    max_variants: int = Field(ge=1)
    max_iterations: int = Field(ge=1)
    max_duration_seconds: int = Field(ge=1)
    stop_on_violation: Literal[True]


class FrozenConfiguration(_FrozenModel):
    language: str = Field(pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    market: str = Field(pattern=r"^[A-Z]{2}$")
    platform: Literal["tiktok", "instagram", "youtube", "other"]
    duration_seconds: int = Field(ge=1)
    model: str = Field(min_length=1, max_length=256)
    material_scope: tuple[str, ...] = Field(min_length=1)
    execution_budget: ExecutionBudget


def _validate_mechanism_partition(
    primary_mechanism: str,
    selected_component: str,
    frozen_components: tuple[str, ...],
) -> None:
    allowed = _MECHANISM_COMPONENTS[primary_mechanism]
    if selected_component not in allowed:
        raise ValueError("mechanism_component_invalid")
    expected_frozen = allowed - {selected_component}
    if set(frozen_components) != expected_frozen or len(frozen_components) != len(
        set(frozen_components)
    ):
        raise ValueError("frozen_components_invalid")


class ReplicationPlan(ArtifactEnvelope):
    schema_version: Literal["sv.replication-plan.v1"]
    artifact_type: Literal["replication_plan"]
    pattern_hypothesis_ref: ArtifactRef
    control_reference_ref: ArtifactRef
    primary_mechanism: PrimaryMechanism
    selected_component: MechanismComponent
    control_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    variant_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    changed_dimension: str = Field(min_length=1, max_length=512)
    frozen_components: tuple[MechanismComponent, ...]
    target_platform: Literal["tiktok", "instagram", "youtube", "other"]
    target_duration_seconds: int = Field(ge=1)
    execution_budget: ExecutionBudget
    stop_conditions: tuple[str, ...] = Field(min_length=1)
    acceptance_gates: tuple[str, ...] = Field(min_length=1)
    rights_state: Literal["confirmed_for_analysis", "analysis_only", "unknown", "restricted"]
    requires_human_approval: Literal[True]

    @model_validator(mode="after")
    def validate_selected_component(self) -> ReplicationPlan:
        _validate_direct_refs(
            self,
            (
                (self.pattern_hypothesis_ref, "pattern_hypothesis"),
                (self.control_reference_ref, "reference_bundle"),
            ),
        )
        _validate_mechanism_partition(
            self.primary_mechanism,
            self.selected_component,
            self.frozen_components,
        )
        return self


class ClaimMapping(_FrozenModel):
    claim_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    claim_text: str = Field(min_length=1, max_length=4000)
    disposition: Literal["bind", "exclude", "non_product_claim", "unsupported"]
    fact_id: str | None = Field(pattern=_IDENTIFIER_PATTERN)
    fact_status: Literal["confirmed", "locked", "unconfirmed", "rejected"] | None
    evidence_refs: tuple[str, ...]
    reason: str | None = Field(max_length=2000)

    @model_validator(mode="after")
    def validate_fact_binding(self) -> ClaimMapping:
        if self.disposition == "bind":
            if (
                self.fact_id is None
                or self.fact_status not in {"confirmed", "locked"}
                or not self.evidence_refs
            ):
                raise ValueError("fact_binding_invalid")
        elif self.disposition in {"non_product_claim", "unsupported"} and (
            self.fact_id is not None or self.fact_status is not None
        ):
            raise ValueError("fact_binding_invalid")
        return self


class FactMap(ArtifactEnvelope):
    schema_version: Literal["sv.fact-map.v1"]
    artifact_type: Literal["fact_map"]
    replication_plan_ref: ArtifactRef
    claim_scope: Literal["product_claims", "no_product_claims"]
    product_snapshot_id: str | None = Field(pattern=_IDENTIFIER_PATTERN)
    product_snapshot_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    claim_mappings: tuple[ClaimMapping, ...]
    selected_fact_ids: tuple[str, ...]
    excluded_fact_ids: tuple[str, ...]
    unsupported_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_fact_sets(self) -> FactMap:
        _validate_direct_refs(self, ((self.replication_plan_ref, "replication_plan"),))
        selected = set(self.selected_fact_ids)
        excluded = set(self.excluded_fact_ids)
        if selected & excluded:
            raise ValueError("fact_sets_overlap")
        bound = {
            mapping.fact_id
            for mapping in self.claim_mappings
            if mapping.disposition == "bind" and mapping.fact_id is not None
        }
        if self.claim_scope == "no_product_claims":
            if (
                self.subject_binding.state != "not_applicable"
                or self.product_snapshot_id is not None
                or self.product_snapshot_digest is not None
                or self.claim_mappings
                or selected
                or excluded
                or self.unsupported_claims
            ):
                raise ValueError("claim_scope_invalid")
        else:
            if bound != selected:
                raise ValueError("fact_binding_invalid")
            if (
                self.subject_binding.state not in {"exact_snapshot", "reviewed_snapshot_selection"}
                or self.product_snapshot_id is None
                or self.product_snapshot_digest is None
                or not selected
                or self.subject_binding.product_snapshot_id != self.product_snapshot_id
                or self.subject_binding.product_snapshot_digest != self.product_snapshot_digest
            ):
                raise ValueError("claim_scope_invalid")
        return self


class ReplicationContract(ArtifactEnvelope):
    schema_version: Literal["sv.replication-contract.v1"]
    artifact_type: Literal["replication_contract"]
    replication_plan_ref: ArtifactRef
    fact_map_ref: ArtifactRef
    decomposition_map_ref: ArtifactRef
    primary_mechanism: PrimaryMechanism
    selected_component: MechanismComponent
    frozen_components: tuple[MechanismComponent, ...]
    claim_scope: Literal["product_claims", "no_product_claims"]
    control_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    variant_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    changed_dimension: str = Field(min_length=1, max_length=512)
    frozen_configuration: FrozenConfiguration
    selected_fact_ids: tuple[str, ...]
    excluded_fact_ids: tuple[str, ...]
    stop_conditions: tuple[str, ...] = Field(min_length=1)
    acceptance_gates: tuple[str, ...] = Field(min_length=1)
    rights_state: Literal["confirmed_for_analysis", "analysis_only", "unknown", "restricted"]
    approval_ref: str = Field(pattern=_IDENTIFIER_PATTERN)
    immutable: Literal[True]

    @model_validator(mode="after")
    def validate_contract(self) -> ReplicationContract:
        _validate_direct_refs(
            self,
            (
                (self.replication_plan_ref, "replication_plan"),
                (self.fact_map_ref, "fact_map"),
                (self.decomposition_map_ref, "decomposition_map"),
            ),
        )
        _validate_mechanism_partition(
            self.primary_mechanism,
            self.selected_component,
            self.frozen_components,
        )
        if set(self.selected_fact_ids) & set(self.excluded_fact_ids):
            raise ValueError("fact_sets_overlap")
        if self.claim_scope == "no_product_claims":
            if (
                self.subject_binding.state != "not_applicable"
                or self.selected_fact_ids
                or self.excluded_fact_ids
            ):
                raise ValueError("claim_scope_invalid")
        elif (
            self.subject_binding.state not in {"exact_snapshot", "reviewed_snapshot_selection"}
            or not self.selected_fact_ids
        ):
            raise ValueError("claim_scope_invalid")
        if (
            self.subject_binding.market is not None
            and self.subject_binding.market != self.frozen_configuration.market
        ):
            raise ValueError("contract_configuration_invalid")
        return self


class NarrativeTransformationPayload(_FrozenModel):
    mechanism: Literal["narrative-transformation"]
    component: Literal["narrative_arc"]
    frozen_components: tuple[MechanismComponent, ...]
    source_arc: tuple[str, ...] = Field(min_length=1)
    transformed_arc: tuple[str, ...] = Field(min_length=1)
    preserved_truths: tuple[str, ...]


class ProofDemonstrationPayload(_FrozenModel):
    mechanism: Literal["proof-demonstration"]
    component: Literal["proof_device"]
    frozen_components: tuple[MechanismComponent, ...]
    proof_setup: str = Field(min_length=1)
    observable_result: str = Field(min_length=1)
    boundary_disclosures: tuple[str, ...]


class ExperiencePovPayload(_FrozenModel):
    mechanism: Literal["experience-pov"]
    component: Literal["experience_pov"]
    frozen_components: tuple[MechanismComponent, ...]
    pov_actor: str = Field(min_length=1)
    moment: str = Field(min_length=1)
    sensory_cues: tuple[str, ...]


class AttentionAnchor(_FrozenModel):
    component: AttentionComponent
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    carrier: str = Field(min_length=1, max_length=256)
    observable_function: str = Field(min_length=1, max_length=1000)
    surface_class: Literal["text", "visual", "audio", "motion", "mixed"]
    source_ref: str = Field(min_length=1, max_length=512)
    availability: ObservationState
    shot_or_phase_anchor: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_anchor_range(self) -> AttentionAnchor:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("mechanism_safety_fields_invalid")
        return self


class AttentionGrammarPayload(_FrozenModel):
    mechanism: Literal["attention-grammar"]
    component: AttentionComponent
    frozen_components: tuple[AttentionComponent, ...]
    anchors: tuple[AttentionAnchor, ...] = Field(min_length=1)
    pattern_identity: PatternIdentity
    target_surface_substitutions: tuple[str, ...] = Field(min_length=1)
    sound_policy: Literal[
        "licensed_target",
        "functional_substitution",
        "silent",
        "not_applicable",
    ]
    hook_trigger: str = Field(min_length=1)
    reveal_cadence: str = Field(min_length=1)
    caption_cadence: str = Field(min_length=1)
    visual_contrast: str = Field(min_length=1)
    sonic_timing: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_attention_safety(self) -> AttentionGrammarPayload:
        _validate_mechanism_partition(self.mechanism, self.component, self.frozen_components)
        if not any(anchor.component == self.component for anchor in self.anchors):
            raise ValueError("mechanism_safety_fields_invalid")
        return self


class PromotionContractBinding(_FrozenModel):
    state: Literal["eligible", "not_applicable"]
    promotion_fact_id: str | None = Field(pattern=_IDENTIFIER_PATTERN)
    promotion_fact_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    value_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    database_time_valid_at: datetime | None
    product_snapshot_id: str | None = Field(pattern=_IDENTIFIER_PATTERN)
    product_snapshot_digest: str | None = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_promotion_binding(self) -> PromotionContractBinding:
        values = (
            self.promotion_fact_id,
            self.promotion_fact_digest,
            self.value_digest,
            self.database_time_valid_at,
            self.product_snapshot_id,
            self.product_snapshot_digest,
        )
        if self.state == "eligible" and any(value is None for value in values):
            raise ValueError("mechanism_safety_fields_invalid")
        if self.state == "not_applicable" and any(value is not None for value in values):
            raise ValueError("mechanism_safety_fields_invalid")
        return self


class CtaPolicy(_FrozenModel):
    pattern_policy: str = Field(min_length=1, max_length=1000)
    final_cta_role: str = Field(min_length=1, max_length=256)
    visible_copy_owner: Literal["server"]
    provider_may_write_visible_cta: Literal[False]


class ActionPathBinding(_FrozenModel):
    state: Literal["reviewed_binding", "not_applicable"]
    destination_ref: str | None = Field(default=None, max_length=512)
    external_execution: Literal[False]

    @model_validator(mode="after")
    def validate_action_path(self) -> ActionPathBinding:
        if (self.state == "reviewed_binding") != (self.destination_ref is not None):
            raise ValueError("mechanism_safety_fields_invalid")
        return self


class ProviderExclusion(_FrozenModel):
    excluded_surfaces: tuple[str, ...] = Field(min_length=1)
    provider_may_write_visible_copy: Literal[False]
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class ConversionActionPayload(_FrozenModel):
    mechanism: Literal["conversion-action"]
    component: ConversionComponent
    frozen_components: tuple[ConversionComponent, ...]
    objection_resolution: str = Field(min_length=1)
    promotion_contract: PromotionContractBinding
    cta_invitation: str = Field(min_length=1)
    action_path: str = Field(min_length=1)
    cta_policy: CtaPolicy
    action_path_binding: ActionPathBinding
    provider_exclusion: ProviderExclusion

    @model_validator(mode="after")
    def validate_conversion_safety(self) -> ConversionActionPayload:
        _validate_mechanism_partition(self.mechanism, self.component, self.frozen_components)
        return self


TrendEvidenceState = Literal[
    "confirmed",
    "unknown",
    "not_applicable",
    "restricted",
    "blocked",
]


class TrendAdmissionRecord(_FrozenModel):
    evidence_scope: tuple[str, ...] = Field(min_length=1)
    freshness_window_days: int = Field(ge=1)
    source_refs: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...]
    analysis_evidence_state: TrendEvidenceState
    adaptation_evidence_state: TrendEvidenceState
    source_audio_evidence_state: TrendEvidenceState
    template_evidence_state: TrendEvidenceState
    platform_constraints: tuple[str, ...] = Field(min_length=1)
    market_constraints: tuple[str, ...] = Field(min_length=1)
    locale_constraints: tuple[str, ...] = Field(min_length=1)
    assessment_state: Literal["admitted_with_limits", "blocked", "unknown"]
    execution_capability: Literal["not_implemented"]
    external_action_requested: Literal[False]
    target_text_substitutions: tuple[str, ...]
    target_visual_substitutions: tuple[str, ...]
    target_audio_substitutions: tuple[str, ...]
    source_identity_exclusions: tuple[str, ...] = Field(min_length=1)
    originality_handoff: tuple[str, ...] = Field(min_length=1)


class TrendNativePayload(_FrozenModel):
    mechanism: Literal["trend-native"]
    component: TrendComponent
    frozen_components: tuple[TrendComponent, ...]
    trend_signal_binding: str = Field(min_length=1)
    trend_semantic_frame: str = Field(min_length=1)
    template_grammar: str = Field(min_length=1)
    audio_function: str = Field(min_length=1)
    admission: TrendAdmissionRecord

    @model_validator(mode="after")
    def validate_trend_safety(self) -> TrendNativePayload:
        _validate_mechanism_partition(self.mechanism, self.component, self.frozen_components)
        return self


MechanismPayload = Annotated[
    NarrativeTransformationPayload
    | ProofDemonstrationPayload
    | ExperiencePovPayload
    | AttentionGrammarPayload
    | ConversionActionPayload
    | TrendNativePayload,
    Field(discriminator="mechanism"),
]


class AdaptationPackage(ArtifactEnvelope):
    schema_version: Literal["sv.adaptation-package.v1"]
    artifact_type: Literal["adaptation_package"]
    replication_contract_ref: ArtifactRef
    primary_mechanism: PrimaryMechanism
    selected_component: MechanismComponent
    mechanism_payload: MechanismPayload

    @model_validator(mode="before")
    @classmethod
    def validate_payload_cardinality(cls, value: object) -> object:
        if isinstance(value, Mapping):
            payload_keys = {str(key) for key in value if str(key).endswith("_payload")}
            if payload_keys != {"mechanism_payload"}:
                raise ValueError("adaptation_payload_cardinality_invalid")
        return value

    @model_validator(mode="after")
    def validate_mechanism_payload(self) -> AdaptationPackage:
        _validate_direct_refs(self, ((self.replication_contract_ref, "replication_contract"),))
        payload = self.mechanism_payload
        if (
            payload.mechanism != self.primary_mechanism
            or payload.component != self.selected_component
        ):
            raise ValueError("adaptation_mechanism_mismatch")
        _validate_mechanism_partition(
            payload.mechanism, payload.component, payload.frozen_components
        )
        if isinstance(payload, ConversionActionPayload):
            promotion = payload.promotion_contract
            if promotion.state == "eligible" and (
                self.subject_binding.state not in {"exact_snapshot", "reviewed_snapshot_selection"}
                or promotion.product_snapshot_id != self.subject_binding.product_snapshot_id
                or promotion.product_snapshot_digest != self.subject_binding.product_snapshot_digest
            ):
                raise ValueError("mechanism_safety_fields_invalid")
        return self


IntegrityGate = Literal[
    "artifact_traceability",
    "technical_profile",
    "communicative_surface",
    "target_identity_continuity",
    "source_use_scope",
    "originality_delta",
]

_INTEGRITY_GATES = frozenset(
    {
        "artifact_traceability",
        "technical_profile",
        "communicative_surface",
        "target_identity_continuity",
        "source_use_scope",
        "originality_delta",
    }
)


class IntegrityGateCheck(_FrozenModel):
    gate: IntegrityGate
    state: Literal[
        "blocked",
        "unknown",
        "not_applicable_pending_artifact",
        "reviewed_with_limits",
        "passed",
    ]
    findings: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    unknowns: tuple[str, ...]
    fallback_strategy: tuple[str, ...]

    @model_validator(mode="after")
    def validate_gate_state(self) -> IntegrityGateCheck:
        if self.state == "passed" and (not self.evidence_refs or self.blockers or self.unknowns):
            raise ValueError("media_integrity_gate_state_invalid")
        if self.state == "reviewed_with_limits" and (
            not self.evidence_refs or self.blockers or not self.unknowns
        ):
            raise ValueError("media_integrity_gate_state_invalid")
        if self.state == "blocked" and (not self.blockers or not self.findings):
            raise ValueError("media_integrity_gate_state_invalid")
        if self.state in {"unknown", "not_applicable_pending_artifact"} and (
            self.blockers or not self.unknowns
        ):
            raise ValueError("media_integrity_gate_state_invalid")
        if self.state != "passed" and not self.fallback_strategy:
            raise ValueError("media_integrity_gate_state_invalid")
        return self


class ScriptVersionRef(ArtifactRef):
    artifact_type: Literal["script_version"]


class StoryboardVersionRef(ArtifactRef):
    artifact_type: Literal["storyboard_version"]


class ControlledArtifactRef(ArtifactRef):
    artifact_type: Literal["controlled_media"]


class StoryboardLineage(_FrozenModel):
    storyboard_version_ref: StoryboardVersionRef
    source_script_version_ref: ScriptVersionRef
    evidence_scope: Literal["declared_artifact_lineage"]


_FUTURE_ARTIFACT_GATES = frozenset(
    {
        "artifact_traceability",
        "technical_profile",
        "target_identity_continuity",
        "originality_delta",
    }
)


class MediaIntegrityRecord(ArtifactEnvelope):
    schema_version: Literal["sv.media-integrity-record.v1"]
    artifact_type: Literal["media_integrity_record"]
    replication_contract_ref: ArtifactRef
    adaptation_package_ref: ArtifactRef
    script_version_ref: ScriptVersionRef | None
    storyboard_version_ref: StoryboardVersionRef | None
    storyboard_lineage: StoryboardLineage | None
    controlled_artifact_ref: ControlledArtifactRef | None
    mode: Literal["preflight", "artifact_review"]
    gate_checks: tuple[IntegrityGateCheck, ...]
    disposition: Literal["blocked", "proceed_with_limits", "ready_for_next_gate"]
    fallback_strategy: tuple[str, ...]
    blockers: tuple[str, ...]
    unknowns: tuple[str, ...]
    evidence_limits: tuple[str, ...]

    @model_validator(mode="after")
    def validate_integrity_scope(self) -> MediaIntegrityRecord:
        direct_refs: list[tuple[ArtifactRef, str]] = [
            (self.replication_contract_ref, "replication_contract"),
            (self.adaptation_package_ref, "adaptation_package"),
        ]
        if self.script_version_ref is not None:
            direct_refs.append((self.script_version_ref, "script_version"))
        if self.storyboard_version_ref is not None:
            direct_refs.append((self.storyboard_version_ref, "storyboard_version"))
        if self.controlled_artifact_ref is not None:
            direct_refs.append((self.controlled_artifact_ref, "controlled_media"))
        _validate_direct_refs(self, tuple(direct_refs))
        if self.script_version_ref is None and self.storyboard_version_ref is None:
            raise ValueError("media_integrity_artifact_refs_invalid")
        has_script = self.script_version_ref is not None
        has_storyboard = self.storyboard_version_ref is not None
        if has_script and has_storyboard:
            if (
                self.storyboard_lineage is None
                or self.storyboard_lineage.storyboard_version_ref != self.storyboard_version_ref
                or self.storyboard_lineage.source_script_version_ref != self.script_version_ref
            ):
                raise ValueError("storyboard_lineage_mismatch")
        elif self.storyboard_lineage is not None:
            raise ValueError("storyboard_lineage_mismatch")
        if self.mode == "preflight" and self.controlled_artifact_ref is not None:
            raise ValueError("media_integrity_artifact_refs_invalid")
        if self.mode == "artifact_review" and (
            self.controlled_artifact_ref is None or not has_script or not has_storyboard
        ):
            raise ValueError("media_integrity_artifact_refs_invalid")
        gates = [check.gate for check in self.gate_checks]
        if len(gates) != len(_INTEGRITY_GATES) or set(gates) != _INTEGRITY_GATES:
            raise ValueError("media_integrity_gates_invalid")
        if self.mode == "preflight" and any(
            check.gate in _FUTURE_ARTIFACT_GATES
            and check.state != "not_applicable_pending_artifact"
            for check in self.gate_checks
        ):
            raise ValueError("media_integrity_scope_invalid")
        if self.mode == "artifact_review" and any(
            check.state == "not_applicable_pending_artifact" for check in self.gate_checks
        ):
            raise ValueError("media_integrity_scope_invalid")
        gate_blockers = {blocker for check in self.gate_checks for blocker in check.blockers}
        gate_unknowns = {unknown for check in self.gate_checks for unknown in check.unknowns}
        if gate_blockers != set(self.blockers) or gate_unknowns != set(self.unknowns):
            raise ValueError("media_integrity_summary_invalid")
        states = {check.state for check in self.gate_checks}
        if self.disposition == "ready_for_next_gate":
            if states != {"passed"} or self.blockers or self.unknowns:
                raise ValueError("media_integrity_disposition_invalid")
        elif self.disposition == "blocked":
            if "blocked" not in states or not self.blockers:
                raise ValueError("media_integrity_disposition_invalid")
        elif "blocked" in states or states == {"passed"}:
            raise ValueError("media_integrity_disposition_invalid")
        return self


class ReplicationFinding(ArtifactEnvelope):
    schema_version: Literal["sv.replication-finding.v1"]
    artifact_type: Literal["replication_finding"]
    replication_contract_ref: ArtifactRef
    adaptation_package_ref: ArtifactRef
    media_integrity_record_ref: ArtifactRef
    conclusion_scope: Literal["local_fixture", "reviewed_artifact", "experiment_window"]
    observations: tuple[ObservationValue, ...]
    bounded_inferences: tuple[str, ...]
    unknowns: tuple[str, ...]
    anomalies: tuple[str, ...]
    next_actions: tuple[str, ...]
    causal_claim: Literal[False]
    production_acceptance: Literal[False]

    @model_validator(mode="after")
    def validate_direct_refs(self) -> ReplicationFinding:
        _validate_direct_refs(
            self,
            (
                (self.replication_contract_ref, "replication_contract"),
                (self.adaptation_package_ref, "adaptation_package"),
                (self.media_integrity_record_ref, "media_integrity_record"),
            ),
        )
        if self.evidence_level == "fact" and any(
            observation.state == "source_ambiguous" for observation in self.observations
        ):
            raise ValueError("missing_semantics_invalid")
        return self


ARTIFACT_MODELS: dict[str, type[ArtifactEnvelope]] = {
    "reference_bundle": ReferenceBundle,
    "decomposition_map": DecompositionMap,
    "pattern_hypothesis": PatternHypothesis,
    "replication_plan": ReplicationPlan,
    "fact_map": FactMap,
    "replication_contract": ReplicationContract,
    "adaptation_package": AdaptationPackage,
    "media_integrity_record": MediaIntegrityRecord,
    "replication_finding": ReplicationFinding,
}


def _canonical_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactValidationError(
                "ARTIFACT_NUMBER_NON_FINITE",
                path="$",
                detail="artifact_number_non_finite",
            )
        return 0 if value == 0 else value
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def canonical_artifact_digest(payload: Mapping[str, Any]) -> str:
    """Digest one normalized artifact body while excluding its digest field."""

    body = dict(payload)
    body.pop("content_digest", None)
    body = _canonical_value(body)
    serialized = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validation_error(exc: ValidationError) -> ArtifactValidationError:
    error = exc.errors(include_url=False)[0]
    path = ".".join(str(item) for item in error["loc"])
    detail = str(error["msg"])
    if "artifact_digest_mismatch" in detail:
        code = "ARTIFACT_DIGEST_MISMATCH"
    elif "artifact_number_non_finite" in detail:
        code = "ARTIFACT_NUMBER_NON_FINITE"
    elif "source_locator_invalid" in detail:
        code = "SOURCE_LOCATOR_INVALID"
    elif path.rsplit(".", maxsplit=1)[-1] in {"task_ref", "run_ref"}:
        code = "ARTIFACT_TASK_RUN_REQUIRED"
    elif path.endswith("_ref.artifact_type") and error["type"] == "literal_error":
        code = "DIRECT_REF_TYPE_INVALID"
    elif "artifact_ref_scope_mismatch" in detail:
        code = "ARTIFACT_REF_SCOPE_MISMATCH"
    elif "direct_ref_type_invalid" in detail:
        code = "DIRECT_REF_TYPE_INVALID"
    elif "direct_ref_input_missing" in detail:
        code = "DIRECT_REF_INPUT_MISSING"
    elif "missing_semantics_invalid" in detail:
        code = "MISSING_SEMANTICS_INVALID"
    elif "decomposition_mechanism_mismatch" in detail:
        code = "DECOMPOSITION_MECHANISM_MISMATCH"
    elif "decomposition_observations_invalid" in detail or path.startswith(
        "mechanism_observations"
    ):
        code = "DECOMPOSITION_OBSERVATIONS_INVALID"
    elif "mechanism_component_invalid" in detail:
        code = "MECHANISM_COMPONENT_INVALID"
    elif "frozen_components_invalid" in detail:
        code = "FROZEN_COMPONENTS_INVALID"
    elif "fact_binding_invalid" in detail:
        code = "FACT_BINDING_INVALID"
    elif "claim_scope_invalid" in detail:
        code = "CLAIM_SCOPE_INVALID"
    elif "fact_sets_overlap" in detail:
        code = "FACT_SETS_OVERLAP"
    elif "adaptation_payload_cardinality_invalid" in detail:
        code = "ADAPTATION_PAYLOAD_CARDINALITY_INVALID"
    elif "adaptation_mechanism_mismatch" in detail:
        code = "ADAPTATION_MECHANISM_MISMATCH"
    elif "mechanism_safety_fields_invalid" in detail or path.startswith("mechanism_payload"):
        code = "MECHANISM_SAFETY_FIELDS_INVALID"
    elif "media_integrity_scope_invalid" in detail:
        code = "MEDIA_INTEGRITY_SCOPE_INVALID"
    elif "media_integrity_gates_invalid" in detail:
        code = "MEDIA_INTEGRITY_GATES_INVALID"
    elif "media_integrity_gate_state_invalid" in detail:
        code = "MEDIA_INTEGRITY_GATE_STATE_INVALID"
    elif "media_integrity_artifact_refs_invalid" in detail:
        code = "MEDIA_INTEGRITY_ARTIFACT_REFS_INVALID"
    elif "storyboard_lineage_mismatch" in detail:
        code = "STORYBOARD_LINEAGE_MISMATCH"
    elif path.startswith("storyboard_lineage"):
        code = "STORYBOARD_LINEAGE_INVALID"
    elif "media_integrity_summary_invalid" in detail:
        code = "MEDIA_INTEGRITY_SUMMARY_INVALID"
    elif "media_integrity_disposition_invalid" in detail:
        code = "MEDIA_INTEGRITY_DISPOSITION_INVALID"
    elif "contract_configuration_invalid" in detail or path.startswith("frozen_configuration"):
        code = "CONTRACT_CONFIGURATION_INVALID"
    elif path == "status" and error["type"] == "literal_error":
        code = "ARTIFACT_STATUS_INVALID"
    elif path.startswith("subject_binding"):
        code = "SUBJECT_BINDING_INVALID"
    else:
        code = "ARTIFACT_SCHEMA_INVALID"
    return ArtifactValidationError(code, path=path, detail=detail)


def _resolve_model(
    payload: object, *, expected_type: str | None = None
) -> tuple[type[ArtifactEnvelope], dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise ArtifactValidationError(
            "ARTIFACT_NOT_OBJECT", path="$", detail="Artifact must be a JSON object."
        )
    value = dict(payload)
    artifact_type = value.get("artifact_type")
    if not isinstance(artifact_type, str):
        raise ArtifactValidationError(
            "ARTIFACT_TYPE_MISSING",
            path="artifact_type",
            detail="artifact_type is required.",
        )
    if expected_type is not None and artifact_type != expected_type:
        raise ArtifactValidationError(
            "ARTIFACT_TYPE_MISMATCH",
            path="artifact_type",
            detail=f"Expected {expected_type}, received {artifact_type}.",
        )
    model = ARTIFACT_MODELS.get(artifact_type)
    if model is None:
        raise ArtifactValidationError(
            "ARTIFACT_TYPE_UNSUPPORTED",
            path="artifact_type",
            detail=f"Unsupported artifact_type: {artifact_type}.",
        )
    return model, value


def bind_artifact_digest(payload: object) -> dict[str, Any]:
    """Normalize an artifact and bind its canonical digest."""

    model, value = _resolve_model(payload)
    value["content_digest"] = "0" * 64
    try:
        normalized = model.model_validate(value, context={"skip_digest": True}).model_dump(
            mode="json"
        )
    except ValidationError as exc:
        raise _validation_error(exc) from exc
    normalized["content_digest"] = canonical_artifact_digest(normalized)
    return validate_artifact(normalized)


def validate_artifact(payload: object, *, expected_type: str | None = None) -> dict[str, Any]:
    """Validate one artifact through its closed public schema."""

    model, value = _resolve_model(payload, expected_type=expected_type)
    try:
        return model.model_validate(value).model_dump(mode="json")
    except ValidationError as exc:
        raise _validation_error(exc) from exc


def _chain_ref_key(ref: Mapping[str, Any]) -> tuple[str, str, str, int]:
    return (
        str(ref["task_ref"]),
        str(ref["run_ref"]),
        str(ref["artifact_id"]),
        int(ref["version"]),
    )


def _raise_chain_error(code: str, *, path: str, detail: str) -> NoReturn:
    raise ArtifactValidationError(code, path=path, detail=detail)


def _validated_external_ref(payload: object, *, index: int) -> dict[str, Any]:
    try:
        return ArtifactRef.model_validate(payload).model_dump(mode="json")
    except ValidationError as exc:
        error = exc.errors(include_url=False)[0]
        suffix = ".".join(str(item) for item in error["loc"])
        _raise_chain_error(
            "ARTIFACT_REF_INVALID",
            path=f"external_refs.{index}.{suffix}".rstrip("."),
            detail=str(error["msg"]),
        )


def _validate_chain_relationships(
    artifacts: tuple[dict[str, Any], ...],
    resolved_refs: Mapping[tuple[str, str, str, int], dict[str, Any]],
) -> None:
    ambiguous_evidence_refs = {
        evidence_ref
        for artifact in artifacts
        if artifact["artifact_type"] == "reference_bundle"
        for observation in artifact["observations"]
        if observation["state"] == "source_ambiguous"
        for evidence_ref in (
            observation["observation_ref"],
            *observation["source_refs"],
        )
    }
    for artifact in artifacts:
        artifact_type = artifact["artifact_type"]
        if artifact_type == "pattern_hypothesis":
            decomposition = resolved_refs[_chain_ref_key(artifact["decomposition_map_ref"])]
            if decomposition["primary_mechanism"] != artifact["primary_mechanism"]:
                _raise_chain_error(
                    "CHAIN_MECHANISM_MISMATCH",
                    path=f"{artifact['artifact_id']}.primary_mechanism",
                    detail="PatternHypothesis does not match DecompositionMap.",
                )
        elif artifact_type == "fact_map":
            for mapping in artifact["claim_mappings"]:
                if mapping["disposition"] == "bind" and ambiguous_evidence_refs & set(
                    mapping["evidence_refs"]
                ):
                    _raise_chain_error(
                        "SOURCE_AMBIGUOUS_NOT_FACT",
                        path=f"{artifact['artifact_id']}.claim_mappings",
                        detail=("A source-ambiguous observation cannot support a Fact binding."),
                    )
        elif artifact_type == "replication_plan":
            hypothesis = resolved_refs[_chain_ref_key(artifact["pattern_hypothesis_ref"])]
            if hypothesis["primary_mechanism"] != artifact["primary_mechanism"]:
                _raise_chain_error(
                    "CHAIN_MECHANISM_MISMATCH",
                    path=f"{artifact['artifact_id']}.primary_mechanism",
                    detail="ReplicationPlan does not match PatternHypothesis.",
                )
            decomposition = resolved_refs[_chain_ref_key(hypothesis["decomposition_map_ref"])]
            if decomposition["reference_bundle_ref"] != artifact["control_reference_ref"]:
                _raise_chain_error(
                    "CHAIN_LINEAGE_MISMATCH",
                    path=f"{artifact['artifact_id']}.control_reference_ref",
                    detail=(
                        "ReplicationPlan control reference does not match the "
                        "decomposed ReferenceBundle."
                    ),
                )
        elif artifact_type == "replication_contract":
            plan = resolved_refs[_chain_ref_key(artifact["replication_plan_ref"])]
            fact_map = resolved_refs[_chain_ref_key(artifact["fact_map_ref"])]
            hypothesis = resolved_refs[_chain_ref_key(plan["pattern_hypothesis_ref"])]
            if (
                fact_map["replication_plan_ref"] != artifact["replication_plan_ref"]
                or hypothesis["decomposition_map_ref"] != artifact["decomposition_map_ref"]
            ):
                _raise_chain_error(
                    "CHAIN_LINEAGE_MISMATCH",
                    path=f"{artifact['artifact_id']}.input_refs",
                    detail=(
                        "ReplicationContract inputs do not share the same Plan and "
                        "Decomposition lineage."
                    ),
                )
            mechanism_fields = (
                "primary_mechanism",
                "selected_component",
                "frozen_components",
            )
            if any(artifact[field] != plan[field] for field in mechanism_fields):
                _raise_chain_error(
                    "CHAIN_MECHANISM_MISMATCH",
                    path=f"{artifact['artifact_id']}.primary_mechanism",
                    detail="ReplicationContract does not match ReplicationPlan.",
                )
            plan_contract_fields = (
                "control_id",
                "variant_id",
                "changed_dimension",
                "stop_conditions",
                "acceptance_gates",
                "rights_state",
            )
            frozen = artifact["frozen_configuration"]
            configuration_matches = (
                frozen["platform"] == plan["target_platform"]
                and frozen["duration_seconds"] == plan["target_duration_seconds"]
                and frozen["execution_budget"] == plan["execution_budget"]
                and all(artifact[field] == plan[field] for field in plan_contract_fields)
            )
            if not configuration_matches:
                _raise_chain_error(
                    "CHAIN_CONFIGURATION_MISMATCH",
                    path=f"{artifact['artifact_id']}.frozen_configuration",
                    detail="ReplicationContract does not freeze ReplicationPlan values.",
                )
            fact_fields = (
                "claim_scope",
                "selected_fact_ids",
                "excluded_fact_ids",
                "subject_binding",
            )
            if any(artifact[field] != fact_map[field] for field in fact_fields):
                _raise_chain_error(
                    "CHAIN_CLAIM_SCOPE_MISMATCH",
                    path=f"{artifact['artifact_id']}.claim_scope",
                    detail="ReplicationContract does not match FactMap binding.",
                )
        elif artifact_type == "adaptation_package":
            contract = resolved_refs[_chain_ref_key(artifact["replication_contract_ref"])]
            payload = artifact["mechanism_payload"]
            if artifact["subject_binding"] != contract["subject_binding"]:
                _raise_chain_error(
                    "CHAIN_SUBJECT_BINDING_MISMATCH",
                    path=f"{artifact['artifact_id']}.subject_binding",
                    detail="AdaptationPackage does not preserve contract subject binding.",
                )
            if (
                artifact["primary_mechanism"] != contract["primary_mechanism"]
                or artifact["selected_component"] != contract["selected_component"]
                or payload["frozen_components"] != contract["frozen_components"]
            ):
                _raise_chain_error(
                    "CHAIN_MECHANISM_MISMATCH",
                    path=f"{artifact['artifact_id']}.primary_mechanism",
                    detail="AdaptationPackage does not match ReplicationContract.",
                )
        elif artifact_type == "media_integrity_record":
            contract = resolved_refs[_chain_ref_key(artifact["replication_contract_ref"])]
            adaptation = resolved_refs[_chain_ref_key(artifact["adaptation_package_ref"])]
            if (
                artifact["subject_binding"] != contract["subject_binding"]
                or artifact["subject_binding"] != adaptation["subject_binding"]
            ):
                _raise_chain_error(
                    "CHAIN_SUBJECT_BINDING_MISMATCH",
                    path=f"{artifact['artifact_id']}.subject_binding",
                    detail="MediaIntegrityRecord does not preserve subject binding.",
                )
            if adaptation["replication_contract_ref"] != artifact["replication_contract_ref"]:
                _raise_chain_error(
                    "CHAIN_LINEAGE_MISMATCH",
                    path=f"{artifact['artifact_id']}.adaptation_package_ref",
                    detail="MediaIntegrityRecord contract and adaptation lineage differ.",
                )
        elif artifact_type == "replication_finding":
            integrity = resolved_refs[_chain_ref_key(artifact["media_integrity_record_ref"])]
            contract = resolved_refs[_chain_ref_key(artifact["replication_contract_ref"])]
            adaptation = resolved_refs[_chain_ref_key(artifact["adaptation_package_ref"])]
            if (
                artifact["subject_binding"] != contract["subject_binding"]
                or artifact["subject_binding"] != adaptation["subject_binding"]
                or artifact["subject_binding"] != integrity["subject_binding"]
            ):
                _raise_chain_error(
                    "CHAIN_SUBJECT_BINDING_MISMATCH",
                    path=f"{artifact['artifact_id']}.subject_binding",
                    detail="ReplicationFinding does not preserve subject binding.",
                )
            if (
                integrity["mode"] != "artifact_review"
                or integrity["script_version_ref"] is None
                or integrity["storyboard_version_ref"] is None
                or integrity["controlled_artifact_ref"] is None
            ):
                _raise_chain_error(
                    "CHAIN_INCOMPLETE_PREFLIGHT",
                    path=f"{artifact['artifact_id']}.media_integrity_record_ref",
                    detail=(
                        "ReplicationFinding requires a completed artifact review with "
                        "ScriptVersion, StoryboardVersion, and controlled media refs."
                    ),
                )
            storyboard_lineage = integrity["storyboard_lineage"]
            if (
                storyboard_lineage is None
                or storyboard_lineage["storyboard_version_ref"]
                != integrity["storyboard_version_ref"]
                or storyboard_lineage["source_script_version_ref"]
                != integrity["script_version_ref"]
            ):
                _raise_chain_error(
                    "CHAIN_STORYBOARD_LINEAGE_MISMATCH",
                    path=f"{artifact['artifact_id']}.media_integrity_record_ref",
                    detail=(
                        "Completed chain storyboard lineage does not bind the reviewed "
                        "StoryboardVersion to its declared source ScriptVersion."
                    ),
                )
            if (
                artifact["replication_contract_ref"] != integrity["replication_contract_ref"]
                or artifact["adaptation_package_ref"] != integrity["adaptation_package_ref"]
            ):
                _raise_chain_error(
                    "CHAIN_LINEAGE_MISMATCH",
                    path=f"{artifact['artifact_id']}.media_integrity_record_ref",
                    detail="ReplicationFinding and MediaIntegrityRecord lineage differ.",
                )


def validate_artifact_chain(
    payloads: Iterable[object], *, external_refs: Iterable[object] = ()
) -> tuple[dict[str, Any], ...]:
    """Validate canonical artifacts and resolve every declared input reference."""

    artifacts = tuple(validate_artifact(payload) for payload in payloads)
    if not artifacts:
        _raise_chain_error("CHAIN_EMPTY", path="$", detail="Artifact chain must not be empty.")
    scopes = {(item["task_ref"], item["run_ref"]) for item in artifacts}
    if len(scopes) != 1:
        _raise_chain_error(
            "CHAIN_SCOPE_MISMATCH",
            path="$",
            detail="All canonical artifacts in one chain must share task_ref and run_ref.",
        )

    canonical_by_key: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for artifact in artifacts:
        key = _chain_ref_key(artifact)
        if key in canonical_by_key:
            _raise_chain_error(
                "CHAIN_ARTIFACT_DUPLICATE",
                path=str(artifact["artifact_id"]),
                detail="Artifact identity and version must be unique in one chain.",
            )
        canonical_by_key[key] = artifact

    external_by_key: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for index, payload in enumerate(external_refs):
        ref = _validated_external_ref(payload, index=index)
        key = _chain_ref_key(ref)
        existing = external_by_key.get(key)
        if existing is not None and existing != ref:
            _raise_chain_error(
                "CHAIN_ARTIFACT_DUPLICATE",
                path=f"external_refs.{index}",
                detail="Conflicting external artifact references share one identity.",
            )
        external_by_key[key] = ref

    resolved_refs: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for artifact in artifacts:
        for index, ref in enumerate(artifact["input_refs"]):
            key = _chain_ref_key(ref)
            source = (
                canonical_by_key.get(key)
                if ref["artifact_type"] in ARTIFACT_MODELS
                else external_by_key.get(key)
            )
            path = f"{artifact['artifact_id']}.input_refs.{index}"
            if source is None:
                _raise_chain_error(
                    "CHAIN_REF_MISSING",
                    path=path,
                    detail="Referenced artifact is not present in the validated chain.",
                )
            if source["artifact_type"] != ref["artifact_type"]:
                _raise_chain_error(
                    "CHAIN_REF_TYPE_MISMATCH",
                    path=path,
                    detail="Referenced artifact_type does not match the resolved artifact.",
                )
            if source["content_digest"] != ref["content_digest"]:
                _raise_chain_error(
                    "CHAIN_REF_DIGEST_MISMATCH",
                    path=path,
                    detail="Referenced content_digest does not match the resolved artifact.",
                )
            resolved_refs[key] = source

    _validate_chain_relationships(artifacts, resolved_refs)
    return artifacts


def get_artifact_schema(artifact_type: str) -> dict[str, Any]:
    """Return the machine-readable JSON Schema for one canonical artifact."""

    model = ARTIFACT_MODELS.get(artifact_type)
    if model is None:
        raise ArtifactValidationError(
            "ARTIFACT_TYPE_UNSUPPORTED",
            path="artifact_type",
            detail=f"Unsupported artifact_type: {artifact_type}.",
        )
    return model.model_json_schema()
