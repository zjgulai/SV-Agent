"""Add append-only and source integrity guards.

Revision ID: 0002_integrity_guards
Revises: 0001_p0_core
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_integrity_guards"
down_revision: str | None = "0001_p0_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_product_sources_schema_org_url",
        "product_sources",
        ["source_url"],
        unique=True,
        postgresql_where=sa.text(
            "source_type = 'schema_org_url' AND source_url IS NOT NULL"
        ),
    )
    op.create_check_constraint(
        "ck_product_facts_evidence_kind",
        "product_facts",
        "evidence_kind IN ('user_assertion', 'source_field')",
    )
    op.execute(
        """
        CREATE FUNCTION rem_reject_immutable_row() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$
        """
    )
    for table_name in ("product_snapshots", "script_generations", "script_versions"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION rem_reject_immutable_row()
            """
        )
    op.execute(
        """
        CREATE FUNCTION rem_reject_locked_fact_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status = 'locked' THEN
                RAISE EXCEPTION 'locked product facts are immutable';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_product_facts_locked_immutable
        BEFORE UPDATE OR DELETE ON product_facts
        FOR EACH ROW EXECUTE FUNCTION rem_reject_locked_fact_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_product_facts_locked_immutable ON product_facts")
    op.execute("DROP FUNCTION rem_reject_locked_fact_mutation()")
    for table_name in ("script_versions", "script_generations", "product_snapshots"):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP FUNCTION rem_reject_immutable_row()")
    op.drop_constraint(
        "ck_product_facts_evidence_kind", "product_facts", type_="check"
    )
    op.drop_index("uq_product_sources_schema_org_url", table_name="product_sources")
