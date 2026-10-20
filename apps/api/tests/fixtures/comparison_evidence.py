from decimal import Decimal
from typing import Any


def reviewed_performance_package_payload() -> dict[str, Any]:
    """Synthetic public-reviewed package; it is never loaded by application runtime."""
    return {
        "schema_version": "reviewed-performance-package.v1",
        "package_ref": "synthetic-leap-momcozy-de-bottle-care-v1",
        "evidence_context": "content_performance",
        "visibility": "public_reviewed",
        "subject": {
            "brand_workspace": "momcozy",
            "market": "DE",
            "product_family": "bottle_washer_warmer",
            "model": {"state": "not_reported", "value": None},
            "variant": {"state": "not_reported", "value": None},
            "source_subject_label": "momcozy-德国-奶瓶清洗暖奶器",
        },
        "window": {
            "start": "2026-08-21",
            "end": "2026-08-27",
            "timezone": {"state": "not_reported", "value": None},
        },
        "source": {
            "locator": "https://leap-ai-delta.vercel.app/public-report/c89da8a0-681f-42ed-91b2-8a3062f19ac8",
            "captured_on": "2026-08-27",
            "captured_at": {"state": "not_reported", "value": None},
            "snapshot_state": "not_reported",
            "collection_method": {"state": "unknown", "value": None},
            "deduplication_method": {"state": "unknown", "value": None},
            "paid_organic_split": {"state": "unknown", "value": None},
            "ranking_formula": {"state": "unknown", "value": None},
        },
        "review": {
            "review_state": "reviewed_with_limitations",
            "review_scope": "technical_and_claim_safety",
            "review_policy_version": "performance-review.v1",
            "reviewed_at": "2026-08-28T09:30:00+00:00",
        },
        "observations": [
            {
                "observation_ref": "overall.views",
                "platform": "all",
                "metric": "views",
                "state": "observed",
                "value": Decimal(10312),
                "unit": "count",
                "source_display": "10.3K",
                "source_presentations": [],
                "precision": "exact_payload",
                "disposition": "cite",
            },
            {
                "observation_ref": "overall.comments",
                "platform": "all",
                "metric": "comments",
                "state": "source_ambiguous",
                "value": None,
                "unit": "count",
                "source_display": None,
                "source_presentations": [
                    {"surface": "getter_payload", "display": "0"},
                    {"surface": "page_ui", "display": "-"},
                ],
                "precision": "unresolved",
                "disposition": "recompute",
            },
        ],
        "creative_signals": [
            {
                "signal_ref": "manual_to_automation_relief",
                "role": "hypothesis_only",
                "disposition": "test",
            }
        ],
        "reported_product_claims": [
            {
                "claim_ref": "high_temperature_disinfection",
                "role": "fact_gate_required",
                "fact_gate": "required",
                "disposition": "reject",
            }
        ],
        "limitations": ["COLLECTION_METHOD_UNDISCLOSED"],
    }
