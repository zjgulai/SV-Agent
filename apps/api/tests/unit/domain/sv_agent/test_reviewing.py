from __future__ import annotations

from dataclasses import fields, replace
from uuid import UUID

from app.domain.products.entities import FactStatus
from app.domain.sv_agent.entities import CreativeDimension
from app.domain.sv_agent.reviewing import (
    CandidateSnapshot,
    CanonicalArtifactSnapshot,
    ClaimKind,
    ClaimSurface,
    EvidencePlane,
    EvidenceSnapshot,
    EvidenceState,
    FindingCategory,
    FindingCode,
    FindingNextAction,
    FindingSeverity,
    FrozenContextSnapshot,
    IndependentReviewer,
    MechanismValue,
    NextGateReviewPackage,
    ReviewDisposition,
    TaskRunBinding,
    VisibleClaimSnapshot,
)
from app.domain.sv_agent.runtime_records import ArtifactType, EvidenceLevel

TASK_ID = UUID("00000000-0000-0000-0000-000000000101")
RUN_ID = UUID("00000000-0000-0000-0000-000000000201")
CONTRACT_DIGEST = "660b93d98f42477f5cd2794362197860e0d497dffa0db1c710360687a3e4b423"
CONTRACT_PAYLOAD = (
    '{"artifact_id":"contract-001","artifact_type":"replication_contract",'
    '"excluded_fact_ids":["fact-002"],'
    '"frozen_components":["reveal_cadence","caption_cadence",'
    '"visual_contrast","sonic_timing"],'
    '"run_ref":"00000000-0000-0000-0000-000000000201",'
    '"selected_component":"hook_trigger","selected_fact_ids":["fact-001"],'
    '"subject_binding":{"product_snapshot_id":"snapshot-001"},'
    '"task_ref":"00000000-0000-0000-0000-000000000101","version":1}'
)


def _binding() -> TaskRunBinding:
    return TaskRunBinding(
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=2,
    )


def _artifact() -> CanonicalArtifactSnapshot:
    return CanonicalArtifactSnapshot(
        artifact_type=ArtifactType.REPLICATION_CONTRACT,
        artifact_id="contract-001",
        version=1,
        binding=_binding(),
        declared_digest=CONTRACT_DIGEST,
        canonical_payload_json=CONTRACT_PAYLOAD,
    )


def _mechanism_values(
    *, hook_digest: str, reveal_digest: str = "2" * 64
) -> tuple[MechanismValue, ...]:
    return (
        MechanismValue(CreativeDimension.HOOK_TRIGGER, hook_digest),
        MechanismValue(CreativeDimension.REVEAL_CADENCE, reveal_digest),
        MechanismValue(CreativeDimension.CAPTION_CADENCE, "3" * 64),
        MechanismValue(CreativeDimension.VISUAL_CONTRAST, "4" * 64),
        MechanismValue(CreativeDimension.SONIC_TIMING, "5" * 64),
    )


def _frozen_context() -> FrozenContextSnapshot:
    return FrozenContextSnapshot(
        configuration_digest="6" * 64,
        fact_binding_digest="7" * 64,
        subject_binding_digest="8" * 64,
        material_scope_digest="9" * 64,
        claim_contract_digest="a" * 64,
    )


def _claims() -> tuple[VisibleClaimSnapshot, ...]:
    return (
        VisibleClaimSnapshot(
            claim_id="claim-001",
            surface=ClaimSurface.VOICEOVER,
            kind=ClaimKind.PRODUCT,
            fact_id="fact-001",
            fact_state=FactStatus.CONFIRMED,
            evidence_refs=("fact-evidence-001",),
        ),
    )


def _candidate(*, hook_digest: str, reveal_digest: str = "2" * 64) -> CandidateSnapshot:
    return CandidateSnapshot(
        mechanism_values=_mechanism_values(
            hook_digest=hook_digest,
            reveal_digest=reveal_digest,
        ),
        frozen_context=_frozen_context(),
        visible_claims=_claims(),
    )


def _package() -> NextGateReviewPackage:
    return NextGateReviewPackage(
        binding=_binding(),
        artifacts=(_artifact(),),
        control=_candidate(hook_digest="0" * 64),
        variant=_candidate(hook_digest="1" * 64),
        evidence=(
            EvidenceSnapshot(
                evidence_ref="fact-evidence-001",
                plane=EvidencePlane.PRODUCT_TRUTH,
                state=EvidenceState.OBSERVED,
                level=EvidenceLevel.FACT,
                required_for_next_gate=True,
                product_snapshot_id="snapshot-001",
                fact_id="fact-001",
                fact_state=FactStatus.CONFIRMED,
            ),
        ),
    )


def test_consistent_single_variable_package_is_ready_and_repeatable() -> None:
    request = _package()

    first = IndependentReviewer.review(request)
    second = IndependentReviewer.review(request)

    assert first.disposition is ReviewDisposition.READY_FOR_NEXT_GATE
    assert first.findings == ()
    assert second == first


def test_tampered_artifact_payload_is_blocked_by_recomputed_digest() -> None:
    tampered = replace(
        _artifact(),
        canonical_payload_json=CONTRACT_PAYLOAD.replace(
            '"selected_component":"hook_trigger"',
            '"selected_component":"reveal_cadence"',
        ),
    )
    request = replace(_package(), artifacts=(tampered,))

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.BLOCKED
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code is FindingCode.ARTIFACT_DIGEST_MISMATCH
    assert finding.severity is FindingSeverity.BLOCKING
    assert finding.category is FindingCategory.ARTIFACT_INTEGRITY
    assert finding.path == "artifacts[replication_contract:contract-001:1].content_digest"
    assert finding.artifact_ref == "replication_contract:contract-001:1"
    assert finding.evidence_refs == ()
    assert finding.next_action is FindingNextAction.REPAIR_ARTIFACT


def test_multiple_actual_changes_are_not_treated_as_single_variable() -> None:
    request = replace(
        _package(),
        variant=_candidate(
            hook_digest="1" * 64,
            reveal_digest="c" * 64,
        ),
    )

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.MULTIPLE_CHANGED_DIMENSIONS,
        FindingCode.DECLARED_DIMENSION_MISMATCH,
    }
    assert all(
        finding.category is FindingCategory.SINGLE_VARIABLE_ISOLATION
        and finding.severity is FindingSeverity.BLOCKING
        and finding.next_action is FindingNextAction.RESTORE_SINGLE_VARIABLE
        for finding in result.findings
    )


def test_artifact_from_another_task_scope_is_blocked_even_with_valid_digest() -> None:
    foreign_binding = replace(
        _binding(),
        task_id=UUID("00000000-0000-0000-0000-000000000999"),
    )
    foreign_artifact = replace(_artifact(), binding=foreign_binding)
    request = replace(_package(), artifacts=(foreign_artifact,))

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.BLOCKED
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code is FindingCode.ARTIFACT_SCOPE_MISMATCH
    assert finding.category is FindingCategory.SCOPE_LINEAGE
    assert finding.path == "artifacts[replication_contract:contract-001:1].binding"
    assert finding.next_action is FindingNextAction.REPAIR_ARTIFACT


def test_excluded_or_unsupported_claim_is_blocked_on_visual_surface() -> None:
    unsafe_claim = VisibleClaimSnapshot(
        claim_id="claim-unsafe",
        surface=ClaimSurface.VISUAL,
        kind=ClaimKind.PRODUCT,
        fact_id="fact-002",
        fact_state=FactStatus.PROPOSED,
        evidence_refs=(),
    )
    variant = replace(_package().variant, visible_claims=(unsafe_claim,))
    request = replace(_package(), variant=variant)

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.EXCLUDED_FACT_RESURRECTION,
        FindingCode.UNSUPPORTED_CLAIM,
    }
    assert all(
        finding.category is FindingCategory.DENY_SET
        and finding.severity is FindingSeverity.BLOCKING
        and finding.path == "variant.visible_claims[claim-unsafe].visual"
        and finding.next_action is FindingNextAction.REMOVE_OR_BIND_CLAIM
        for finding in result.findings
    )


def test_optional_not_reported_evidence_proceeds_only_with_limits() -> None:
    limited = EvidenceSnapshot(
        evidence_ref="performance-retention-001",
        plane=EvidencePlane.PERFORMANCE,
        state=EvidenceState.NOT_REPORTED,
        level=EvidenceLevel.UNKNOWN,
        required_for_next_gate=False,
    )
    request = replace(_package(), evidence=(*_package().evidence, limited))

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.PROCEED_WITH_LIMITS
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code is FindingCode.EVIDENCE_LIMITED
    assert finding.category is FindingCategory.EVIDENCE_BOUNDARY
    assert finding.severity is FindingSeverity.LIMITATION
    assert finding.path == "evidence[performance-retention-001]"
    assert finding.evidence_refs == ("performance-retention-001",)
    assert finding.next_action is FindingNextAction.PROVIDE_EVIDENCE


def test_required_inference_evidence_blocks_the_next_gate() -> None:
    inferred = replace(
        _package().evidence[0],
        level=EvidenceLevel.INFERENCE,
        required_for_next_gate=True,
    )

    result = IndependentReviewer.review(replace(_package(), evidence=(inferred,)))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.EVIDENCE_BOUNDARY_EXCEEDED,
    }
    assert all(finding.severity is FindingSeverity.BLOCKING for finding in result.findings)


def test_product_claim_with_unresolved_evidence_reference_is_blocked() -> None:
    unresolved_claim = replace(
        _claims()[0],
        evidence_refs=("missing-fact-evidence",),
    )
    variant = replace(_package().variant, visible_claims=(unresolved_claim,))
    request = replace(_package(), variant=variant)

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.BLOCKED
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code is FindingCode.EVIDENCE_REF_MISSING
    assert finding.category is FindingCategory.EVIDENCE_BOUNDARY
    assert finding.path == "variant.visible_claims[claim-001].evidence_refs"
    assert finding.evidence_refs == ("missing-fact-evidence",)
    assert finding.next_action is FindingNextAction.PROVIDE_EVIDENCE


def test_product_claim_rejects_product_truth_evidence_for_unrelated_fact() -> None:
    unrelated = replace(_package().evidence[0], fact_id="fact-999")

    result = IndependentReviewer.review(replace(_package(), evidence=(unrelated,)))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.EVIDENCE_BOUNDARY_EXCEEDED,
    }
    assert {finding.path for finding in result.findings} == {
        "control.visible_claims[claim-001].evidence_refs",
        "variant.visible_claims[claim-001].evidence_refs",
    }


def test_product_claim_rejects_product_truth_evidence_for_unrelated_snapshot() -> None:
    unrelated = replace(_package().evidence[0], product_snapshot_id="snapshot-999")

    result = IndependentReviewer.review(replace(_package(), evidence=(unrelated,)))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.EVIDENCE_BOUNDARY_EXCEEDED,
    }
    assert {finding.path for finding in result.findings} == {
        "control.visible_claims[claim-001].evidence_refs",
        "variant.visible_claims[claim-001].evidence_refs",
    }


def test_product_claim_rejects_unconfirmed_product_truth_evidence() -> None:
    unconfirmed = replace(_package().evidence[0], fact_state=FactStatus.PROPOSED)

    result = IndependentReviewer.review(replace(_package(), evidence=(unconfirmed,)))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.EVIDENCE_BOUNDARY_EXCEEDED,
    }
    assert {finding.path for finding in result.findings} == {
        "control.visible_claims[claim-001].evidence_refs",
        "variant.visible_claims[claim-001].evidence_refs",
    }


def test_conflicting_duplicate_artifacts_are_order_independent() -> None:
    valid = _artifact()
    tampered = replace(
        valid,
        canonical_payload_json=CONTRACT_PAYLOAD.replace(
            '"selected_component":"hook_trigger"',
            '"selected_component":"reveal_cadence"',
        ),
    )

    forward = IndependentReviewer.review(replace(_package(), artifacts=(valid, tampered)))
    reverse = IndependentReviewer.review(replace(_package(), artifacts=(tampered, valid)))

    assert forward == reverse
    assert forward.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in forward.findings} == {
        FindingCode.ARTIFACT_DUPLICATE,
        FindingCode.ARTIFACT_DIGEST_MISMATCH,
    }


def test_conflicting_evidence_snapshots_are_order_independent() -> None:
    valid = _package().evidence[0]
    ambiguous = replace(
        valid,
        state=EvidenceState.SOURCE_AMBIGUOUS,
        level=EvidenceLevel.UNKNOWN,
    )

    forward = IndependentReviewer.review(replace(_package(), evidence=(valid, ambiguous)))
    reverse = IndependentReviewer.review(replace(_package(), evidence=(ambiguous, valid)))

    assert forward == reverse
    assert forward.disposition is ReviewDisposition.BLOCKED
    assert FindingCode.EVIDENCE_CONFLICT in {finding.code for finding in forward.findings}


def test_reviewer_outcome_cannot_carry_a_human_approval_event() -> None:
    result = IndependentReviewer.review(_package())

    assert tuple(field.name for field in fields(result)) == ("disposition", "findings")
    assert "approve" not in {action.value for action in FindingNextAction}


def test_zero_actual_changes_do_not_count_as_isolation_evidence() -> None:
    request = replace(
        _package(),
        variant=_candidate(hook_digest="0" * 64),
    )

    result = IndependentReviewer.review(request)

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.ISOLATION_EVIDENCE_MISSING,
        FindingCode.DECLARED_DIMENSION_MISMATCH,
    }


def test_frozen_configuration_drift_is_a_second_changed_dimension() -> None:
    drifted_context = replace(_frozen_context(), configuration_digest="c" * 64)
    variant = replace(_package().variant, frozen_context=drifted_context)

    result = IndependentReviewer.review(replace(_package(), variant=variant))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert {finding.code for finding in result.findings} == {
        FindingCode.MULTIPLE_CHANGED_DIMENSIONS,
        FindingCode.DECLARED_DIMENSION_MISMATCH,
        FindingCode.FROZEN_FIELD_CHANGED,
    }


def test_source_ambiguous_evidence_cannot_support_a_product_claim() -> None:
    ambiguous = replace(
        _package().evidence[0],
        state=EvidenceState.SOURCE_AMBIGUOUS,
    )

    result = IndependentReviewer.review(replace(_package(), evidence=(ambiguous,)))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert all(
        finding.code is FindingCode.EVIDENCE_BOUNDARY_EXCEEDED
        and finding.category is FindingCategory.EVIDENCE_BOUNDARY
        for finding in result.findings
    )
    assert {finding.path for finding in result.findings} == {
        "control.visible_claims[claim-001].evidence_refs",
        "variant.visible_claims[claim-001].evidence_refs",
        "evidence[fact-evidence-001]",
    }


def test_non_object_artifact_payload_returns_a_typed_finding() -> None:
    malformed = replace(_artifact(), canonical_payload_json="[]")

    result = IndependentReviewer.review(replace(_package(), artifacts=(malformed,)))

    assert result.disposition is ReviewDisposition.BLOCKED
    assert tuple(finding.code for finding in result.findings) == (
        FindingCode.ARTIFACT_PAYLOAD_INVALID,
    )
