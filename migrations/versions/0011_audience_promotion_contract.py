"""Add immutable, idempotent Promotion Facts for the P1.3c creative contract.

Revision ID: 0011_audience_promotion
Revises: 0010_fact_rebind_guard
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_audience_promotion"
down_revision: str | None = "0010_fact_rebind_guard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PROMOTION_VALUE_FUNCTION = """
CREATE OR REPLACE FUNCTION rem_promotion_value_is_valid(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    kind text;
    percent numeric;
    amount numeric;
    starts_at timestamptz;
    ends_at timestamptz;
BEGIN
    IF jsonb_typeof(value) <> 'object'
       OR value->>'schema_version' <> 'promotion-v1'
       OR value->>'market' <> 'US'
       OR value->>'channel' <> 'tiktok_shop'
       OR value->>'timezone' <> 'America/Los_Angeles' THEN
        RETURN false;
    END IF;
    IF EXISTS (
        SELECT 1
        FROM jsonb_object_keys(value) AS key
        WHERE key NOT IN (
            'schema_version', 'kind', 'percent', 'amount', 'currency',
            'market', 'channel', 'timezone', 'effective_from', 'effective_to'
        )
    )
       OR value->>'effective_from' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$'
       OR value->>'effective_to' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' THEN
        RETURN false;
    END IF;
    kind := value->>'kind';
    starts_at := (value->>'effective_from')::timestamptz;
    ends_at := (value->>'effective_to')::timestamptz;
    IF starts_at >= ends_at THEN
        RETURN false;
    END IF;
    IF kind = 'percent_off' THEN
        percent := (value->>'percent')::numeric;
        RETURN percent IS NOT NULL AND percent > 0 AND percent <= 100
            AND NOT (value ? 'amount') AND NOT (value ? 'currency');
    ELSIF kind = 'amount_off' THEN
        amount := (value->>'amount')::numeric;
        RETURN amount IS NOT NULL AND amount > 0 AND value->>'currency' = 'USD'
            AND NOT (value ? 'percent');
    END IF;
    RETURN false;
EXCEPTION WHEN others THEN
    RETURN false;
END;
$$;
"""

_STRICT_FUNCTION = """
CREATE OR REPLACE FUNCTION rem_reject_locked_fact_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'product facts are append-only';
    END IF;
    IF ROW(
        NEW.snapshot_id, NEW.claim_type, NEW.claim, NEW.value,
        NEW.evidence_kind, NEW.evidence_locator, NEW.evidence_excerpt,
        NEW.confidence, NEW.operation_key, NEW.operation_input_digest
    ) IS DISTINCT FROM ROW(
        OLD.snapshot_id, OLD.claim_type, OLD.claim, OLD.value,
        OLD.evidence_kind, OLD.evidence_locator, OLD.evidence_excerpt,
        OLD.confidence, OLD.operation_key, OLD.operation_input_digest
    ) THEN
        RAISE EXCEPTION 'product fact evidence is immutable';
    END IF;
    IF OLD.status = 'locked' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'locked product facts are immutable';
    END IF;
    RETURN NEW;
END;
$$;
"""

_PREVIOUS_STRICT_FUNCTION = _STRICT_FUNCTION.replace(
", NEW.operation_key, NEW.operation_input_digest", "").replace(
    ", OLD.operation_key, OLD.operation_input_digest", ""
)


def upgrade() -> None:
    op.add_column("product_facts", sa.Column("operation_key", sa.String(length=255)))
    op.add_column("product_facts", sa.Column("operation_input_digest", sa.String(length=64)))
    op.create_check_constraint(
        "ck_product_facts_operation_metadata",
        "product_facts",
        "(operation_key IS NULL AND operation_input_digest IS NULL) OR "
        "(operation_key IS NOT NULL AND operation_input_digest IS NOT NULL)",
    )
    op.create_index(
        "uq_product_facts_snapshot_operation_key",
        "product_facts",
        ["snapshot_id", "operation_key"],
        unique=True,
        postgresql_where="operation_key IS NOT NULL",
    )
    op.execute(_PROMOTION_VALUE_FUNCTION)
    op.create_check_constraint(
        "ck_product_facts_promotion_value",
        "product_facts",
        "claim_type <> 'promotion' OR rem_promotion_value_is_valid(value)",
    )
    op.execute(_STRICT_FUNCTION)


def downgrade() -> None:
    op.execute(_PREVIOUS_STRICT_FUNCTION)
    op.drop_constraint("ck_product_facts_promotion_value", "product_facts", type_="check")
    op.execute("DROP FUNCTION rem_promotion_value_is_valid(jsonb)")
    op.drop_index("uq_product_facts_snapshot_operation_key", table_name="product_facts")
    op.drop_constraint("ck_product_facts_operation_metadata", "product_facts", type_="check")
    op.drop_column("product_facts", "operation_input_digest")
    op.drop_column("product_facts", "operation_key")
