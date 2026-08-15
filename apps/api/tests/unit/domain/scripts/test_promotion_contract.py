from decimal import Decimal
from uuid import UUID

from app.adapters.providers.deterministic import DeterministicScriptProvider
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.products.promotion import render_promotion
from app.domain.scripts.creative_contract import enforce_creative_contract
from app.domain.scripts.patterns import compile_pattern
from app.domain.scripts.validation import validate_script
from app.ports.script_provider import ScriptGenerationRequest, SupportedFact


async def test_promotion_is_rendered_only_in_the_final_offer_cta_slot() -> None:
    snapshot_id = UUID("00000000-0000-0000-0000-000000000121")
    product_fact = ProductFact.create(
        id=UUID("00000000-0000-0000-0000-000000000122"),
        snapshot_id=snapshot_id,
        claim_type="feature",
        claim="The pouch is resealable",
        value={"resealable": True},
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt="Resealable pouch",
        confidence=Decimal(1),
        status=FactStatus.CONFIRMED,
    )
    promotion_fact = ProductFact.create(
        id=UUID("00000000-0000-0000-0000-000000000123"),
        snapshot_id=snapshot_id,
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
        evidence_excerpt="Promotion window",
        confidence=Decimal(1),
        status=FactStatus.CONFIRMED,
    )
    pattern = compile_pattern("offer_cta", duration_seconds=15, language="en")
    promotion = render_promotion(promotion_fact, language="en")
    draft = await DeterministicScriptProvider().generate(
        ScriptGenerationRequest(
            snapshot_id=snapshot_id,
            title="Pulse Mix",
            facts=[SupportedFact(id=product_fact.id, claim=product_fact.claim, claim_type="feature")],
            target_duration_seconds=15,
            language="en",
            audience="General routine",
            pattern_definition=pattern,
            promotion=promotion,
        )
    )
    enforced = enforce_creative_contract(draft, pattern=pattern, promotion=promotion)

    report = validate_script(enforced, {product_fact.id: product_fact}, pattern_definition=pattern, promotion=promotion)
    assert report.acceptable
    assert [shot.promotion for shot in enforced.shots[:-1]] == [None] * (len(enforced.shots) - 1)
    assert enforced.shots[-1].promotion == promotion

    misplaced = enforced.model_copy(
        update={
            "shots": [
                enforced.shots[0].model_copy(update={"promotion": promotion}),
                *enforced.shots[1:-1],
                enforced.shots[-1].model_copy(update={"promotion": None}),
            ]
        }
    )
    misplaced_report = validate_script(misplaced, {product_fact.id: product_fact}, pattern_definition=pattern, promotion=promotion)
    assert {finding.rule_id for finding in misplaced_report.blocking} >= {
        "PROMOTION_SLOT_INVALID",
        "PROMOTION_RENDER_MISMATCH",
    }
