"""Add provenance and idempotency for fact-bound script edits.

Revision ID: 0009_fact_bound_edit
Revises: 0008_outbox_dead_letter
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_fact_bound_edit"
down_revision: str | None = "0008_outbox_dead_letter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("script_versions", sa.Column("revision_kind", sa.String(length=32)))
    op.add_column("script_versions", sa.Column("actor_kind", sa.String(length=32)))
    op.add_column("script_versions", sa.Column("reason_code", sa.String(length=64)))
    op.add_column("script_versions", sa.Column("operation_key", sa.String(length=255)))
    op.add_column(
        "script_versions", sa.Column("operation_input_digest", sa.String(length=64))
    )
    op.create_unique_constraint(
        "uq_script_versions_parent_operation",
        "script_versions",
        ["parent_version_id", "operation_key"],
    )
    op.create_check_constraint(
        "ck_script_versions_fact_rebind_provenance",
        "script_versions",
        """
        (revision_kind IS NULL
            AND actor_kind IS NULL
            AND reason_code IS NULL
            AND operation_key IS NULL
            AND operation_input_digest IS NULL)
        OR (revision_kind = 'fact_rebind'
            AND actor_kind = 'local_operator'
            AND reason_code = 'fact_rebind'
            AND operation_key IS NOT NULL
            AND operation_input_digest IS NOT NULL)
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_script_versions_fact_rebind_provenance",
        "script_versions",
        type_="check",
    )
    op.drop_constraint(
        "uq_script_versions_parent_operation",
        "script_versions",
        type_="unique",
    )
    op.drop_column("script_versions", "operation_input_digest")
    op.drop_column("script_versions", "operation_key")
    op.drop_column("script_versions", "reason_code")
    op.drop_column("script_versions", "actor_kind")
    op.drop_column("script_versions", "revision_kind")
