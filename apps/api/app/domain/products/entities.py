from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.domain.common.canonical import canonical_digest
from app.domain.products.errors import LockedFactError


class FactStatus(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    LOCKED = "locked"


class SourceType(StrEnum):
    MANUAL = "manual"
    SCHEMA_ORG_URL = "schema_org_url"


class ParseStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProductSource:
    id: UUID
    source_type: SourceType
    source_url: str | None
    retrieved_at: datetime
    content_digest: str
    raw_payload: dict[str, Any]
    parse_status: ParseStatus
    error_code: str | None = None

    @classmethod
    def create(
        cls,
        *,
        source_type: SourceType,
        raw_payload: dict[str, Any],
        source_url: str | None = None,
        id: UUID | None = None,
        retrieved_at: datetime | None = None,
        parse_status: ParseStatus = ParseStatus.SUCCEEDED,
        error_code: str | None = None,
    ) -> "ProductSource":
        return cls(
            id=id or uuid4(),
            source_type=source_type,
            source_url=source_url,
            retrieved_at=retrieved_at or datetime.now(UTC),
            content_digest=canonical_digest(raw_payload),
            raw_payload=raw_payload,
            parse_status=parse_status,
            error_code=error_code,
        )


@dataclass(frozen=True, slots=True)
class ProductSnapshot:
    id: UUID
    source_id: UUID
    title: str
    description: str | None
    category_path: tuple[str, ...]
    images: tuple[str, ...]
    price_amount: Decimal | None
    price_currency: str | None
    canonical_digest: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        source_id: UUID,
        title: str,
        description: str | None = None,
        category_path: tuple[str, ...] = (),
        images: tuple[str, ...] = (),
        price_amount: Decimal | None = None,
        price_currency: str | None = None,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> "ProductSnapshot":
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("title must not be blank")

        normalized_description = description.strip() if description is not None else None
        normalized_categories = tuple(item.strip() for item in category_path)
        normalized_images = tuple(item.strip() for item in images)
        normalized_currency = price_currency.strip().upper() if price_currency is not None else None
        digest = canonical_digest(
            {
                "title": normalized_title,
                "description": normalized_description,
                "category_path": normalized_categories,
                "images": normalized_images,
                "price_amount": price_amount,
                "price_currency": normalized_currency,
            }
        )
        return cls(
            id=id or uuid4(),
            source_id=source_id,
            title=normalized_title,
            description=normalized_description,
            category_path=normalized_categories,
            images=normalized_images,
            price_amount=price_amount,
            price_currency=normalized_currency,
            canonical_digest=digest,
            created_at=created_at or datetime.now(UTC),
        )


@dataclass(frozen=True, slots=True)
class ProductFact:
    id: UUID
    snapshot_id: UUID
    claim_type: str
    claim: str
    value: dict[str, Any]
    evidence_kind: str
    evidence_locator: str
    evidence_excerpt: str
    confidence: Decimal
    status: FactStatus
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        snapshot_id: UUID,
        claim_type: str,
        claim: str,
        value: dict[str, Any],
        evidence_kind: str,
        evidence_locator: str,
        evidence_excerpt: str,
        confidence: Decimal | float | str,
        id: UUID | None = None,
        status: FactStatus = FactStatus.PROPOSED,
        updated_at: datetime | None = None,
    ) -> "ProductFact":
        normalized_confidence = Decimal(str(confidence))
        if not Decimal(0) <= normalized_confidence <= Decimal(1):
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            id=id or uuid4(),
            snapshot_id=snapshot_id,
            claim_type=claim_type.strip(),
            claim=claim.strip(),
            value=value,
            evidence_kind=evidence_kind.strip(),
            evidence_locator=evidence_locator.strip(),
            evidence_excerpt=evidence_excerpt.strip(),
            confidence=normalized_confidence,
            status=status,
            updated_at=updated_at or datetime.now(UTC),
        )

    def transition_to(self, status: FactStatus) -> "ProductFact":
        if status == self.status:
            return self
        if self.status is FactStatus.LOCKED:
            raise LockedFactError("locked facts must be replaced with a new fact")
        return replace(self, status=status, updated_at=datetime.now(UTC))
