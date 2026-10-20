"""Add the SV-Agent task runtime and immutable event journal.

Revision ID: 0012_sv_agent_persistence
Revises: 0011_audience_promotion
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0012_sv_agent_persistence"
down_revision: str | None = "0011_audience_promotion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_IMMUTABLE_TABLES = (
    "sv_task_revisions",
    "sv_command_receipts",
    "sv_task_events",
    "sv_run_plans",
    "sv_artifacts",
    "sv_runtime_lineage_links",
    "sv_approval_requests",
    "sv_tool_run_events",
    "sv_decision_events",
    "sv_tool_job_links",
)


def upgrade() -> None:
    op.execute("CREATE SEQUENCE sv_runtime_event_sequence")

    op.create_table(
        "sv_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("active_run_id", UUID(as_uuid=True)),
        sa.Column("summary", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "current_revision >= 1", name="ck_sv_tasks_current_revision"
        ),
        sa.CheckConstraint(
            "octet_length(summary::text) <= 16384",
            name="ck_sv_tasks_summary_size",
        ),
    )
    op.create_table(
        "sv_task_revisions",
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_tasks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("goal_track", sa.String(length=48), nullable=False),
        sa.Column("decision_question", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=24), nullable=False),
        sa.Column("market", sa.String(length=2), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("performance_start", sa.Date(), nullable=False),
        sa.Column("performance_end", sa.Date(), nullable=False),
        sa.Column("performance_timezone", sa.String(length=64), nullable=False),
        sa.Column("stop_condition", sa.Text(), nullable=False),
        sa.Column("initial_rights_state", sa.String(length=32), nullable=False),
        sa.Column("brief_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("task_id", "revision", name="pk_sv_task_revisions"),
        sa.CheckConstraint("revision >= 1", name="ck_sv_task_revisions_revision"),
        sa.CheckConstraint(
            "goal_track IN ('product_replication', 'brand_voice_social_resonance')",
            name="ck_sv_task_revisions_goal_track",
        ),
        sa.CheckConstraint(
            "platform IN ('tiktok', 'instagram', 'youtube', 'other')",
            name="ck_sv_task_revisions_platform",
        ),
        sa.CheckConstraint(
            "initial_rights_state IN "
            "('confirmed_for_analysis', 'analysis_only', 'unknown', 'restricted', 'blocked')",
            name="ck_sv_task_revisions_rights_state",
        ),
        sa.CheckConstraint("market ~ '^[A-Z]{2}$'", name="ck_sv_task_revisions_market"),
        sa.CheckConstraint(
            "performance_end >= performance_start",
            name="ck_sv_task_revisions_performance_window",
        ),
        sa.CheckConstraint(
            "brief_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_task_revisions_brief_digest",
        ),
    )
    op.create_table(
        "sv_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("primary_mechanism", sa.String(length=48)),
        sa.Column("creative_dimension", sa.String(length=48)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_runs_task_revision",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("task_id", "id", name="uq_sv_runs_task_id_id"),
        sa.CheckConstraint("task_revision >= 1", name="ck_sv_runs_task_revision"),
        sa.CheckConstraint("revision >= 1", name="ck_sv_runs_revision"),
        sa.CheckConstraint(
            "state IN ('draft', 'planning', 'awaiting_input', 'runnable', 'running', "
            "'awaiting_approval', 'blocked', 'completed_with_limits', 'failed', 'stopped')",
            name="ck_sv_runs_state",
        ),
        sa.CheckConstraint(
            "(primary_mechanism IS NULL) = (creative_dimension IS NULL)",
            name="ck_sv_runs_axis_complete",
        ),
        sa.CheckConstraint(
            "primary_mechanism IS NULL OR "
            "(primary_mechanism = 'narrative-transformation' AND "
            "creative_dimension = 'narrative_arc') OR "
            "(primary_mechanism = 'proof-demonstration' AND "
            "creative_dimension = 'proof_device') OR "
            "(primary_mechanism = 'experience-pov' AND "
            "creative_dimension = 'experience_pov') OR "
            "(primary_mechanism = 'attention-grammar' AND creative_dimension IN "
            "('hook_trigger', 'reveal_cadence', 'caption_cadence', 'visual_contrast', "
            "'sonic_timing')) OR "
            "(primary_mechanism = 'conversion-action' AND creative_dimension IN "
            "('objection_resolution', 'promotion_contract', 'cta_invitation', 'action_path')) OR "
            "(primary_mechanism = 'trend-native' AND creative_dimension IN "
            "('trend_signal_binding', 'trend_semantic_frame', 'template_grammar', "
            "'audio_function'))",
            name="ck_sv_runs_axis_pair",
        ),
        sa.CheckConstraint(
            "state <> 'draft' OR primary_mechanism IS NULL",
            name="ck_sv_runs_draft_axis",
        ),
        sa.CheckConstraint(
            "state NOT IN ('runnable', 'running', 'awaiting_approval', "
            "'completed_with_limits', 'failed') OR primary_mechanism IS NOT NULL",
            name="ck_sv_runs_required_axis",
        ),
    )
    op.create_foreign_key(
        "fk_sv_tasks_current_revision",
        "sv_tasks",
        "sv_task_revisions",
        ["id", "current_revision"],
        ["task_id", "revision"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_sv_tasks_active_run",
        "sv_tasks",
        "sv_runs",
        ["id", "active_run_id"],
        ["task_id", "id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "sv_command_receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_tasks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_scope", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("expected_task_revision", sa.Integer()),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("result_payload", JSONB(), nullable=False),
        sa.Column("result_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "idempotency_scope",
            "idempotency_key",
            name="uq_sv_command_receipts_scope_key",
        ),
        sa.CheckConstraint(
            "expected_task_revision IS NULL OR expected_task_revision >= 1",
            name="ck_sv_command_receipts_expected_revision",
        ),
        sa.CheckConstraint(
            "input_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_command_receipts_input_digest",
        ),
        sa.CheckConstraint(
            "result_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_command_receipts_result_digest",
        ),
        sa.CheckConstraint(
            "octet_length(result_payload::text) <= 16384",
            name="ck_sv_command_receipts_result_size",
        ),
    )
    op.create_table(
        "sv_task_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("nextval('sv_runtime_event_sequence')"),
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
        ),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column("run_revision", sa.Integer()),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("initiated_by_kind", sa.String(length=16), nullable=False),
        sa.Column("initiated_by_ref", sa.String(length=255), nullable=False),
        sa.Column("executed_by_kind", sa.String(length=16), nullable=False),
        sa.Column("executed_by_ref", sa.String(length=255), nullable=False),
        sa.Column(
            "causation_receipt_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_command_receipts.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_task_events_task_revision",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("event_sequence", name="uq_sv_task_events_event_sequence"),
        sa.CheckConstraint("event_sequence >= 1", name="ck_sv_task_events_sequence"),
        sa.CheckConstraint(
            "task_revision >= 1", name="ck_sv_task_events_task_revision"
        ),
        sa.CheckConstraint(
            "(run_id IS NULL) = (run_revision IS NULL)",
            name="ck_sv_task_events_run_ref",
        ),
        sa.CheckConstraint(
            "run_revision IS NULL OR run_revision >= 1",
            name="ck_sv_task_events_run_revision",
        ),
        sa.CheckConstraint(
            "event_type IN ('task.created.v1', 'task.revised.v1', 'run.created.v1', "
            "'run.state_transitioned.v1', 'run.replication_axis_selected.v1', "
            "'run.plan_recorded.v1', 'artifact.recorded.v1', "
            "'runtime_lineage.verified.v1', 'approval.requested.v1')",
            name="ck_sv_task_events_type",
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 16384",
            name="ck_sv_task_events_payload_size",
        ),
        sa.CheckConstraint(
            "payload_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_task_events_payload_digest",
        ),
        sa.CheckConstraint(
            "initiated_by_kind IN ('human', 'agent', 'system', 'operator')",
            name="ck_sv_task_events_initiated_by_kind",
        ),
        sa.CheckConstraint(
            "executed_by_kind IN ('human', 'agent', 'system', 'operator')",
            name="ck_sv_task_events_executed_by_kind",
        ),
    )
    op.create_index(
        "ix_sv_task_events_timeline",
        "sv_task_events",
        ["task_id", "event_sequence"],
    )

    op.create_table(
        "sv_run_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("workflow_name", sa.String(length=128), nullable=False),
        sa.Column("workflow_version", sa.String(length=64), nullable=False),
        sa.Column("capability_catalog_version", sa.String(length=64), nullable=False),
        sa.Column("plan_payload", JSONB(), nullable=False),
        sa.Column("plan_digest", sa.String(length=64), nullable=False),
        sa.Column("input_refs", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_run_plans_task_revision",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("run_id", "version", name="uq_sv_run_plans_run_version"),
        sa.CheckConstraint("version >= 1", name="ck_sv_run_plans_version"),
        sa.CheckConstraint("run_revision >= 1", name="ck_sv_run_plans_run_revision"),
        sa.CheckConstraint(
            "octet_length(plan_payload::text) <= 262144",
            name="ck_sv_run_plans_payload_size",
        ),
        sa.CheckConstraint(
            "plan_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_run_plans_digest",
        ),
    )
    op.create_table(
        "sv_artifacts",
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.String(length=48), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_level", sa.String(length=16), nullable=False),
        sa.Column("proof_level", sa.String(length=16), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("input_refs", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("artifact_id", "version", name="pk_sv_artifacts"),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_artifacts_task_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("version >= 1", name="ck_sv_artifacts_version"),
        sa.CheckConstraint("run_revision >= 1", name="ck_sv_artifacts_run_revision"),
        sa.CheckConstraint(
            "artifact_type IN ('reference_bundle', 'decomposition_map', 'pattern_hypothesis', "
            "'replication_plan', 'fact_map', 'replication_contract', 'adaptation_package', "
            "'media_integrity_record', 'replication_finding')",
            name="ck_sv_artifacts_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'validated', 'awaiting_approval', 'blocked', 'approved', "
            "'stale', 'superseded', 'final_with_limits')",
            name="ck_sv_artifacts_status",
        ),
        sa.CheckConstraint(
            "evidence_level IN ('fact', 'inference', 'unknown')",
            name="ck_sv_artifacts_evidence_level",
        ),
        sa.CheckConstraint(
            "proof_level IN ('local', 'ci', 'private', 'deployment', 'live', 'production')",
            name="ck_sv_artifacts_proof_level",
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 262144",
            name="ck_sv_artifacts_payload_size",
        ),
        sa.CheckConstraint(
            "payload_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_artifacts_payload_digest",
        ),
    )
    op.create_index(
        "ix_sv_artifacts_task_type",
        "sv_artifacts",
        ["task_id", "artifact_type", "version"],
    )
    op.create_table(
        "sv_runtime_lineage_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("source_ref_type", sa.String(length=64), nullable=False),
        sa.Column("source_ref_id", sa.String(length=255), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_digest", sa.String(length=64), nullable=False),
        sa.Column("target_ref_type", sa.String(length=64), nullable=False),
        sa.Column("target_ref_id", sa.String(length=255), nullable=False),
        sa.Column("target_version", sa.Integer(), nullable=False),
        sa.Column("target_digest", sa.String(length=64), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("verifier_name", sa.String(length=128), nullable=False),
        sa.Column("verifier_version", sa.String(length=64), nullable=False),
        sa.Column("verification_payload", JSONB(), nullable=False),
        sa.Column("verification_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_runtime_lineage_task_revision",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_ref_type",
            "source_ref_id",
            "source_version",
            "target_ref_type",
            "target_ref_id",
            "target_version",
            "relation_type",
            "verification_digest",
            name="uq_sv_runtime_lineage_verified_link",
        ),
        sa.CheckConstraint(
            "run_revision >= 1", name="ck_sv_runtime_lineage_run_revision"
        ),
        sa.CheckConstraint(
            "source_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_runtime_lineage_source_digest",
        ),
        sa.CheckConstraint(
            "target_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_runtime_lineage_target_digest",
        ),
        sa.CheckConstraint(
            "verification_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_runtime_lineage_verification_digest",
        ),
        sa.CheckConstraint(
            "octet_length(verification_payload::text) <= 16384",
            name="ck_sv_runtime_lineage_payload_size",
        ),
    )
    op.create_table(
        "sv_approval_requests",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("request_version", sa.Integer(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("gate_kind", sa.String(length=32), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_id", sa.String(length=255), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False),
        sa.Column("artifact_digest", sa.String(length=64), nullable=False),
        sa.Column("precondition_digest", sa.String(length=64), nullable=False),
        sa.Column("predicted_effects", JSONB(), nullable=False),
        sa.Column("explicit_non_effects", JSONB(), nullable=False),
        sa.Column("evidence_summary", JSONB(), nullable=False),
        sa.Column("limitations", JSONB(), nullable=False),
        sa.Column("stale_if", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint(
            "id", "request_version", name="pk_sv_approval_requests"
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_approval_requests_task_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "request_version >= 1", name="ck_sv_approval_requests_version"
        ),
        sa.CheckConstraint(
            "run_revision >= 1", name="ck_sv_approval_requests_run_revision"
        ),
        sa.CheckConstraint(
            "artifact_version >= 1",
            name="ck_sv_approval_requests_artifact_version",
        ),
        sa.CheckConstraint(
            "gate_kind IN ('fact', 'replication_contract', 'storyboard', 'reference_rights', "
            "'child_safety', 'media_integrity', 'source_use', 'originality', 'legal', "
            "'commercial', 'platform', 'deployment', 'production')",
            name="ck_sv_approval_requests_gate",
        ),
        sa.CheckConstraint(
            "request_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_approval_requests_request_digest",
        ),
        sa.CheckConstraint(
            "artifact_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_approval_requests_artifact_digest",
        ),
        sa.CheckConstraint(
            "precondition_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_approval_requests_precondition_digest",
        ),
        sa.CheckConstraint(
            "octet_length(predicted_effects::text) <= 262144 AND "
            "octet_length(explicit_non_effects::text) <= 262144 AND "
            "octet_length(evidence_summary::text) <= 262144 AND "
            "octet_length(limitations::text) <= 262144 AND "
            "octet_length(stale_if::text) <= 262144",
            name="ck_sv_approval_requests_payload_sizes",
        ),
    )
    op.create_table(
        "sv_tool_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_version", sa.String(length=64), nullable=False),
        sa.Column("intent_summary", sa.Text(), nullable=False),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("effect_class", sa.String(length=8), nullable=False),
        sa.Column("approval_request_id", UUID(as_uuid=True)),
        sa.Column("approval_request_version", sa.Integer()),
        sa.Column("idempotency_key", sa.String(length=255)),
        sa.Column("attempt_token", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("artifact_refs", JSONB(), nullable=False),
        sa.Column("stable_error_code", sa.String(length=64)),
        sa.Column("recovery_action", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_tool_runs_task_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ("approval_request_id", "approval_request_version"),
            ("sv_approval_requests.id", "sv_approval_requests.request_version"),
            name="fk_sv_tool_runs_approval_request",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("task_revision >= 1", name="ck_sv_tool_runs_task_revision"),
        sa.CheckConstraint("run_revision >= 1", name="ck_sv_tool_runs_run_revision"),
        sa.CheckConstraint("revision >= 1", name="ck_sv_tool_runs_revision"),
        sa.CheckConstraint("attempt_token >= 1", name="ck_sv_tool_runs_attempt_token"),
        sa.CheckConstraint(
            "effect_class IN ('read', 'write')",
            name="ck_sv_tool_runs_effect_class",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'unavailable', 'unknown')",
            name="ck_sv_tool_runs_status",
        ),
        sa.CheckConstraint(
            "(approval_request_id IS NULL) = (approval_request_version IS NULL)",
            name="ck_sv_tool_runs_approval_ref",
        ),
        sa.CheckConstraint(
            "effect_class = 'read' OR approval_request_id IS NOT NULL",
            name="ck_sv_tool_runs_write_approval",
        ),
        sa.CheckConstraint(
            "input_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_tool_runs_input_digest",
        ),
        sa.CheckConstraint(
            "octet_length(artifact_refs::text) <= 262144",
            name="ck_sv_tool_runs_artifact_refs_size",
        ),
    )
    op.create_table(
        "sv_tool_run_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("nextval('sv_runtime_event_sequence')"),
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "tool_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_tool_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("attempt_token", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("initiated_by_kind", sa.String(length=16), nullable=False),
        sa.Column("initiated_by_ref", sa.String(length=255), nullable=False),
        sa.Column("executed_by_kind", sa.String(length=16), nullable=False),
        sa.Column("executed_by_ref", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_tool_run_events_task_revision",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "event_sequence", name="uq_sv_tool_run_events_event_sequence"
        ),
        sa.CheckConstraint(
            "event_sequence >= 1", name="ck_sv_tool_run_events_sequence"
        ),
        sa.CheckConstraint(
            "task_revision >= 1",
            name="ck_sv_tool_run_events_task_revision",
        ),
        sa.CheckConstraint(
            "run_revision >= 1",
            name="ck_sv_tool_run_events_run_revision",
        ),
        sa.CheckConstraint(
            "attempt_token >= 1",
            name="ck_sv_tool_run_events_attempt_token",
        ),
        sa.CheckConstraint(
            "event_type IN ('tool_run.created.v1', 'tool_run.started.v1', "
            "'tool_run.completed.v1', 'tool_run.failed.v1', 'tool_run.unavailable.v1', "
            "'tool_run.effect_unknown.v1', 'tool_run.technical_job_linked.v1')",
            name="ck_sv_tool_run_events_type",
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 16384",
            name="ck_sv_tool_run_events_payload_size",
        ),
        sa.CheckConstraint(
            "payload_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_tool_run_events_payload_digest",
        ),
        sa.CheckConstraint(
            "initiated_by_kind IN ('human', 'agent', 'system', 'operator')",
            name="ck_sv_tool_run_events_initiated_by_kind",
        ),
        sa.CheckConstraint(
            "executed_by_kind IN ('human', 'agent', 'system', 'operator')",
            name="ck_sv_tool_run_events_executed_by_kind",
        ),
    )
    op.create_index(
        "ix_sv_tool_run_events_timeline",
        "sv_tool_run_events",
        ["task_id", "event_sequence"],
    )
    op.create_table(
        "sv_decision_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("nextval('sv_runtime_event_sequence')"),
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("approval_request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("approval_request_version", sa.Integer(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("task_revision", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("decided_by_kind", sa.String(length=16), nullable=False),
        sa.Column("decided_by_ref", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ("approval_request_id", "approval_request_version"),
            ("sv_approval_requests.id", "sv_approval_requests.request_version"),
            name="fk_sv_decision_events_approval_request",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_decision_events_task_revision",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "approval_request_id",
            "approval_request_version",
            name="uq_sv_decision_events_request",
        ),
        sa.UniqueConstraint(
            "event_sequence", name="uq_sv_decision_events_event_sequence"
        ),
        sa.CheckConstraint(
            "event_sequence >= 1", name="ck_sv_decision_events_sequence"
        ),
        sa.CheckConstraint(
            "task_revision >= 1",
            name="ck_sv_decision_events_task_revision",
        ),
        sa.CheckConstraint(
            "run_revision >= 1",
            name="ck_sv_decision_events_run_revision",
        ),
        sa.CheckConstraint(
            "event_type = 'human_decision.recorded.v1'",
            name="ck_sv_decision_events_type",
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject', 'request_evidence', 'stop')",
            name="ck_sv_decision_events_decision",
        ),
        sa.CheckConstraint(
            "decided_by_kind = 'human'",
            name="ck_sv_decision_events_human_actor",
        ),
        sa.CheckConstraint(
            "request_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_decision_events_request_digest",
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 16384",
            name="ck_sv_decision_events_payload_size",
        ),
        sa.CheckConstraint(
            "payload_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_decision_events_payload_digest",
        ),
    )
    op.create_index(
        "ix_sv_decision_events_timeline",
        "sv_decision_events",
        ["task_id", "event_sequence"],
    )
    op.create_table(
        "sv_tool_job_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_tasks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tool_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sv_tool_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("link_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tool_run_id", name="uq_sv_tool_job_links_tool_run"),
        sa.UniqueConstraint("job_id", name="uq_sv_tool_job_links_job"),
        sa.CheckConstraint(
            "link_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sv_tool_job_links_digest",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION rem_guard_sv_task_head() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'sv task heads cannot be deleted';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'sv task identity is immutable';
            END IF;
            IF NEW.current_revision <> OLD.current_revision + 1 THEN
                RAISE EXCEPTION 'sv task revision must advance by one';
            END IF;
            IF NEW.updated_at < OLD.updated_at THEN
                RAISE EXCEPTION 'sv task updated_at cannot move backwards';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION rem_guard_sv_run_head() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'sv run heads cannot be deleted';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.task_id IS DISTINCT FROM OLD.task_id
               OR NEW.task_revision IS DISTINCT FROM OLD.task_revision
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'sv run intent is immutable';
            END IF;
            IF NEW.revision <> OLD.revision + 1 THEN
                RAISE EXCEPTION 'sv run revision must advance by one';
            END IF;
            IF NEW.updated_at < OLD.updated_at THEN
                RAISE EXCEPTION 'sv run updated_at cannot move backwards';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION rem_guard_sv_tool_run_head() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'sv tool run heads cannot be deleted';
            END IF;
            IF ROW(
                NEW.id, NEW.task_id, NEW.task_revision, NEW.run_id, NEW.run_revision,
                NEW.tool_name, NEW.tool_version, NEW.intent_summary, NEW.input_digest,
                NEW.effect_class, NEW.approval_request_id, NEW.approval_request_version,
                NEW.idempotency_key, NEW.created_at
            ) IS DISTINCT FROM ROW(
                OLD.id, OLD.task_id, OLD.task_revision, OLD.run_id, OLD.run_revision,
                OLD.tool_name, OLD.tool_version, OLD.intent_summary, OLD.input_digest,
                OLD.effect_class, OLD.approval_request_id, OLD.approval_request_version,
                OLD.idempotency_key, OLD.created_at
            ) THEN
                RAISE EXCEPTION 'sv tool run intent is immutable';
            END IF;
            IF NEW.revision <> OLD.revision + 1 THEN
                RAISE EXCEPTION 'sv tool run revision must advance by one';
            END IF;
            IF NEW.attempt_token < OLD.attempt_token THEN
                RAISE EXCEPTION 'sv tool run attempt token cannot move backwards';
            END IF;
            IF NEW.updated_at < OLD.updated_at THEN
                RAISE EXCEPTION 'sv tool run updated_at cannot move backwards';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_sv_tasks_guard
        BEFORE UPDATE OR DELETE ON sv_tasks
        FOR EACH ROW EXECUTE FUNCTION rem_guard_sv_task_head()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_sv_runs_guard
        BEFORE UPDATE OR DELETE ON sv_runs
        FOR EACH ROW EXECUTE FUNCTION rem_guard_sv_run_head()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_sv_tool_runs_guard
        BEFORE UPDATE OR DELETE ON sv_tool_runs
        FOR EACH ROW EXECUTE FUNCTION rem_guard_sv_tool_run_head()
        """
    )
    for table_name in _IMMUTABLE_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION rem_reject_immutable_row()
            """
        )


def downgrade() -> None:
    for table_name in reversed(_IMMUTABLE_TABLES):
        op.execute(f"DROP TRIGGER trg_{table_name}_immutable ON {table_name}")
    op.execute("DROP TRIGGER trg_sv_tool_runs_guard ON sv_tool_runs")
    op.execute("DROP TRIGGER trg_sv_runs_guard ON sv_runs")
    op.execute("DROP TRIGGER trg_sv_tasks_guard ON sv_tasks")
    op.execute("DROP FUNCTION rem_guard_sv_tool_run_head()")
    op.execute("DROP FUNCTION rem_guard_sv_run_head()")
    op.execute("DROP FUNCTION rem_guard_sv_task_head()")

    op.drop_table("sv_tool_job_links")
    op.drop_index("ix_sv_decision_events_timeline", table_name="sv_decision_events")
    op.drop_table("sv_decision_events")
    op.drop_index("ix_sv_tool_run_events_timeline", table_name="sv_tool_run_events")
    op.drop_table("sv_tool_run_events")
    op.drop_table("sv_tool_runs")
    op.drop_table("sv_approval_requests")
    op.drop_table("sv_runtime_lineage_links")
    op.drop_index("ix_sv_artifacts_task_type", table_name="sv_artifacts")
    op.drop_table("sv_artifacts")
    op.drop_table("sv_run_plans")
    op.drop_index("ix_sv_task_events_timeline", table_name="sv_task_events")
    op.drop_table("sv_task_events")
    op.drop_table("sv_command_receipts")
    op.drop_constraint("fk_sv_tasks_active_run", "sv_tasks", type_="foreignkey")
    op.drop_constraint("fk_sv_tasks_current_revision", "sv_tasks", type_="foreignkey")
    op.drop_table("sv_runs")
    op.drop_table("sv_task_revisions")
    op.drop_table("sv_tasks")
    op.execute("DROP SEQUENCE sv_runtime_event_sequence")
