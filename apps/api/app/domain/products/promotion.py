from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.products.entities import FactStatus, ProductFact

PromotionKind = Literal["percent_off", "amount_off"]


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


class PromotionValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["promotion-v1"] = "promotion-v1"
    kind: PromotionKind
    percent: Decimal | None = Field(default=None, gt=0, le=100)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: Literal["USD"] | None = None
    market: Literal["US"] = "US"
    channel: Literal["tiktok_shop"] = "tiktok_shop"
    timezone: Literal["America/Los_Angeles"] = "America/Los_Angeles"
    effective_from: datetime
    effective_to: datetime

    @model_validator(mode="after")
    def validate_shape(self) -> "PromotionValue":
        if self.effective_from.tzinfo is None or self.effective_to.tzinfo is None:
            raise ValueError("promotion timestamps must include an offset")
        if self.effective_from >= self.effective_to:
            raise ValueError("promotion effective_from must precede effective_to")
        if self.kind == "percent_off" and (
            self.percent is None or self.amount is not None or self.currency is not None
        ):
            raise ValueError("percent promotion must include only percent")
        if self.kind == "amount_off" and (
            self.amount is None or self.currency is None or self.percent is not None
        ):
            raise ValueError("amount promotion must include amount and currency")
        return self


class PromotionRender(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: UUID
    text: str


def promotion_value(fact: ProductFact) -> PromotionValue:
    if fact.claim_type != "promotion":
        raise ValueError("fact is not a promotion")
    return PromotionValue.model_validate(fact.value)


def promotion_is_active(fact: ProductFact, *, now: datetime | None = None) -> bool:
    if fact.status not in {FactStatus.CONFIRMED, FactStatus.LOCKED}:
        return False
    value = promotion_value(fact)
    observed_at = (now or datetime.now(UTC)).astimezone(UTC)
    return value.effective_from.astimezone(UTC) <= observed_at < value.effective_to.astimezone(UTC)


def promotion_claim(value: PromotionValue) -> str:
    if value.kind == "percent_off":
        assert value.percent is not None
        return f"{_decimal_text(value.percent)}% off on TikTok Shop in the US."
    assert value.amount is not None and value.currency is not None
    return f"${_decimal_text(value.amount)} off on TikTok Shop in the US."


def render_promotion(fact: ProductFact, *, language: str) -> PromotionRender:
    value = promotion_value(fact)
    if language.lower().startswith("zh"):
        if value.kind == "percent_off":
            assert value.percent is not None
            text = f"美国 TikTok Shop 立减 {_decimal_text(value.percent)}%。"
        else:
            assert value.amount is not None
            text = f"美国 TikTok Shop 立减 ${_decimal_text(value.amount)}。"
    else:
        text = promotion_claim(value)
    return PromotionRender(fact_id=fact.id, text=text)
