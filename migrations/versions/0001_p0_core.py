"""Create P0 product, job, and script tables.

Revision ID: 0001_p0_core
Revises:
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_p0_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("parse_status", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(64)),
    )
    op.create_table(
        "product_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category_path", postgresql.JSONB(), nullable=False),
        sa.Column("images", postgresql.JSONB(), nullable=False),
        sa.Column("price_amount", sa.Numeric(18, 4)),
        sa.Column("price_currency", sa.String(3)),
        sa.Column("canonical_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_snapshots_source_created", "product_snapshots", ["source_id", "created_at"])
    op.create_table(
        "product_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_snapshots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("claim_type", sa.String(64), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column("evidence_locator", sa.Text(), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_facts_snapshot", "product_facts", ["snapshot_id"])
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_detail", sa.Text()),
        sa.Column("result_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("job_type", "idempotency_key", name="uq_job_idempotency"),
    )
    op.create_table(
        "script_generations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_snapshots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("selected_fact_ids", postgresql.JSONB(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("pattern_key", sa.String(64), nullable=False),
        sa.Column("pattern_version", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_contract_version", sa.String(32), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "script_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "generation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("script_generations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "parent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("script_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column("draft", postgresql.JSONB(), nullable=False),
        sa.Column("validation_report", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_script_versions_generation", "script_versions", ["generation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_script_versions_generation", table_name="script_versions")
    op.drop_table("script_versions")
    op.drop_table("script_generations")
    op.drop_table("jobs")
    op.drop_index("ix_product_facts_snapshot", table_name="product_facts")
    op.drop_table("product_facts")
    op.drop_index("ix_product_snapshots_source_created", table_name="product_snapshots")
    op.drop_table("product_snapshots")
    op.drop_table("product_sources")
