from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.jobs.entities import JobState, JobType
from app.domain.scripts.models import ScriptDraft, ValidationReport


class ScriptGenerationInput(BaseModel):
    target_duration_seconds: int = Field(ge=5, le=120)
    language: str = Field(min_length=2, max_length=16)
    audience: str = Field(min_length=1, max_length=500)
    creative_pattern_key: str = Field(min_length=1, max_length=64)
    selected_fact_ids: list[UUID]
    excluded_fact_ids: list[UUID] = Field(default_factory=list)


class DeriveVersionInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class JobOutput(BaseModel):
    id: UUID
    job_type: JobType
    state: JobState
    attempt_count: int
    error_code: str | None
    error_detail: str | None
    result_id: UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ScriptGenerationOutput(BaseModel):
    id: UUID
    snapshot_id: UUID
    selected_fact_ids: list[UUID]
    excluded_fact_ids: list[UUID]
    configuration: dict[str, Any]
    pattern_key: str
    pattern_version: str
    provider: str
    model: str
    prompt_contract_version: str
    input_digest: str
    created_at: datetime


class ScriptVersionOutput(BaseModel):
    id: UUID
    generation_id: UUID
    parent_version_id: UUID | None
    draft: ScriptDraft
    validation_report: ValidationReport
    created_at: datetime


class ScriptOutput(BaseModel):
    generation: ScriptGenerationOutput
    versions: list[ScriptVersionOutput]


class VersionDiffOutput(BaseModel):
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]


class StoryboardVersionOutput(BaseModel):
    id: UUID
    script_version_id: UUID
    snapshot_id: UUID
    selected_fact_ids: list[UUID]
    excluded_fact_ids: list[UUID]
    pattern_key: str
    pattern_version: str
    phase_sequence: list[str]
    draft: ScriptDraft
    validation_report: ValidationReport
    preflight_digest: str
    storyboard_digest: str
    preview_contract_version: str
    created_at: datetime


class StoryboardApprovalInput(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class StoryboardApprovalEventOutput(BaseModel):
    id: UUID
    storyboard_id: UUID
    decision: Literal["approved", "rejected"]
    reason: str | None
    storyboard_digest: str
    preflight_digest: str
    approval_digest: str
    validation_report: ValidationReport
    event_sequence: int
    created_at: datetime


class StoryboardApprovalOutput(BaseModel):
    status: Literal["unreviewed", "approved", "rejected", "stale"]
    latest_event: StoryboardApprovalEventOutput | None
