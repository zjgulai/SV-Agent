from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.application.comparison_evidence import (
    ComparisonEvidenceSubject,
    InMemoryComparisonEvidenceReader,
    PerformanceEvidenceSection,
    UnavailableComparisonEvidenceReader,
    build_reviewed_performance_package,
)
from tests.fixtures.comparison_evidence import reviewed_performance_package_payload


def test_reviewed_package_preserves_observed_zero_and_source_ambiguity() -> None:
    package = build_reviewed_performance_package(reviewed_performance_package_payload())

    assert package.observations[0].value == Decimal(10312)
    assert package.observations[0].source_display == "10.3K"
    assert package.observations[1].state == "source_ambiguous"
    assert package.observations[1].value is None
    assert (
        package.package_digest == "dab8a93117b0d64807afdc158e63543cfa896417088ba348133c0a207e6968ee"
    )


def test_reviewed_package_rejects_a_non_observed_metric_value() -> None:
    payload = reviewed_performance_package_payload()
    observations = payload["observations"]
    assert isinstance(observations, list)
    observations[1]["value"] = Decimal(0)

    with pytest.raises(ValidationError, match="non-observed"):
        build_reviewed_performance_package(payload)


def test_reviewed_package_requires_conflicting_source_ambiguity_presentations() -> None:
    payload = reviewed_performance_package_payload()
    observations = payload["observations"]
    assert isinstance(observations, list)
    observations[1]["source_presentations"][1]["display"] = "0"

    with pytest.raises(ValidationError, match="conflicting"):
        build_reviewed_performance_package(payload)


def test_reviewed_package_rejects_a_digest_that_does_not_match_its_body() -> None:
    package = build_reviewed_performance_package(reviewed_performance_package_payload())
    raw = package.model_dump(mode="json")
    raw["package_digest"] = "0" * 64

    with pytest.raises(ValidationError, match="package_digest"):
        type(package).model_validate(raw)


def test_reviewed_package_rejects_a_sensitive_source_locator() -> None:
    payload = reviewed_performance_package_payload()
    payload["source"]["locator"] = "https://example.test/report?token=secret"

    with pytest.raises(ValidationError, match="query"):
        build_reviewed_performance_package(payload)


def test_reviewed_package_rejects_an_absolute_path_in_a_visible_value() -> None:
    payload = reviewed_performance_package_payload()
    payload["subject"]["source_subject_label"] = "/private/raw-report"

    with pytest.raises(ValidationError, match="unsafe"):
        build_reviewed_performance_package(payload)


@pytest.mark.asyncio
async def test_unavailable_reader_returns_only_honest_unavailable_sections() -> None:
    subject = ComparisonEvidenceSubject(
        product_snapshot_id=uuid4(),
        product_snapshot_canonical_digest="a" * 64,
        evidence_context="performance",
    )

    evidence = await UnavailableComparisonEvidenceReader().read(subject)

    assert evidence.performance.state == "unavailable"
    assert evidence.performance.public_code == "PERFORMANCE_EVIDENCE_UNAVAILABLE"
    assert evidence.performance.package is None
    assert evidence.experiment.state == "unavailable"
    assert evidence.asset.state == "unavailable"


@pytest.mark.asyncio
async def test_in_memory_reader_returns_only_the_exact_subject_fixture() -> None:
    subject = ComparisonEvidenceSubject(
        product_snapshot_id=uuid4(),
        product_snapshot_canonical_digest="b" * 64,
        evidence_context="performance",
    )
    package = build_reviewed_performance_package(reviewed_performance_package_payload())
    available = PerformanceEvidenceSection(
        state="partial",
        public_code="PERFORMANCE_EVIDENCE_PARTIAL",
        subject_relation="reviewed_snapshot_selection",
        package=package,
        limitation_codes=package.limitations,
    )
    reader = InMemoryComparisonEvidenceReader({subject: available})

    found = await reader.read(subject)
    missing = await reader.read(
        ComparisonEvidenceSubject(
            product_snapshot_id=subject.product_snapshot_id,
            product_snapshot_canonical_digest="c" * 64,
            evidence_context="performance",
        )
    )

    assert found.performance.state == "partial"
    assert found.performance.package is not None
    assert missing.performance.state == "unavailable"
