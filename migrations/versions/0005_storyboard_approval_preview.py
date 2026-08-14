"""Add immutable storyboard review and approval records.

Revision ID: 0005_storyboard_approval_preview
Revises: 0004_generation_fact_selection
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005_storyboard_approval_preview"
down_revision: str | None = "0004_generation_fact_selection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "storyboard_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "script_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("script_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_snapshots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("selected_fact_ids", JSONB(), nullable=False),
        sa.Column("excluded_fact_ids", JSONB(), nullable=False),
        sa.Column("pattern_key", sa.String(length=64), nullable=False),
        sa.Column("pattern_version", sa.String(length=32), nullable=False),
        sa.Column("phase_sequence", JSONB(), nullable=False),
        sa.Column("draft", JSONB(), nullable=False),
        sa.Column("validation_report", JSONB(), nullable=False),
        sa.Column("preflight_digest", sa.String(length=64), nullable=False),
        sa.Column("storyboard_digest", sa.String(length=64), nullable=False),
        sa.Column("preview_contract_version", sa.String(length=32), nullable=False),
        sa.Column("operation_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "script_version_id",
            "operation_key",
            name="uq_storyboard_version_operation",
        ),
    )
    op.execute("CREATE SEQUENCE storyboard_approval_event_sequence")
    op.create_table(
        "storyboard_approval_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "storyboard_id",
            UUID(as_uuid=True),
            sa.ForeignKey("storyboard_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("storyboard_digest", sa.String(length=64), nullable=False),
        sa.Column("preflight_digest", sa.String(length=64), nullable=False),
        sa.Column("approval_digest", sa.String(length=64), nullable=False),
        sa.Column("validation_report", JSONB(), nullable=False),
        sa.Column("operation_key", sa.String(length=255), nullable=False),
        sa.Column(
            "event_sequence",
            sa.BigInteger(),
            server_default=sa.text("nextval('storyboard_approval_event_sequence')"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_storyboard_approval_event_decision",
        ),
        sa.UniqueConstraint(
            "storyboard_id",
            "operation_key",
            name="uq_storyboard_approval_event_operation",
        ),
    )
    op.create_index(
        "ix_storyboard_approval_events_latest",
        "storyboard_approval_events",
        ["storyboard_id", "event_sequence"],
    )
    for table_name in ("storyboard_versions", "storyboard_approval_events"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION rem_reject_immutable_row()
            """
        )


def downgrade() -> None:
    for table_name in ("storyboard_approval_events", "storyboard_versions"):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.drop_index(
        "ix_storyboard_approval_events_latest",
        table_name="storyboard_approval_events",
    )
    op.drop_table("storyboard_approval_events")
    op.execute("DROP SEQUENCE storyboard_approval_event_sequence")
    op.drop_table("storyboard_versions")
