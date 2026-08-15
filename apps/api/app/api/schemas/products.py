from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.domain.products.entities import FactStatus
from app.domain.products.promotion import PromotionValue


class PriceInput(BaseModel):
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class FactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_type: str = Field(min_length=1, max_length=64)
    claim: str = Field(min_length=1, max_length=500)
    value: dict[str, Any]
    evidence_excerpt: str = Field(min_length=1, max_length=1000)


class PromotionFactInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: PromotionValue
    evidence_excerpt: str = Field(min_length=1, max_length=1000)


class ManualProductInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    category_path: list[str] = Field(default_factory=list, max_length=20)
    images: list[HttpUrl] = Field(default_factory=list, max_length=20)
    price: PriceInput | None = None
    facts: list[FactInput] = Field(default_factory=list, max_length=100)


class FactStatusInput(BaseModel):
    status: FactStatus


class ProductSnapshotOutput(BaseModel):
    id: UUID
    source_id: UUID
    title: str
    description: str | None
    category_path: list[str]
    images: list[str]
    price_amount: Decimal | None
    price_currency: str | None
    canonical_digest: str
    created_at: datetime


class ProductFactOutput(BaseModel):
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


class ProductOutput(BaseModel):
    product_id: UUID
    snapshot: ProductSnapshotOutput
    facts: list[ProductFactOutput]
