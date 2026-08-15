from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.products.entities import FactStatus, ProductFact
from app.domain.products.promotion import (
    PromotionValue,
    promotion_claim,
    promotion_is_active,
    render_promotion,
)


def _promotion(*, status: FactStatus = FactStatus.CONFIRMED) -> ProductFact:
    return ProductFact.create(
        id=UUID("00000000-0000-0000-0000-000000000111"),
        snapshot_id=UUID("00000000-0000-0000-0000-000000000112"),
        claim_type="promotion",
        claim="10% off on TikTok Shop in the US.",
        value={
            "schema_version": "promotion-v1",
            "kind": "percent_off",
            "percent": "10",
            "market": "US",
            "channel": "tiktok_shop",
            "timezone": "America/Los_Angeles",
            "effective_from": "2026-08-14T00:00:00-07:00",
            "effective_to": "2026-08-15T00:00:00-07:00",
        },
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt="Operator-entered promotion window",
        confidence=Decimal(1),
        status=status,
    )


def test_promotion_value_accepts_only_the_declared_shape() -> None:
    value = PromotionValue.model_validate(_promotion().value)
    assert promotion_claim(value) == "10% off on TikTok Shop in the US."
    assert render_promotion(_promotion(), language="zh-CN").text == "美国 TikTok Shop 立减 10%。"

    with pytest.raises(ValidationError):
        PromotionValue.model_validate({**_promotion().value, "amount": "1"})


def test_promotion_activity_requires_ready_status_and_effective_window() -> None:
    fact = _promotion()
    assert promotion_is_active(fact, now=datetime(2026, 8, 14, 12, tzinfo=UTC))
    assert not promotion_is_active(fact, now=datetime(2026, 8, 16, tzinfo=UTC))
    assert not promotion_is_active(_promotion(status=FactStatus.PROPOSED), now=datetime(2026, 8, 14, 12, tzinfo=UTC))
