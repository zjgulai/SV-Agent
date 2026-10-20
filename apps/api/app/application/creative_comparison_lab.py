import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.application.storyboards import (
    StoryboardPreflightEvaluation,
    StoryboardPreflightService,
)
from app.application.version_diff import diff_versions
from app.domain.common.canonical import canonical_digest
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.scripts.models import (
    ScriptDraft,
    ValidationFinding,
    ValidationReport,
)


class CreativeComparisonReferenceInvalidError(Exception):
    pass


class CreativeComparisonIntegrityError(Exception):
    pass


class CreativeComparisonSubjectNotFoundError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CreativeComparisonRequest:
    script_id: UUID
    control_version_id: UUID
    variant_version_id: UUID


class ReadinessProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: Literal["blocked", "needs_evidence", "reviewable"]
    disposition: Literal["revise", "collect_evidence", "stop"]
    single_variable_status: Literal["unverified"]
    blockers: list["ComparisonFinding"]
    evidence_needs: list["ComparisonFinding"]


class ComparisonFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    context: Literal[
        "identity",
        "comparability",
        "product_truth",
        "script_validation",
        "storyboard",
        "performance",
        "experiment",
        "asset",
    ]
    path: str | None = None
    message: str


class CandidateProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    parent_version_id: UUID | None
    created_at: datetime
    draft: ScriptDraft
    stored_validation_report: ValidationReport
    live_validation_report: ValidationReport
    storyboard_readiness: Literal["ready", "blocked"]


class SemanticDifference(BaseModel):
    model_config = ConfigDict(frozen=True)

    section: Literal["script", "storyboard", "asset"]
    path: str
    change: Literal["added", "removed", "changed"]
    kind: Literal[
        "declared_dimension",
        "unexpected_change",
        "fact_binding_change",
        "unverified",
    ]
    control_present: bool
    variant_present: bool
    control: Any | None = None
    variant: Any | None = None


class ComparisonFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    availability: Literal["present", "missing"]
    claim: str | None
    status: FactStatus | None


class ProductTruthGateProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["pass", "blocked"]
    snapshot_id: UUID
    pattern_key: str
    pattern_version: str
    selected_facts: list["ComparisonFact"]
    excluded_facts: list["ComparisonFact"]


class EvidenceAvailabilityProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    availability: Literal["available", "unavailable", "quarantined"]
    source_reference: str
    limitation: str


class CreativeComparisonProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["creative-comparison-view-v1"]
    script_id: UUID
    observed_at: datetime
    readiness: ReadinessProjection
    control: CandidateProjection
    variant: CandidateProjection
    differences: list[SemanticDifference]
    product_truth_gate: ProductTruthGateProjection
    performance_evidence: EvidenceAvailabilityProjection
    experiment_evidence: EvidenceAvailabilityProjection
    asset_evidence: EvidenceAvailabilityProjection
    limitations: list[ComparisonFinding]
    projection_digest: str


@dataclass(slots=True)
class CreativeComparisonLab:
    session: AsyncSession

    async def inspect(
        self, request: CreativeComparisonRequest
    ) -> CreativeComparisonProjection:
        if request.control_version_id == request.variant_version_id:
            raise CreativeComparisonReferenceInvalidError(
                "control and variant must be different versions"
            )
        repository = ScriptRepository(self.session)
        generation = await repository.get_generation(request.script_id)
        control = await repository.get_version(request.control_version_id)
        variant = await repository.get_version(request.variant_version_id)
        if generation is None or control is None or variant is None:
            raise CreativeComparisonSubjectNotFoundError(
                "creative comparison subject is unavailable"
            )
        if (
            control.generation_id != request.script_id
            or variant.generation_id != request.script_id
        ):
            raise CreativeComparisonReferenceInvalidError(
                "control and variant must belong to the requested script"
            )

        try:
            product_facts, observed_at = await ProductRepository(
                self.session
            ).list_facts_at_observation(generation.snapshot_id)
            facts_by_id = {item.id: item for item in product_facts}
            control_draft = ScriptDraft.model_validate(control.draft, extra="forbid")
            variant_draft = ScriptDraft.model_validate(variant.draft, extra="forbid")
            evaluator = StoryboardPreflightService(self.session)
            control_evaluation = evaluator.evaluate_loaded(
                generation=generation,
                version=control,
                product_facts=facts_by_id,
                observed_at=observed_at,
                strict_draft=True,
            )
            variant_evaluation = evaluator.evaluate_loaded(
                generation=generation,
                version=variant,
                product_facts=facts_by_id,
                observed_at=observed_at,
                strict_draft=True,
            )
            selected_facts = _comparison_facts(
                generation.selected_fact_ids, facts_by_id
            )
            excluded_facts = _comparison_facts(
                generation.excluded_fact_ids, facts_by_id
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise CreativeComparisonIntegrityError(
                "creative comparison product truth is invalid"
            ) from exc

        differences = _compile_script_differences(
            control_draft.model_dump(mode="json"),
            variant_draft.model_dump(mode="json"),
        )
        product_truth_findings = _product_truth_findings(control_evaluation)
        blockers = [
            *product_truth_findings,
            *_validation_findings(
                ("control", control_evaluation),
                ("variant", variant_evaluation),
            ),
        ]
        if any(
            item.kind in {"unexpected_change", "fact_binding_change"}
            for item in differences
        ):
            blockers.append(
                ComparisonFinding(
                    code="COMPARISON_UNEXPECTED_CHANGE",
                    context="comparability",
                    message="The versions contain a change outside a verified creative dimension.",
                )
            )
        blockers = _stable_findings(blockers)
        truth_status: Literal["pass", "blocked"] = (
            "blocked" if product_truth_findings else "pass"
        )
        evidence_needs = _evidence_needs()
        readiness = ReadinessProjection(
            state="blocked" if blockers else "needs_evidence",
            disposition="revise" if blockers else "collect_evidence",
            single_variable_status="unverified",
            blockers=blockers,
            evidence_needs=evidence_needs,
        )
        control_projection = CandidateProjection(
            version_id=control.id,
            parent_version_id=control.parent_version_id,
            created_at=control.created_at,
            draft=control_draft,
            stored_validation_report=control_evaluation.stored_validation_report,
            live_validation_report=control_evaluation.live_validation_report,
            storyboard_readiness=control_evaluation.preflight.status,
        )
        variant_projection = CandidateProjection(
            version_id=variant.id,
            parent_version_id=variant.parent_version_id,
            created_at=variant.created_at,
            draft=variant_draft,
            stored_validation_report=variant_evaluation.stored_validation_report,
            live_validation_report=variant_evaluation.live_validation_report,
            storyboard_readiness=variant_evaluation.preflight.status,
        )
        product_truth_gate = ProductTruthGateProjection(
            status=truth_status,
            snapshot_id=generation.snapshot_id,
            pattern_key=generation.pattern_key,
            pattern_version=generation.pattern_version,
            selected_facts=selected_facts,
            excluded_facts=excluded_facts,
        )
        performance_evidence = EvidenceAvailabilityProjection(
            availability="unavailable",
            source_reference="docs/research/leap/public-report-evidence.md",
            limitation="No approved machine-readable performance evidence package is connected.",
        )
        experiment_evidence = EvidenceAvailabilityProjection(
            availability="unavailable",
            source_reference="docs/research/oumomo/evidence-index.md",
            limitation="No approved experiment manifest is connected to this comparison.",
        )
        asset_evidence = EvidenceAvailabilityProjection(
            availability="unavailable",
            source_reference="tools/momcozy_assets/README.md",
            limitation="No approved Asset Bundle or Commercial Approval is connected.",
        )

        digest_input = {
            "schema_version": "creative-comparison-view-v1",
            "script_id": request.script_id,
            "readiness": readiness.model_dump(mode="json"),
            "control": control_projection.model_dump(mode="json"),
            "variant": variant_projection.model_dump(mode="json"),
            "differences": [item.model_dump(mode="json") for item in differences],
            "product_truth_gate": product_truth_gate.model_dump(mode="json"),
            "performance_evidence": performance_evidence.model_dump(mode="json"),
            "experiment_evidence": experiment_evidence.model_dump(mode="json"),
            "asset_evidence": asset_evidence.model_dump(mode="json"),
            "limitations": [item.model_dump(mode="json") for item in evidence_needs],
        }
        _assert_safe_projection_value(digest_input)
        return CreativeComparisonProjection(
            schema_version="creative-comparison-view-v1",
            script_id=request.script_id,
            observed_at=observed_at,
            readiness=readiness,
            control=control_projection,
            variant=variant_projection,
            differences=differences,
            product_truth_gate=product_truth_gate,
            performance_evidence=performance_evidence,
            experiment_evidence=experiment_evidence,
            asset_evidence=asset_evidence,
            limitations=evidence_needs,
            projection_digest=canonical_digest(digest_input),
        )


def _comparison_facts(
    fact_ids: list[str], facts_by_id: dict[UUID, ProductFact]
) -> list[ComparisonFact]:
    projected: list[ComparisonFact] = []
    for raw_id in fact_ids:
        fact_id = UUID(raw_id)
        fact = facts_by_id.get(fact_id)
        projected.append(
            ComparisonFact(
                id=fact_id,
                availability="present" if fact is not None else "missing",
                claim=fact.claim if fact is not None else None,
                status=fact.status if fact is not None else None,
            )
        )
    return projected


_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/(?:Users|private|tmp|var|home)/|[A-Za-z]:[\\/])")
_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "credential",
    "key",
    "signature",
    "sig",
    "token",
    "x-amz-credential",
    "x-amz-signature",
}


def _assert_safe_projection_value(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _assert_safe_projection_value(item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_safe_projection_value(item)
        return
    if not isinstance(value, str):
        return
    lowered = value.casefold()
    if _ABSOLUTE_PATH.search(value) or "cookie:" in lowered or "set-cookie:" in lowered:
        raise CreativeComparisonIntegrityError(
            "creative comparison projection contains a sensitive value"
        )
    for raw_url in _URL.findall(value):
        query_keys = {key.casefold() for key, _ in parse_qsl(urlsplit(raw_url).query)}
        if query_keys.intersection(_SENSITIVE_QUERY_KEYS) or any(
            key.startswith("x-amz-") for key in query_keys
        ):
            raise CreativeComparisonIntegrityError(
                "creative comparison projection contains a sensitive value"
            )


def _finding(
    item: ValidationFinding, *, context: Literal["product_truth", "script_validation"], prefix: str = ""
) -> ComparisonFinding:
    return ComparisonFinding(
        code=item.rule_id,
        context=context,
        path=f"{prefix}.{item.path}" if prefix else item.path,
        message=item.message,
    )


def _product_truth_findings(
    evaluation: StoryboardPreflightEvaluation,
) -> list[ComparisonFinding]:
    return _stable_findings(
        [
            _finding(item, context="product_truth")
            for item in (
                *evaluation.fact_contract_findings,
                *evaluation.promotion_findings,
            )
        ]
    )


def _validation_findings(
    *evaluations: tuple[str, StoryboardPreflightEvaluation],
) -> list[ComparisonFinding]:
    findings: list[ComparisonFinding] = []
    for side, evaluation in evaluations:
        for report in (
            evaluation.stored_validation_report,
            evaluation.live_validation_report,
        ):
            findings.extend(
                _finding(item, context="script_validation", prefix=side)
                for item in report.blocking
            )
    return _stable_findings(findings)


def _stable_findings(findings: list[ComparisonFinding]) -> list[ComparisonFinding]:
    unique = {
        (item.context, item.path, item.code, item.message): item for item in findings
    }
    return [
        unique[key]
        for key in sorted(
            unique,
            key=lambda item: (item[0], item[1] or "", item[2], item[3]),
        )
    ]


def _evidence_needs() -> list[ComparisonFinding]:
    return [
        ComparisonFinding(
            code="COMPARISON_CONTRACT_UNAVAILABLE",
            context="comparability",
            message="Single-variable comparability is unverified without an immutable contract.",
        ),
        ComparisonFinding(
            code="PERFORMANCE_EVIDENCE_UNAVAILABLE",
            context="performance",
            message="No approved performance evidence package is connected.",
        ),
        ComparisonFinding(
            code="EXPERIMENT_EVIDENCE_UNAVAILABLE",
            context="experiment",
            message="No approved experiment evidence package is connected.",
        ),
        ComparisonFinding(
            code="ASSET_EVIDENCE_UNAVAILABLE",
            context="asset",
            message="No approved asset evidence package is connected.",
        ),
    ]


def _compile_script_differences(
    control: dict[str, Any], variant: dict[str, Any]
) -> list[SemanticDifference]:
    raw = diff_versions(control, variant)
    differences: list[SemanticDifference] = []
    for item in raw["changed"]:
        differences.append(
            SemanticDifference(
                section="script",
                path=item["path"],
                change="changed",
                kind=_difference_kind(item["path"]),
                control_present=True,
                variant_present=True,
                control=item["left"],
                variant=item["right"],
            )
        )
    for item in raw["added"]:
        differences.append(
            SemanticDifference(
                section="script",
                path=item["path"],
                change="added",
                kind=_difference_kind(item["path"]),
                control_present=False,
                variant_present=True,
                variant=item["value"],
            )
        )
    for item in raw["removed"]:
        differences.append(
            SemanticDifference(
                section="script",
                path=item["path"],
                change="removed",
                kind=_difference_kind(item["path"]),
                control_present=True,
                variant_present=False,
                control=item["value"],
            )
        )
    return sorted(differences, key=lambda item: (item.section, item.path, item.change))


def _difference_kind(
    path: str,
) -> Literal["unexpected_change", "fact_binding_change", "unverified"]:
    normalized = re.sub(r"\[\d+\]", "[]", path)
    if normalized == "snapshot_id" or normalized.startswith(
        (
            "shots[].supported_fact_ids",
            "shots[].product_claims",
            "shots[].voiceover",
            "shots[].caption",
            "shots[].promotion",
        )
    ):
        return "fact_binding_change"
    if normalized in {"target_duration_seconds", "language", "audience"} or normalized.startswith(
        (
            "titles",
            "tags",
            "shooting_list",
            "phases",
            "shots[].start_seconds",
            "shots[].end_seconds",
            "shots[].phase_key",
            "shots[].role",
            "shots[].visual",
            "shots[].action",
            "shots[].acceptance_shot",
        )
    ):
        return "unexpected_change"
    return "unverified"
