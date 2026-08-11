from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.jobs.entities import JobState, JobType
from app.domain.scripts.models import ScriptDraft, ValidationReport


class ScriptGenerationInput(BaseModel):
    target_duration_seconds: int = Field(ge=5, le=120)
    language: str = Field(min_length=2, max_length=16)
    audience: str = Field(min_length=1, max_length=500)
    creative_pattern_key: str = Field(min_length=1, max_length=64)


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
