from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
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


class ProductSourceRecord(Base):
    __tablename__ = "product_sources"
    __table_args__ = (
        Index(
            "uq_product_sources_schema_org_url",
            "source_url",
            unique=True,
            postgresql_where=text(
                "source_type = 'schema_org_url' AND source_url IS NOT NULL"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))


class ProductSnapshotRecord(Base):
    __tablename__ = "product_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("product_sources.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    images: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    price_currency: Mapped[str | None] = mapped_column(String(3))
    canonical_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductFactRecord(Base):
    __tablename__ = "product_facts"
    __table_args__ = (
        CheckConstraint(
            "evidence_kind IN ('user_assertion', 'source_field')",
            name="ck_product_facts_evidence_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("product_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_locator: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JobRecord(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("job_type", "idempotency_key", name="uq_job_idempotency"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_detail: Mapped[str | None] = mapped_column(Text)
    result_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScriptGenerationRecord(Base):
    __tablename__ = "script_generations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("product_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    selected_fact_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    excluded_fact_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(64), nullable=False)
    pattern_version: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ScriptVersionRecord(Base):
    __tablename__ = "script_versions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    generation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("script_generations.id", ondelete="RESTRICT"), nullable=False
    )
    parent_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("script_versions.id", ondelete="RESTRICT")
    )
    draft: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    validation_report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StoryboardVersionRecord(Base):
    __tablename__ = "storyboard_versions"
    __table_args__ = (
        UniqueConstraint(
            "script_version_id",
            "operation_key",
            name="uq_storyboard_version_operation",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    script_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("script_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    selected_fact_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    excluded_fact_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(64), nullable=False)
    pattern_version: Mapped[str] = mapped_column(String(32), nullable=False)
    phase_sequence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    draft: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    validation_report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preflight_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    storyboard_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StoryboardApprovalEventRecord(Base):
    __tablename__ = "storyboard_approval_events"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_storyboard_approval_event_decision",
        ),
        UniqueConstraint(
            "storyboard_id",
            "operation_key",
            name="uq_storyboard_approval_event_operation",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    storyboard_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("storyboard_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    storyboard_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    preflight_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    event_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
