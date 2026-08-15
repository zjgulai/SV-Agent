"""Add durable outbox and append-only execution ledgers.

Revision ID: 0006_reliable_execution_ledger
Revises: 0005_storyboard_approval_preview
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0006_reliable_execution_ledger"
down_revision: str | None = "0005_storyboard_approval_preview"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE job_event_sequence")
    op.create_table(
        "outbox_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("delivery_state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("delivery_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("lease_token", UUID(as_uuid=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(length=64)),
        sa.Column("last_error_detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type = 'job.dispatch.v1'", name="ck_outbox_events_type"
        ),
        sa.CheckConstraint(
            "delivery_state IN ('pending', 'leased', 'published')",
            name="ck_outbox_events_delivery_state",
        ),
        sa.CheckConstraint(
            "delivery_attempt_count >= 0", name="ck_outbox_events_attempt_count"
        ),
        sa.UniqueConstraint("job_id", "event_type", name="uq_outbox_events_job_type"),
    )
    op.create_index(
        "ix_outbox_events_due",
        "outbox_events",
        ["delivery_state", "available_at", "id"],
    )
    op.create_table(
        "job_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("from_state", sa.String(length=32)),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("error_detail", sa.Text()),
        sa.Column(
            "event_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("nextval('job_event_sequence')"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("attempt_count >= 0", name="ck_job_events_attempt_count"),
    )
    op.create_index("ix_job_events_timeline", "job_events", ["job_id", "event_sequence"])
    op.create_table(
        "import_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("attempt_token", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("source_url_digest", sa.String(length=64), nullable=False),
        sa.Column("resolution_digest", sa.String(length=64)),
        sa.Column("response_digest", sa.String(length=64)),
        sa.Column(
            "snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_snapshots.id", ondelete="RESTRICT"),
        ),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("attempt_token >= 1", name="ck_import_attempts_token"),
        sa.CheckConstraint(
            "stage IN ('started', 'parsed', 'succeeded', 'failed')",
            name="ck_import_attempts_stage",
        ),
    )
    op.create_index("ix_import_attempts_job", "import_attempts", ["job_id", "id"])
    op.create_index("ix_import_attempts_source", "import_attempts", ["source_id", "created_at"])

    op.execute(
        """
        CREATE FUNCTION rem_guard_outbox_event() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'outbox events cannot be deleted';
            END IF;
            IF OLD.id IS DISTINCT FROM NEW.id
               OR OLD.event_type IS DISTINCT FROM NEW.event_type
               OR OLD.job_id IS DISTINCT FROM NEW.job_id
               OR OLD.task_name IS DISTINCT FROM NEW.task_name
               OR OLD.payload IS DISTINCT FROM NEW.payload
               OR OLD.payload_digest IS DISTINCT FROM NEW.payload_digest
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'outbox event intent is immutable';
            END IF;
            IF OLD.delivery_state = 'published' AND NEW.delivery_state <> 'published' THEN
                RAISE EXCEPTION 'published outbox events cannot be reopened';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_outbox_events_guard
        BEFORE UPDATE OR DELETE ON outbox_events
        FOR EACH ROW EXECUTE FUNCTION rem_guard_outbox_event()
        """
    )
    for table_name in ("job_events", "import_attempts"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION rem_reject_immutable_row()
            """
        )


def downgrade() -> None:
    for table_name in ("import_attempts", "job_events"):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP TRIGGER trg_outbox_events_guard ON outbox_events")
    op.execute("DROP FUNCTION rem_guard_outbox_event()")
    op.drop_index("ix_import_attempts_source", table_name="import_attempts")
    op.drop_index("ix_import_attempts_job", table_name="import_attempts")
    op.drop_table("import_attempts")
    op.drop_index("ix_job_events_timeline", table_name="job_events")
    op.drop_table("job_events")
    op.execute("DROP SEQUENCE job_event_sequence")
    op.drop_index("ix_outbox_events_due", table_name="outbox_events")
    op.drop_table("outbox_events")
