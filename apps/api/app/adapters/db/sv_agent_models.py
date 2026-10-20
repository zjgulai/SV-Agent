from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base

_ACTOR_KIND_CHECK = "{column} IN ('human', 'agent', 'system', 'operator')"
_DIGEST_CHECK = "{column} ~ '^[0-9a-f]{{64}}$'"


class SvTaskRecord(Base):
    __tablename__ = "sv_tasks"
    __table_args__ = (
        CheckConstraint("current_revision >= 1", name="ck_sv_tasks_current_revision"),
        CheckConstraint(
            "octet_length(summary::text) <= 16384",
            name="ck_sv_tasks_summary_size",
        ),
        ForeignKeyConstraint(
            ("id", "current_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_tasks_current_revision",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ("id", "active_run_id"),
            ("sv_runs.task_id", "sv_runs.id"),
            name="fk_sv_tasks_active_run",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    active_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SvTaskRevisionRecord(Base):
    __tablename__ = "sv_task_revisions"
    __table_args__ = (
        PrimaryKeyConstraint("task_id", "revision", name="pk_sv_task_revisions"),
        CheckConstraint("revision >= 1", name="ck_sv_task_revisions_revision"),
        CheckConstraint(
            "goal_track IN ('product_replication', 'brand_voice_social_resonance')",
            name="ck_sv_task_revisions_goal_track",
        ),
        CheckConstraint(
            "platform IN ('tiktok', 'instagram', 'youtube', 'other')",
            name="ck_sv_task_revisions_platform",
        ),
        CheckConstraint(
            "initial_rights_state IN "
            "('confirmed_for_analysis', 'analysis_only', 'unknown', 'restricted', 'blocked')",
            name="ck_sv_task_revisions_rights_state",
        ),
        CheckConstraint("market ~ '^[A-Z]{2}$'", name="ck_sv_task_revisions_market"),
        CheckConstraint(
            "performance_end >= performance_start",
            name="ck_sv_task_revisions_performance_window",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="brief_digest"),
            name="ck_sv_task_revisions_brief_digest",
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sv_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    goal_track: Mapped[str] = mapped_column(String(48), nullable=False)
    decision_question: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False)
    market: Mapped[str] = mapped_column(String(2), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    performance_start: Mapped[date] = mapped_column(Date, nullable=False)
    performance_end: Mapped[date] = mapped_column(Date, nullable=False)
    performance_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    stop_condition: Mapped[str] = mapped_column(Text, nullable=False)
    initial_rights_state: Mapped[str] = mapped_column(String(32), nullable=False)
    brief_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SvRunRecord(Base):
    __tablename__ = "sv_runs"
    __table_args__ = (
        UniqueConstraint("task_id", "id", name="uq_sv_runs_task_id_id"),
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_runs_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("task_revision >= 1", name="ck_sv_runs_task_revision"),
        CheckConstraint("revision >= 1", name="ck_sv_runs_revision"),
        CheckConstraint(
            "state IN ('draft', 'planning', 'awaiting_input', 'runnable', 'running', "
            "'awaiting_approval', 'blocked', 'completed_with_limits', 'failed', 'stopped')",
            name="ck_sv_runs_state",
        ),
        CheckConstraint(
            "(primary_mechanism IS NULL) = (creative_dimension IS NULL)",
            name="ck_sv_runs_axis_complete",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "state <> 'draft' OR primary_mechanism IS NULL",
            name="ck_sv_runs_draft_axis",
        ),
        CheckConstraint(
            "state NOT IN ('runnable', 'running', 'awaiting_approval', "
            "'completed_with_limits', 'failed') OR primary_mechanism IS NOT NULL",
            name="ck_sv_runs_required_axis",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_mechanism: Mapped[str | None] = mapped_column(String(48))
    creative_dimension: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SvCommandReceiptRecord(Base):
    __tablename__ = "sv_command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_scope",
            "idempotency_key",
            name="uq_sv_command_receipts_scope_key",
        ),
        CheckConstraint(
            "expected_task_revision IS NULL OR expected_task_revision >= 1",
            name="ck_sv_command_receipts_expected_revision",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="input_digest"),
            name="ck_sv_command_receipts_input_digest",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="result_digest"),
            name="ck_sv_command_receipts_result_digest",
        ),
        CheckConstraint(
            "octet_length(result_payload::text) <= 16384",
            name="ck_sv_command_receipts_result_size",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sv_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    command_type: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_task_revision: Mapped[int | None] = mapped_column(Integer)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvTaskEventRecord(Base):
    __tablename__ = "sv_task_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_task_events_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("event_sequence >= 1", name="ck_sv_task_events_sequence"),
        CheckConstraint("task_revision >= 1", name="ck_sv_task_events_task_revision"),
        CheckConstraint(
            "(run_id IS NULL) = (run_revision IS NULL)",
            name="ck_sv_task_events_run_ref",
        ),
        CheckConstraint(
            "run_revision IS NULL OR run_revision >= 1",
            name="ck_sv_task_events_run_revision",
        ),
        CheckConstraint(
            "event_type IN ('task.created.v1', 'task.revised.v1', 'run.created.v1', "
            "'run.state_transitioned.v1', 'run.replication_axis_selected.v1', "
            "'run.plan_recorded.v1', 'artifact.recorded.v1', "
            "'runtime_lineage.verified.v1', 'approval.requested.v1')",
            name="ck_sv_task_events_type",
        ),
        CheckConstraint(
            "octet_length(payload::text) <= 16384",
            name="ck_sv_task_events_payload_size",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="payload_digest"),
            name="ck_sv_task_events_payload_digest",
        ),
        CheckConstraint(
            _ACTOR_KIND_CHECK.format(column="initiated_by_kind"),
            name="ck_sv_task_events_initiated_by_kind",
        ),
        CheckConstraint(
            _ACTOR_KIND_CHECK.format(column="executed_by_kind"),
            name="ck_sv_task_events_executed_by_kind",
        ),
        UniqueConstraint("event_sequence", name="uq_sv_task_events_event_sequence"),
        Index("ix_sv_task_events_timeline", "task_id", "event_sequence"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_sequence: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("nextval('sv_runtime_event_sequence')"),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT")
    )
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_revision: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    initiated_by_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    initiated_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    executed_by_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    executed_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    causation_receipt_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sv_command_receipts.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvRunPlanRecord(Base):
    __tablename__ = "sv_run_plans"
    __table_args__ = (
        UniqueConstraint("run_id", "version", name="uq_sv_run_plans_run_version"),
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_run_plans_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version >= 1", name="ck_sv_run_plans_version"),
        CheckConstraint("run_revision >= 1", name="ck_sv_run_plans_run_revision"),
        CheckConstraint(
            "octet_length(plan_payload::text) <= 262144",
            name="ck_sv_run_plans_payload_size",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="plan_digest"),
            name="ck_sv_run_plans_digest",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_catalog_version: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    input_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvArtifactRecord(Base):
    __tablename__ = "sv_artifacts"
    __table_args__ = (
        PrimaryKeyConstraint("artifact_id", "version", name="pk_sv_artifacts"),
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_artifacts_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version >= 1", name="ck_sv_artifacts_version"),
        CheckConstraint("run_revision >= 1", name="ck_sv_artifacts_run_revision"),
        CheckConstraint(
            "artifact_type IN ('reference_bundle', 'decomposition_map', 'pattern_hypothesis', "
            "'replication_plan', 'fact_map', 'replication_contract', 'adaptation_package', "
            "'media_integrity_record', 'replication_finding')",
            name="ck_sv_artifacts_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'validated', 'awaiting_approval', 'blocked', 'approved', "
            "'stale', 'superseded', 'final_with_limits')",
            name="ck_sv_artifacts_status",
        ),
        CheckConstraint(
            "evidence_level IN ('fact', 'inference', 'unknown')",
            name="ck_sv_artifacts_evidence_level",
        ),
        CheckConstraint(
            "proof_level IN ('local', 'ci', 'private', 'deployment', 'live', 'production')",
            name="ck_sv_artifacts_proof_level",
        ),
        CheckConstraint(
            "octet_length(payload::text) <= 262144",
            name="ck_sv_artifacts_payload_size",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="payload_digest"),
            name="ck_sv_artifacts_payload_digest",
        ),
        Index("ix_sv_artifacts_task_type", "task_id", "artifact_type", "version"),
    )

    artifact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(48), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(16), nullable=False)
    proof_level: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    input_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvRuntimeLineageLinkRecord(Base):
    __tablename__ = "sv_runtime_lineage_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_runtime_lineage_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("run_revision >= 1", name="ck_sv_runtime_lineage_run_revision"),
        CheckConstraint(
            _DIGEST_CHECK.format(column="source_digest"),
            name="ck_sv_runtime_lineage_source_digest",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="target_digest"),
            name="ck_sv_runtime_lineage_target_digest",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="verification_digest"),
            name="ck_sv_runtime_lineage_verification_digest",
        ),
        CheckConstraint(
            "octet_length(verification_payload::text) <= 16384",
            name="ck_sv_runtime_lineage_payload_size",
        ),
        UniqueConstraint(
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
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_ref_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    verifier_name: Mapped[str] = mapped_column(String(128), nullable=False)
    verifier_version: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    verification_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvApprovalRequestRecord(Base):
    __tablename__ = "sv_approval_requests"
    __table_args__ = (
        PrimaryKeyConstraint("id", "request_version", name="pk_sv_approval_requests"),
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_approval_requests_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("request_version >= 1", name="ck_sv_approval_requests_version"),
        CheckConstraint("run_revision >= 1", name="ck_sv_approval_requests_run_revision"),
        CheckConstraint("artifact_version >= 1", name="ck_sv_approval_requests_artifact_version"),
        CheckConstraint(
            "gate_kind IN ('fact', 'replication_contract', 'storyboard', 'reference_rights', "
            "'child_safety', 'media_integrity', 'source_use', 'originality', 'legal', "
            "'commercial', 'platform', 'deployment', 'production')",
            name="ck_sv_approval_requests_gate",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="request_digest"),
            name="ck_sv_approval_requests_request_digest",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="artifact_digest"),
            name="ck_sv_approval_requests_artifact_digest",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="precondition_digest"),
            name="ck_sv_approval_requests_precondition_digest",
        ),
        CheckConstraint(
            "octet_length(predicted_effects::text) <= 262144 AND "
            "octet_length(explicit_non_effects::text) <= 262144 AND "
            "octet_length(evidence_summary::text) <= 262144 AND "
            "octet_length(limitations::text) <= 262144 AND "
            "octet_length(stale_if::text) <= 262144",
            name="ck_sv_approval_requests_payload_sizes",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    request_version: Mapped[int] = mapped_column(Integer, nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    gate_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_version: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    precondition_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_effects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    explicit_non_effects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    stale_if: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvToolRunRecord(Base):
    __tablename__ = "sv_tool_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_tool_runs_task_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("approval_request_id", "approval_request_version"),
            ("sv_approval_requests.id", "sv_approval_requests.request_version"),
            name="fk_sv_tool_runs_approval_request",
            ondelete="RESTRICT",
        ),
        CheckConstraint("task_revision >= 1", name="ck_sv_tool_runs_task_revision"),
        CheckConstraint("run_revision >= 1", name="ck_sv_tool_runs_run_revision"),
        CheckConstraint("revision >= 1", name="ck_sv_tool_runs_revision"),
        CheckConstraint("attempt_token >= 1", name="ck_sv_tool_runs_attempt_token"),
        CheckConstraint(
            "effect_class IN ('read', 'write')",
            name="ck_sv_tool_runs_effect_class",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'unavailable', 'unknown')",
            name="ck_sv_tool_runs_status",
        ),
        CheckConstraint(
            "(approval_request_id IS NULL) = (approval_request_version IS NULL)",
            name="ck_sv_tool_runs_approval_ref",
        ),
        CheckConstraint(
            "effect_class = 'read' OR approval_request_id IS NOT NULL",
            name="ck_sv_tool_runs_write_approval",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="input_digest"),
            name="ck_sv_tool_runs_input_digest",
        ),
        CheckConstraint(
            "octet_length(artifact_refs::text) <= 262144",
            name="ck_sv_tool_runs_artifact_refs_size",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_version: Mapped[str] = mapped_column(String(64), nullable=False)
    intent_summary: Mapped[str] = mapped_column(Text, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    effect_class: Mapped[str] = mapped_column(String(8), nullable=False)
    approval_request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    approval_request_version: Mapped[int | None] = mapped_column(Integer)
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    attempt_token: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    artifact_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    stable_error_code: Mapped[str | None] = mapped_column(String(64))
    recovery_action: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvToolRunEventRecord(Base):
    __tablename__ = "sv_tool_run_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_tool_run_events_task_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("event_sequence >= 1", name="ck_sv_tool_run_events_sequence"),
        CheckConstraint("task_revision >= 1", name="ck_sv_tool_run_events_task_revision"),
        CheckConstraint("run_revision >= 1", name="ck_sv_tool_run_events_run_revision"),
        CheckConstraint("attempt_token >= 1", name="ck_sv_tool_run_events_attempt_token"),
        CheckConstraint(
            "event_type IN ('tool_run.created.v1', 'tool_run.started.v1', "
            "'tool_run.completed.v1', 'tool_run.failed.v1', 'tool_run.unavailable.v1', "
            "'tool_run.effect_unknown.v1', 'tool_run.technical_job_linked.v1')",
            name="ck_sv_tool_run_events_type",
        ),
        CheckConstraint(
            "octet_length(payload::text) <= 16384",
            name="ck_sv_tool_run_events_payload_size",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="payload_digest"),
            name="ck_sv_tool_run_events_payload_digest",
        ),
        CheckConstraint(
            _ACTOR_KIND_CHECK.format(column="initiated_by_kind"),
            name="ck_sv_tool_run_events_initiated_by_kind",
        ),
        CheckConstraint(
            _ACTOR_KIND_CHECK.format(column="executed_by_kind"),
            name="ck_sv_tool_run_events_executed_by_kind",
        ),
        UniqueConstraint("event_sequence", name="uq_sv_tool_run_events_event_sequence"),
        Index("ix_sv_tool_run_events_timeline", "task_id", "event_sequence"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_sequence: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("nextval('sv_runtime_event_sequence')"),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_tool_runs.id", ondelete="RESTRICT"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_token: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    initiated_by_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    initiated_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    executed_by_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    executed_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvDecisionEventRecord(Base):
    __tablename__ = "sv_decision_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ("approval_request_id", "approval_request_version"),
            ("sv_approval_requests.id", "sv_approval_requests.request_version"),
            name="fk_sv_decision_events_approval_request",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("task_id", "task_revision"),
            ("sv_task_revisions.task_id", "sv_task_revisions.revision"),
            name="fk_sv_decision_events_task_revision",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "approval_request_id",
            "approval_request_version",
            name="uq_sv_decision_events_request",
        ),
        CheckConstraint("event_sequence >= 1", name="ck_sv_decision_events_sequence"),
        CheckConstraint("task_revision >= 1", name="ck_sv_decision_events_task_revision"),
        CheckConstraint("run_revision >= 1", name="ck_sv_decision_events_run_revision"),
        CheckConstraint(
            "event_type = 'human_decision.recorded.v1'",
            name="ck_sv_decision_events_type",
        ),
        CheckConstraint(
            "decision IN ('approve', 'reject', 'request_evidence', 'stop')",
            name="ck_sv_decision_events_decision",
        ),
        CheckConstraint(
            "decided_by_kind = 'human'",
            name="ck_sv_decision_events_human_actor",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="request_digest"),
            name="ck_sv_decision_events_request_digest",
        ),
        CheckConstraint(
            "octet_length(payload::text) <= 16384",
            name="ck_sv_decision_events_payload_size",
        ),
        CheckConstraint(
            _DIGEST_CHECK.format(column="payload_digest"),
            name="ck_sv_decision_events_payload_digest",
        ),
        UniqueConstraint("event_sequence", name="uq_sv_decision_events_event_sequence"),
        Index("ix_sv_decision_events_timeline", "task_id", "event_sequence"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_sequence: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("nextval('sv_runtime_event_sequence')"),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    approval_request_version: Mapped[int] = mapped_column(Integer, nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_by_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_by_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SvToolJobLinkRecord(Base):
    __tablename__ = "sv_tool_job_links"
    __table_args__ = (
        UniqueConstraint("tool_run_id", name="uq_sv_tool_job_links_tool_run"),
        UniqueConstraint("job_id", name="uq_sv_tool_job_links_job"),
        CheckConstraint(
            _DIGEST_CHECK.format(column="link_digest"),
            name="ck_sv_tool_job_links_digest",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_runs.id", ondelete="RESTRICT"), nullable=False
    )
    tool_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sv_tool_runs.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
    )
    link_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
