from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.products.entities import FactStatus
from app.domain.sv_agent.entities import CreativeDimension
from app.domain.sv_agent.runtime_records import ArtifactType, EvidenceLevel


class ReviewDisposition(StrEnum):
    BLOCKED = "blocked"
    PROCEED_WITH_LIMITS = "proceed_with_limits"
    READY_FOR_NEXT_GATE = "ready_for_next_gate"


class FindingSeverity(StrEnum):
    BLOCKING = "blocking"
    LIMITATION = "limitation"


class FindingCategory(StrEnum):
    ARTIFACT_INTEGRITY = "artifact_integrity"
    SCOPE_LINEAGE = "scope_lineage"
    SINGLE_VARIABLE_ISOLATION = "single_variable_isolation"
    DENY_SET = "deny_set"
    EVIDENCE_BOUNDARY = "evidence_boundary"


class FindingCode(StrEnum):
    ARTIFACT_PAYLOAD_INVALID = "artifact_payload_invalid"
    ARTIFACT_DIGEST_MISMATCH = "artifact_digest_mismatch"
    ARTIFACT_SCOPE_MISMATCH = "artifact_scope_mismatch"
    ARTIFACT_DUPLICATE = "artifact_duplicate"
    REPLICATION_CONTRACT_MISSING = "replication_contract_missing"
    REPLICATION_CONTRACT_AMBIGUOUS = "replication_contract_ambiguous"
    CONTRACT_REVIEW_FIELDS_INVALID = "contract_review_fields_invalid"
    COMPARISON_COVERAGE_MISMATCH = "comparison_coverage_mismatch"
    ISOLATION_EVIDENCE_MISSING = "isolation_evidence_missing"
    MULTIPLE_CHANGED_DIMENSIONS = "multiple_changed_dimensions"
    DECLARED_DIMENSION_MISMATCH = "declared_dimension_mismatch"
    FROZEN_FIELD_CHANGED = "frozen_field_changed"
    EXCLUDED_FACT_RESURRECTION = "excluded_fact_resurrection"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    EVIDENCE_CONFLICT = "evidence_conflict"
    EVIDENCE_REF_MISSING = "evidence_ref_missing"
    EVIDENCE_BOUNDARY_EXCEEDED = "evidence_boundary_exceeded"
    EVIDENCE_LIMITED = "evidence_limited"


class FindingNextAction(StrEnum):
    REPAIR_ARTIFACT = "repair_artifact"
    RESTORE_SINGLE_VARIABLE = "restore_single_variable"
    REMOVE_OR_BIND_CLAIM = "remove_or_bind_claim"
    PROVIDE_EVIDENCE = "provide_evidence"


class ClaimSurface(StrEnum):
    VOICEOVER = "voiceover"
    CAPTION = "caption"
    ON_SCREEN_TEXT = "on_screen_text"
    VISUAL = "visual"
    ACTION = "action"
    ACCEPTANCE = "acceptance"
    TITLE = "title"
    TAG = "tag"
    SHOOTING_LIST = "shooting_list"


class ClaimKind(StrEnum):
    PRODUCT = "product"
    NON_PRODUCT = "non_product"


class EvidencePlane(StrEnum):
    PRODUCT_TRUTH = "product_truth"
    PERFORMANCE = "performance"
    EXPERIMENT = "experiment"
    ASSET = "asset"
    MEDIA_INTEGRITY = "media_integrity"
    RIGHTS = "rights"


class EvidenceState(StrEnum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"
    NOT_REPORTED = "not_reported"
    NOT_COLLECTED = "not_collected"
    SOURCE_AMBIGUOUS = "source_ambiguous"
    UNAVAILABLE = "unavailable"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class TaskRunBinding:
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int


@dataclass(frozen=True, slots=True)
class CanonicalArtifactSnapshot:
    artifact_type: ArtifactType
    artifact_id: str
    version: int
    binding: TaskRunBinding
    declared_digest: str
    canonical_payload_json: str


@dataclass(frozen=True, slots=True)
class MechanismValue:
    component: CreativeDimension
    value_digest: str


@dataclass(frozen=True, slots=True)
class FrozenContextSnapshot:
    configuration_digest: str
    fact_binding_digest: str
    subject_binding_digest: str
    material_scope_digest: str
    claim_contract_digest: str


@dataclass(frozen=True, slots=True)
class VisibleClaimSnapshot:
    claim_id: str
    surface: ClaimSurface
    kind: ClaimKind
    fact_id: str | None
    fact_state: FactStatus | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateSnapshot:
    mechanism_values: tuple[MechanismValue, ...]
    frozen_context: FrozenContextSnapshot
    visible_claims: tuple[VisibleClaimSnapshot, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    evidence_ref: str
    plane: EvidencePlane
    state: EvidenceState
    level: EvidenceLevel
    required_for_next_gate: bool
    product_snapshot_id: str | None = None
    fact_id: str | None = None
    fact_state: FactStatus | None = None


@dataclass(frozen=True, slots=True)
class NextGateReviewPackage:
    binding: TaskRunBinding
    artifacts: tuple[CanonicalArtifactSnapshot, ...]
    control: CandidateSnapshot
    variant: CandidateSnapshot
    evidence: tuple[EvidenceSnapshot, ...]


@dataclass(frozen=True, slots=True)
class ReviewerFinding:
    code: FindingCode
    severity: FindingSeverity
    category: FindingCategory
    path: str
    artifact_ref: str | None
    evidence_refs: tuple[str, ...]
    next_action: FindingNextAction


@dataclass(frozen=True, slots=True)
class ReviewerOutcome:
    disposition: ReviewDisposition
    findings: tuple[ReviewerFinding, ...]


class IndependentReviewer:
    @classmethod
    def review(cls, package: NextGateReviewPackage) -> ReviewerOutcome:
        findings = list(cls._review_artifacts(package))
        if not findings:
            findings.extend(cls._review_single_variable(package))
            findings.extend(cls._review_claims(package))
            findings.extend(cls._review_evidence(package.evidence))
        return _outcome(findings)

    @staticmethod
    def _review_artifacts(
        package: NextGateReviewPackage,
    ) -> tuple[ReviewerFinding, ...]:
        findings: list[ReviewerFinding] = []
        seen: set[tuple[ArtifactType, str, int]] = set()
        for artifact in sorted(
            package.artifacts,
            key=lambda item: (item.artifact_type.value, item.artifact_id, item.version),
        ):
            artifact_ref = (
                f"{artifact.artifact_type.value}:{artifact.artifact_id}:{artifact.version}"
            )
            identity = (artifact.artifact_type, artifact.artifact_id, artifact.version)
            if identity in seen:
                findings.append(
                    ReviewerFinding(
                        code=FindingCode.ARTIFACT_DUPLICATE,
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.SCOPE_LINEAGE,
                        path=f"artifacts[{artifact_ref}]",
                        artifact_ref=artifact_ref,
                        evidence_refs=(),
                        next_action=FindingNextAction.REPAIR_ARTIFACT,
                    )
                )
            else:
                seen.add(identity)
            if artifact.binding != package.binding:
                findings.append(
                    ReviewerFinding(
                        code=FindingCode.ARTIFACT_SCOPE_MISMATCH,
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.SCOPE_LINEAGE,
                        path=f"artifacts[{artifact_ref}].binding",
                        artifact_ref=artifact_ref,
                        evidence_refs=(),
                        next_action=FindingNextAction.REPAIR_ARTIFACT,
                    )
                )
                continue
            try:
                payload = json.loads(artifact.canonical_payload_json)
                if not isinstance(payload, dict):
                    raise TypeError("artifact payload must be an object")
                declared_in_payload = payload.pop("content_digest", None)
                actual_digest = _canonical_artifact_digest(payload)
            except (TypeError, ValueError, json.JSONDecodeError):
                findings.append(
                    ReviewerFinding(
                        code=FindingCode.ARTIFACT_PAYLOAD_INVALID,
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.ARTIFACT_INTEGRITY,
                        path=f"artifacts[{artifact_ref}].canonical_payload_json",
                        artifact_ref=artifact_ref,
                        evidence_refs=(),
                        next_action=FindingNextAction.REPAIR_ARTIFACT,
                    )
                )
                continue
            if (
                payload.get("artifact_type") != artifact.artifact_type.value
                or payload.get("artifact_id") != artifact.artifact_id
                or payload.get("version") != artifact.version
                or payload.get("task_ref") != str(package.binding.task_id)
                or payload.get("run_ref") != str(package.binding.run_id)
            ):
                findings.append(
                    ReviewerFinding(
                        code=FindingCode.ARTIFACT_SCOPE_MISMATCH,
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.SCOPE_LINEAGE,
                        path=f"artifacts[{artifact_ref}].common_envelope",
                        artifact_ref=artifact_ref,
                        evidence_refs=(),
                        next_action=FindingNextAction.REPAIR_ARTIFACT,
                    )
                )
                continue
            if actual_digest != artifact.declared_digest or (
                declared_in_payload is not None and declared_in_payload != artifact.declared_digest
            ):
                findings.append(
                    ReviewerFinding(
                        code=FindingCode.ARTIFACT_DIGEST_MISMATCH,
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.ARTIFACT_INTEGRITY,
                        path=f"artifacts[{artifact_ref}].content_digest",
                        artifact_ref=artifact_ref,
                        evidence_refs=(),
                        next_action=FindingNextAction.REPAIR_ARTIFACT,
                    )
                )
        return tuple(findings)

    @classmethod
    def _review_single_variable(cls, package: NextGateReviewPackage) -> tuple[ReviewerFinding, ...]:
        contracts = tuple(
            artifact
            for artifact in package.artifacts
            if artifact.artifact_type is ArtifactType.REPLICATION_CONTRACT
        )
        if len(contracts) != 1:
            return (
                ReviewerFinding(
                    code=(
                        FindingCode.REPLICATION_CONTRACT_MISSING
                        if not contracts
                        else FindingCode.REPLICATION_CONTRACT_AMBIGUOUS
                    ),
                    severity=FindingSeverity.BLOCKING,
                    category=FindingCategory.SCOPE_LINEAGE,
                    path="artifacts",
                    artifact_ref=None,
                    evidence_refs=(),
                    next_action=FindingNextAction.REPAIR_ARTIFACT,
                ),
            )
        contract = contracts[0]
        try:
            payload = json.loads(contract.canonical_payload_json)
            if not isinstance(payload, dict):
                raise TypeError("contract payload must be an object")
            selected = CreativeDimension(payload["selected_component"])
            frozen = {CreativeDimension(component) for component in payload["frozen_components"]}
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return (
                ReviewerFinding(
                    code=FindingCode.CONTRACT_REVIEW_FIELDS_INVALID,
                    severity=FindingSeverity.BLOCKING,
                    category=FindingCategory.SINGLE_VARIABLE_ISOLATION,
                    path="artifacts[replication_contract].review_fields",
                    artifact_ref=(
                        f"{contract.artifact_type.value}:{contract.artifact_id}:{contract.version}"
                    ),
                    evidence_refs=(),
                    next_action=FindingNextAction.REPAIR_ARTIFACT,
                ),
            )

        expected_components = frozen | {selected}
        control_values = cls._mechanism_values(package.control)
        variant_values = cls._mechanism_values(package.variant)
        if (
            control_values is None
            or variant_values is None
            or set(control_values) != expected_components
            or set(variant_values) != expected_components
        ):
            return (
                ReviewerFinding(
                    code=FindingCode.COMPARISON_COVERAGE_MISMATCH,
                    severity=FindingSeverity.BLOCKING,
                    category=FindingCategory.SINGLE_VARIABLE_ISOLATION,
                    path="comparison.mechanism_values",
                    artifact_ref=None,
                    evidence_refs=(),
                    next_action=FindingNextAction.RESTORE_SINGLE_VARIABLE,
                ),
            )

        changed_components = tuple(
            component
            for component in sorted(expected_components, key=lambda item: item.value)
            if control_values[component] != variant_values[component]
        )
        context_changes = tuple(
            name
            for name in _FROZEN_CONTEXT_FIELDS
            if getattr(package.control.frozen_context, name)
            != getattr(package.variant.frozen_context, name)
        )
        change_count = len(changed_components) + len(context_changes)
        findings: list[ReviewerFinding] = []
        if change_count == 0:
            findings.append(_single_variable_finding(FindingCode.ISOLATION_EVIDENCE_MISSING))
        elif change_count > 1:
            findings.append(_single_variable_finding(FindingCode.MULTIPLE_CHANGED_DIMENSIONS))
        if change_count != 1 or changed_components != (selected,):
            findings.append(_single_variable_finding(FindingCode.DECLARED_DIMENSION_MISMATCH))
        findings.extend(
            _single_variable_finding(
                FindingCode.FROZEN_FIELD_CHANGED,
                path=f"comparison.frozen_context.{name}",
            )
            for name in context_changes
        )
        return tuple(findings)

    @staticmethod
    def _mechanism_values(
        candidate: CandidateSnapshot,
    ) -> dict[CreativeDimension, str] | None:
        values = {item.component: item.value_digest for item in candidate.mechanism_values}
        if len(values) != len(candidate.mechanism_values):
            return None
        return values

    @classmethod
    def _review_claims(cls, package: NextGateReviewPackage) -> tuple[ReviewerFinding, ...]:
        contracts = tuple(
            artifact
            for artifact in package.artifacts
            if artifact.artifact_type is ArtifactType.REPLICATION_CONTRACT
        )
        if len(contracts) != 1:
            return ()
        try:
            payload = json.loads(contracts[0].canonical_payload_json)
            if not isinstance(payload, dict):
                return ()
            selected = frozenset(str(item) for item in payload["selected_fact_ids"])
            excluded = frozenset(str(item) for item in payload["excluded_fact_ids"])
            subject_binding = payload.get("subject_binding")
            product_snapshot_id = (
                subject_binding.get("product_snapshot_id")
                if isinstance(subject_binding, dict)
                else None
            )
            if not isinstance(product_snapshot_id, str) or not product_snapshot_id:
                product_snapshot_id = None
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return ()

        findings: list[ReviewerFinding] = []
        evidence_groups = _group_evidence(package.evidence)
        evidence_by_ref = {
            ref: values[0] for ref, values in evidence_groups.items() if len(values) == 1
        }
        for candidate_name, candidate in (
            ("control", package.control),
            ("variant", package.variant),
        ):
            for claim in sorted(
                candidate.visible_claims,
                key=lambda item: (item.claim_id, item.surface.value),
            ):
                path = f"{candidate_name}.visible_claims[{claim.claim_id}].{claim.surface.value}"
                if claim.fact_id is not None and claim.fact_id in excluded:
                    findings.append(
                        _claim_finding(
                            FindingCode.EXCLUDED_FACT_RESURRECTION,
                            path=path,
                            evidence_refs=claim.evidence_refs,
                        )
                    )
                unsupported = (
                    claim.kind is ClaimKind.PRODUCT
                    and (
                        claim.fact_id is None
                        or claim.fact_id not in selected
                        or claim.fact_state not in {FactStatus.CONFIRMED, FactStatus.LOCKED}
                        or not claim.evidence_refs
                    )
                ) or (
                    claim.kind is ClaimKind.NON_PRODUCT
                    and (claim.fact_id is not None or claim.fact_state is not None)
                )
                if unsupported:
                    findings.append(
                        _claim_finding(
                            FindingCode.UNSUPPORTED_CLAIM,
                            path=path,
                            evidence_refs=claim.evidence_refs,
                        )
                    )
                if claim.kind is ClaimKind.PRODUCT and claim.evidence_refs:
                    missing_refs = tuple(
                        sorted(
                            ref for ref in set(claim.evidence_refs) if ref not in evidence_groups
                        )
                    )
                    if missing_refs:
                        findings.append(
                            _claim_evidence_finding(
                                FindingCode.EVIDENCE_REF_MISSING,
                                path=f"{path.rsplit('.', maxsplit=1)[0]}.evidence_refs",
                                evidence_refs=missing_refs,
                            )
                        )
                    invalid_refs = tuple(
                        sorted(
                            ref
                            for ref in set(claim.evidence_refs)
                            if ref in evidence_by_ref
                            and (
                                evidence_by_ref[ref].plane is not EvidencePlane.PRODUCT_TRUTH
                                or evidence_by_ref[ref].state is not EvidenceState.OBSERVED
                                or evidence_by_ref[ref].level is not EvidenceLevel.FACT
                                or evidence_by_ref[ref].fact_id != claim.fact_id
                                or evidence_by_ref[ref].fact_state
                                not in {FactStatus.CONFIRMED, FactStatus.LOCKED}
                                or product_snapshot_id is None
                                or evidence_by_ref[ref].product_snapshot_id != product_snapshot_id
                            )
                        )
                    )
                    if invalid_refs:
                        findings.append(
                            _claim_evidence_finding(
                                FindingCode.EVIDENCE_BOUNDARY_EXCEEDED,
                                path=f"{path.rsplit('.', maxsplit=1)[0]}.evidence_refs",
                                evidence_refs=invalid_refs,
                            )
                        )
        return tuple(findings)

    @staticmethod
    def _review_evidence(
        evidence: tuple[EvidenceSnapshot, ...],
    ) -> tuple[ReviewerFinding, ...]:
        findings: list[ReviewerFinding] = []
        for evidence_ref, values in _group_evidence(evidence).items():
            if len(values) > 1:
                findings.append(
                    ReviewerFinding(
                        code=FindingCode.EVIDENCE_CONFLICT,
                        severity=FindingSeverity.BLOCKING,
                        category=FindingCategory.EVIDENCE_BOUNDARY,
                        path=f"evidence[{evidence_ref}]",
                        artifact_ref=None,
                        evidence_refs=(evidence_ref,),
                        next_action=FindingNextAction.PROVIDE_EVIDENCE,
                    )
                )
            for item in values:
                acceptable = (
                    item.state is EvidenceState.OBSERVED and item.level is EvidenceLevel.FACT
                )
                if acceptable:
                    continue
                blocking = item.required_for_next_gate
                findings.append(
                    ReviewerFinding(
                        code=(
                            FindingCode.EVIDENCE_BOUNDARY_EXCEEDED
                            if blocking
                            else FindingCode.EVIDENCE_LIMITED
                        ),
                        severity=(
                            FindingSeverity.BLOCKING if blocking else FindingSeverity.LIMITATION
                        ),
                        category=FindingCategory.EVIDENCE_BOUNDARY,
                        path=f"evidence[{item.evidence_ref}]",
                        artifact_ref=None,
                        evidence_refs=(item.evidence_ref,),
                        next_action=FindingNextAction.PROVIDE_EVIDENCE,
                    )
                )
        return tuple(findings)


def _canonical_artifact_digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        _canonical_artifact_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _canonical_artifact_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("artifact number must be finite")
        return 0 if value == 0 else value
    if isinstance(value, dict):
        return {str(key): _canonical_artifact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonical_artifact_value(item) for item in value]
    raise TypeError("artifact payload must contain JSON values only")


_FROZEN_CONTEXT_FIELDS = (
    "configuration_digest",
    "fact_binding_digest",
    "subject_binding_digest",
    "material_scope_digest",
    "claim_contract_digest",
)


def _single_variable_finding(
    code: FindingCode, *, path: str = "comparison.actual_changes"
) -> ReviewerFinding:
    return ReviewerFinding(
        code=code,
        severity=FindingSeverity.BLOCKING,
        category=FindingCategory.SINGLE_VARIABLE_ISOLATION,
        path=path,
        artifact_ref=None,
        evidence_refs=(),
        next_action=FindingNextAction.RESTORE_SINGLE_VARIABLE,
    )


def _claim_finding(
    code: FindingCode, *, path: str, evidence_refs: tuple[str, ...]
) -> ReviewerFinding:
    return ReviewerFinding(
        code=code,
        severity=FindingSeverity.BLOCKING,
        category=FindingCategory.DENY_SET,
        path=path,
        artifact_ref=None,
        evidence_refs=tuple(sorted(set(evidence_refs))),
        next_action=FindingNextAction.REMOVE_OR_BIND_CLAIM,
    )


def _claim_evidence_finding(
    code: FindingCode, *, path: str, evidence_refs: tuple[str, ...]
) -> ReviewerFinding:
    return ReviewerFinding(
        code=code,
        severity=FindingSeverity.BLOCKING,
        category=FindingCategory.EVIDENCE_BOUNDARY,
        path=path,
        artifact_ref=None,
        evidence_refs=evidence_refs,
        next_action=FindingNextAction.PROVIDE_EVIDENCE,
    )


def _outcome(findings: list[ReviewerFinding]) -> ReviewerOutcome:
    ordered = tuple(
        sorted(
            set(findings),
            key=lambda item: (
                item.severity.value,
                item.category.value,
                item.path,
                item.code.value,
                item.artifact_ref or "",
                item.evidence_refs,
            ),
        )
    )
    if any(item.severity is FindingSeverity.BLOCKING for item in ordered):
        disposition = ReviewDisposition.BLOCKED
    elif ordered:
        disposition = ReviewDisposition.PROCEED_WITH_LIMITS
    else:
        disposition = ReviewDisposition.READY_FOR_NEXT_GATE
    return ReviewerOutcome(disposition=disposition, findings=ordered)


def _group_evidence(
    evidence: tuple[EvidenceSnapshot, ...],
) -> dict[str, tuple[EvidenceSnapshot, ...]]:
    grouped: dict[str, set[EvidenceSnapshot]] = {}
    for item in evidence:
        grouped.setdefault(item.evidence_ref, set()).add(item)
    return {
        evidence_ref: tuple(
            sorted(
                values,
                key=lambda item: (
                    item.plane.value,
                    item.state.value,
                    item.level.value,
                    item.required_for_next_gate,
                ),
            )
        )
        for evidence_ref, values in sorted(grouped.items())
    }
