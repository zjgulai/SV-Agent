"""Persist generation fact selection and explicit deny-set.

Revision ID: 0004_generation_fact_selection
Revises: 0003_fact_evidence_immutability
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004_generation_fact_selection"
down_revision: str | None = "0003_fact_evidence_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "script_generations",
        sa.Column(
            "excluded_fact_ids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("script_generations", "excluded_fact_ids")
