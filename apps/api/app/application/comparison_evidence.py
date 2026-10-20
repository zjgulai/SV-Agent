"""Typed, side-effect-free comparison-evidence contracts for the D1 seam."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationInfo, model_validator

from app.domain.common.canonical import canonical_digest

EvidenceContext = Literal["performance", "experiment", "asset"]
EvidenceSectionState = Literal[
    "available",
    "partial",
    "unavailable",
    "out_of_scope",
    "quarantined",
    "restricted",
]
MeasurementState = Literal[
    "observed",
    "missing",
    "unknown",
    "not_reported",
    "not_collected",
    "source_ambiguous",
    "not_applicable",
    "redacted",
]
SubjectRelation = Literal[
    "exact_snapshot",
    "reviewed_snapshot_selection",
    "reviewed_family_context",
    "unresolved",
    "conflict",
]

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
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


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UnobservedText(_FrozenModel):
    state: Literal[
        "missing",
        "unknown",
        "not_reported",
        "not_collected",
        "source_ambiguous",
        "not_applicable",
        "redacted",
    ]
    value: None = None


class SourcePresentation(_FrozenModel):
    surface: Literal["getter_payload", "page_ui"]
    display: str = Field(min_length=1, max_length=256)


class PerformanceObservation(_FrozenModel):
    observation_ref: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    platform: Literal["all", "instagram", "tiktok", "youtube"]
    metric: Literal[
        "published_videos",
        "views",
        "likes",
        "comments",
        "shares",
        "accounts",
        "followers",
        "engagement_rate",
    ]
    state: MeasurementState
    value: Decimal | None
    unit: Literal["count", "ratio"]
    source_display: str | None = Field(default=None, max_length=256)
    source_presentations: tuple[SourcePresentation, ...] = ()
    precision: Literal["exact_payload", "rounded_ui", "unresolved"]
    disposition: Literal["cite", "recompute", "test", "reject"]

    @model_validator(mode="after")
    def validate_measurement(self) -> "PerformanceObservation":
        if self.state == "observed" and self.value is None:
            raise ValueError("observed metrics require a value")
        if self.state != "observed" and self.value is not None:
            raise ValueError("non-observed metrics must not carry a value")
        if self.state == "source_ambiguous" and (
            len(self.source_presentations) < 2
            or len({item.display for item in self.source_presentations}) < 2
        ):
            raise ValueError("source_ambiguous metrics require conflicting presentations")
        if self.state != "source_ambiguous" and self.source_presentations:
            raise ValueError("only source_ambiguous metrics may carry presentations")
        if self.state == "observed" and self.precision == "unresolved":
            raise ValueError("observed metrics require a resolved precision")
        if self.state != "observed" and self.precision != "unresolved":
            raise ValueError("non-observed metrics require unresolved precision")
        return self


class PerformanceSubject(_FrozenModel):
    brand_workspace: Literal["momcozy"]
    market: str = Field(pattern=r"^[A-Z]{2}$")
    product_family: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    model: UnobservedText
    variant: UnobservedText
    source_subject_label: str = Field(min_length=1, max_length=256)


class PerformanceWindow(_FrozenModel):
    start: date
    end: date
    timezone: UnobservedText

    @model_validator(mode="after")
    def validate_window(self) -> "PerformanceWindow":
        if self.end < self.start:
            raise ValueError("performance window end must not precede start")
        return self


class PerformanceSource(_FrozenModel):
    locator: HttpUrl
    captured_on: date
    captured_at: UnobservedText
    snapshot_state: Literal["observed", "not_reported", "unknown"]
    collection_method: UnobservedText
    deduplication_method: UnobservedText
    paid_organic_split: UnobservedText
    ranking_formula: UnobservedText

    @model_validator(mode="after")
    def validate_locator(self) -> "PerformanceSource":
        if self.locator.query or self.locator.fragment:
            raise ValueError("source locator must not include query or fragment")
        return self


class PerformanceReview(_FrozenModel):
    review_state: Literal["reviewed_with_limitations"]
    review_scope: Literal["technical_and_claim_safety"]
    review_policy_version: Literal["performance-review.v1"]
    reviewed_at: datetime


class CreativeSignal(_FrozenModel):
    signal_ref: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,127}$")
    role: Literal["hypothesis_only"]
    disposition: Literal["cite", "recompute", "test", "reject"]


class ReportedProductClaim(_FrozenModel):
    claim_ref: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,127}$")
    role: Literal["fact_gate_required"]
    fact_gate: Literal["required"]
    disposition: Literal["cite", "recompute", "test", "reject"]


class ReviewedPerformancePackage(_FrozenModel):
    schema_version: Literal["reviewed-performance-package.v1"]
    package_ref: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,127}$")
    evidence_context: Literal["content_performance"]
    visibility: Literal["public_reviewed"]
    subject: PerformanceSubject
    window: PerformanceWindow
    source: PerformanceSource
    review: PerformanceReview
    observations: tuple[PerformanceObservation, ...] = Field(min_length=1, max_length=64)
    creative_signals: tuple[CreativeSignal, ...] = Field(max_length=32)
    reported_product_claims: tuple[ReportedProductClaim, ...] = Field(max_length=32)
    limitations: tuple[str, ...] = Field(min_length=1, max_length=32)
    package_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_package(self, info: ValidationInfo) -> "ReviewedPerformancePackage":
        _assert_safe_value(self.package_body())
        if len({item.observation_ref for item in self.observations}) != len(self.observations):
            raise ValueError("observation_ref values must be unique")
        if not (info.context or {}).get("skip_digest") and (
            canonical_digest(self.package_body()) != self.package_digest
        ):
            raise ValueError("package_digest does not match canonical package body")
        return self

    def package_body(self) -> dict[str, Any]:
        body = self.model_dump(mode="json")
        del body["package_digest"]
        return body

    def scope_digest(self) -> str:
        return canonical_digest(
            {
                "subject": self.subject.model_dump(mode="json"),
                "window": self.window.model_dump(mode="json"),
            }
        )


def build_reviewed_performance_package(payload: dict[str, object]) -> ReviewedPerformancePackage:
    """Build a validated package and bind its digest without any I/O."""
    body = dict(payload)
    body.pop("package_digest", None)
    body["package_digest"] = "0" * 64
    normalized = ReviewedPerformancePackage.model_validate(body, context={"skip_digest": True})
    body = normalized.package_body()
    body["package_digest"] = canonical_digest(body)
    return ReviewedPerformancePackage.model_validate(body)


class PerformanceEvidenceSection(_FrozenModel):
    state: EvidenceSectionState
    public_code: Literal[
        "PERFORMANCE_EVIDENCE_AVAILABLE",
        "PERFORMANCE_EVIDENCE_PARTIAL",
        "PERFORMANCE_EVIDENCE_UNAVAILABLE",
        "PERFORMANCE_EVIDENCE_OUT_OF_SCOPE",
        "PERFORMANCE_EVIDENCE_QUARANTINED",
        "PERFORMANCE_EVIDENCE_RESTRICTED",
    ]
    subject_relation: SubjectRelation | None = None
    package: ReviewedPerformancePackage | None = None
    limitation_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_section(self) -> "PerformanceEvidenceSection":
        package_required = self.state in {"available", "partial"}
        if package_required != (self.package is not None):
            raise ValueError("available or partial performance requires exactly one package")
        if self.state in {"available", "partial"} and self.subject_relation is None:
            raise ValueError("available or partial performance requires subject relation")
        if self.state not in {"available", "partial"} and self.subject_relation is not None:
            raise ValueError("unavailable performance must not expose subject relation")
        return self


class EvidenceSection(_FrozenModel):
    state: Literal["unavailable"]
    public_code: Literal["EXPERIMENT_EVIDENCE_UNAVAILABLE", "ASSET_EVIDENCE_UNAVAILABLE"]


class ComparisonEvidenceSet(_FrozenModel):
    performance: PerformanceEvidenceSection
    experiment: EvidenceSection
    asset: EvidenceSection


@dataclass(frozen=True, slots=True)
class ComparisonEvidenceSubject:
    product_snapshot_id: UUID
    product_snapshot_canonical_digest: str
    evidence_context: EvidenceContext

    def __post_init__(self) -> None:
        if not _DIGEST.fullmatch(self.product_snapshot_canonical_digest):
            raise ValueError("product snapshot canonical digest must be a sha256 hex digest")


class ComparisonEvidenceReader(Protocol):
    async def read(self, subject: ComparisonEvidenceSubject) -> ComparisonEvidenceSet: ...


def _unavailable_set() -> ComparisonEvidenceSet:
    return ComparisonEvidenceSet(
        performance=PerformanceEvidenceSection(
            state="unavailable",
            public_code="PERFORMANCE_EVIDENCE_UNAVAILABLE",
        ),
        experiment=EvidenceSection(
            state="unavailable", public_code="EXPERIMENT_EVIDENCE_UNAVAILABLE"
        ),
        asset=EvidenceSection(state="unavailable", public_code="ASSET_EVIDENCE_UNAVAILABLE"),
    )


@dataclass(frozen=True, slots=True)
class UnavailableComparisonEvidenceReader:
    async def read(self, subject: ComparisonEvidenceSubject) -> ComparisonEvidenceSet:
        return _unavailable_set()


@dataclass(frozen=True, slots=True)
class InMemoryComparisonEvidenceReader:
    performance_by_subject: dict[ComparisonEvidenceSubject, PerformanceEvidenceSection]

    async def read(self, subject: ComparisonEvidenceSubject) -> ComparisonEvidenceSet:
        performance = self.performance_by_subject.get(subject)
        if performance is None:
            return _unavailable_set()
        return ComparisonEvidenceSet(
            performance=performance,
            experiment=EvidenceSection(
                state="unavailable", public_code="EXPERIMENT_EVIDENCE_UNAVAILABLE"
            ),
            asset=EvidenceSection(state="unavailable", public_code="ASSET_EVIDENCE_UNAVAILABLE"),
        )


def _assert_safe_value(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _assert_safe_value(item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_safe_value(item)
        return
    if not isinstance(value, str):
        return
    lowered = value.casefold()
    if _ABSOLUTE_PATH.search(value) or "cookie:" in lowered or "set-cookie:" in lowered:
        raise ValueError("package contains an unsafe value")
    for raw_url in _URL.findall(value):
        query_keys = {key.casefold() for key, _ in parse_qsl(urlsplit(raw_url).query)}
        if query_keys.intersection(_SENSITIVE_QUERY_KEYS) or any(
            key.startswith("x-amz-") for key in query_keys
        ):
            raise ValueError("package contains an unsafe value")
