"""Close NULL pass-through in the fact-rebind provenance guard.

Revision ID: 0010_fact_rebind_guard
Revises: 0009_fact_bound_edit
Create Date: 2026-08-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010_fact_rebind_guard"
down_revision: str | None = "0009_fact_bound_edit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_script_versions_fact_rebind_provenance",
        "script_versions",
        type_="check",
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
        OR (revision_kind IS NOT NULL
            AND actor_kind IS NOT NULL
            AND reason_code IS NOT NULL
            AND operation_key IS NOT NULL
            AND operation_input_digest IS NOT NULL
            AND revision_kind = 'fact_rebind'
            AND actor_kind = 'local_operator'
            AND reason_code = 'fact_rebind')
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_script_versions_fact_rebind_provenance",
        "script_versions",
        type_="check",
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
