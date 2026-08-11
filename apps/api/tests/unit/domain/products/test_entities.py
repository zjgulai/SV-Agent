from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.products.entities import FactStatus, ProductFact, ProductSnapshot
from app.domain.products.errors import LockedFactError

SOURCE_ID = UUID("00000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000002")


def test_snapshot_digest_is_stable_for_equivalent_fields() -> None:
    left = ProductSnapshot.create(
        source_id=SOURCE_ID,
        title=" Pulse Mix ",
        description="Energy powder",
        category_path=("Food", "Drink Mix"),
        images=("https://example.com/a.png",),
        price_amount=Decimal("19.90"),
        price_currency="USD",
    )
    right = ProductSnapshot.create(
        source_id=SOURCE_ID,
        title="Pulse Mix",
        description="Energy powder",
        category_path=("Food", "Drink Mix"),
        images=("https://example.com/a.png",),
        price_amount=Decimal("19.900"),
        price_currency="usd",
    )

    assert left.canonical_digest == right.canonical_digest


def test_locked_fact_cannot_be_changed_in_place() -> None:
    fact = ProductFact.create(
        snapshot_id=SNAPSHOT_ID,
        claim_type="material",
        claim="The pouch is resealable",
        value={"resealable": True},
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt="Resealable pouch",
        confidence=1.0,
    ).transition_to(FactStatus.LOCKED)

    with pytest.raises(LockedFactError):
        fact.transition_to(FactStatus.REJECTED)
