"""Make product fact evidence append-only.

Revision ID: 0003_fact_evidence_immutability
Revises: 0002_integrity_guards
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_fact_evidence_immutability"
down_revision: str | None = "0002_integrity_guards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_STRICT_FUNCTION = """
CREATE OR REPLACE FUNCTION rem_reject_locked_fact_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'product facts are append-only';
    END IF;
    IF ROW(
        NEW.snapshot_id,
        NEW.claim_type,
        NEW.claim,
        NEW.value,
        NEW.evidence_kind,
        NEW.evidence_locator,
        NEW.evidence_excerpt,
        NEW.confidence
    ) IS DISTINCT FROM ROW(
        OLD.snapshot_id,
        OLD.claim_type,
        OLD.claim,
        OLD.value,
        OLD.evidence_kind,
        OLD.evidence_locator,
        OLD.evidence_excerpt,
        OLD.confidence
    ) THEN
        RAISE EXCEPTION 'product fact evidence is immutable';
    END IF;
    IF OLD.status = 'locked' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'locked product facts are immutable';
    END IF;
    RETURN NEW;
END;
$$
"""

_LOCKED_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION rem_reject_locked_fact_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'locked' THEN
        RAISE EXCEPTION 'locked product facts are immutable';
    END IF;
    RETURN NEW;
END;
$$
"""


def upgrade() -> None:
    op.execute(_STRICT_FUNCTION)


def downgrade() -> None:
    op.execute(_LOCKED_ONLY_FUNCTION)
