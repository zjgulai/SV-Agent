"""Add bounded broker delivery and operator dead-letter recovery.

Revision ID: 0008_outbox_dead_letter
Revises: 0007_import_attempt_sequence
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_outbox_dead_letter"
down_revision: str | None = "0007_import_attempt_sequence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("delivery_cycle_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("manual_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "outbox_events",
        sa.Column("last_manual_retry_at", sa.DateTime(timezone=True)),
    )
    op.add_column("outbox_events", sa.Column("dead_letter_code", sa.String(length=64)))
    op.add_column(
        "outbox_events", sa.Column("dead_lettered_at", sa.DateTime(timezone=True))
    )
    op.execute(
        "UPDATE outbox_events SET delivery_cycle_started_at = created_at "
        "WHERE delivery_cycle_started_at IS NULL"
    )
    op.execute(
        "UPDATE outbox_events SET lease_token = NULL "
        "WHERE delivery_state = 'published'"
    )
    op.alter_column("outbox_events", "delivery_cycle_started_at", nullable=False)
    op.drop_constraint(
        "ck_outbox_events_delivery_state", "outbox_events", type_="check"
    )
    op.create_check_constraint(
        "ck_outbox_events_delivery_state",
        "outbox_events",
        "delivery_state IN ('pending', 'leased', 'published', 'dead')",
    )
    op.create_check_constraint(
        "ck_outbox_events_manual_retry_count",
        "outbox_events",
        "manual_retry_count >= 0",
    )
    op.create_check_constraint(
        "ck_outbox_events_delivery_fields",
        "outbox_events",
        """
        (delivery_state = 'pending'
            AND lease_token IS NULL
            AND lease_expires_at IS NULL
            AND published_at IS NULL
            AND dead_letter_code IS NULL
            AND dead_lettered_at IS NULL)
        OR (delivery_state = 'leased'
            AND lease_token IS NOT NULL
            AND lease_expires_at IS NOT NULL
            AND published_at IS NULL
            AND dead_letter_code IS NULL
            AND dead_lettered_at IS NULL)
        OR (delivery_state = 'published'
            AND lease_token IS NULL
            AND lease_expires_at IS NULL
            AND published_at IS NOT NULL
            AND dead_letter_code IS NULL
            AND dead_lettered_at IS NULL)
        OR (delivery_state = 'dead'
            AND lease_token IS NULL
            AND lease_expires_at IS NULL
            AND published_at IS NULL
            AND dead_letter_code IS NOT NULL
            AND dead_lettered_at IS NOT NULL)
        """,
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION rem_guard_outbox_event() RETURNS trigger AS $$
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
            IF OLD.delivery_state = 'dead' AND NEW.delivery_state = 'pending' THEN
                IF NEW.manual_retry_count <> OLD.manual_retry_count + 1
                   OR NEW.delivery_attempt_count <> 0
                   OR NEW.delivery_cycle_started_at < OLD.delivery_cycle_started_at
                   OR NEW.last_manual_retry_at IS NULL THEN
                    RAISE EXCEPTION 'dead outbox event requires a new manual retry cycle';
                END IF;
            ELSIF OLD.delivery_state = 'dead' AND NEW.delivery_state <> 'dead' THEN
                RAISE EXCEPTION 'dead outbox events can only be manually requeued';
            ELSIF OLD.delivery_state <> 'dead'
                  AND (NEW.manual_retry_count <> OLD.manual_retry_count
                       OR NEW.delivery_cycle_started_at <> OLD.delivery_cycle_started_at
                       OR NEW.last_manual_retry_at IS DISTINCT FROM OLD.last_manual_retry_at) THEN
                RAISE EXCEPTION 'outbox retry cycle can change only after dead letter';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE outbox_events
        SET delivery_state = 'pending',
            delivery_attempt_count = 0,
            delivery_cycle_started_at = statement_timestamp(),
            manual_retry_count = manual_retry_count + 1,
            last_manual_retry_at = statement_timestamp(),
            dead_letter_code = NULL,
            dead_lettered_at = NULL,
            available_at = statement_timestamp()
        WHERE delivery_state = 'dead'
        """
    )
    op.drop_constraint("ck_outbox_events_delivery_fields", "outbox_events", type_="check")
    op.drop_constraint(
        "ck_outbox_events_manual_retry_count", "outbox_events", type_="check"
    )
    op.drop_constraint(
        "ck_outbox_events_delivery_state", "outbox_events", type_="check"
    )
    op.create_check_constraint(
        "ck_outbox_events_delivery_state",
        "outbox_events",
        "delivery_state IN ('pending', 'leased', 'published')",
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION rem_guard_outbox_event() RETURNS trigger AS $$
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
    op.drop_column("outbox_events", "dead_lettered_at")
    op.drop_column("outbox_events", "dead_letter_code")
    op.drop_column("outbox_events", "last_manual_retry_at")
    op.drop_column("outbox_events", "manual_retry_count")
    op.drop_column("outbox_events", "delivery_cycle_started_at")
