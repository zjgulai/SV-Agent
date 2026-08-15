from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.jobs.entities import JobState, JobType
from app.domain.products.entities import FactStatus
from app.domain.scripts.audience import AudienceProfileKey
from app.domain.scripts.models import ScriptDraft, ValidationReport


class ScriptGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_duration_seconds: int = Field(ge=5, le=120)
    language: str = Field(min_length=2, max_length=16)
    audience: AudienceProfileKey
    creative_pattern_key: str = Field(min_length=1, max_length=64)
    selected_fact_ids: list[UUID]
    excluded_fact_ids: list[UUID] = Field(default_factory=list)
    promotion_fact_id: UUID | None = None


class FactBindingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    shot_index: int = Field(ge=0)
    fact_id: UUID


class DeriveVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_bindings: list[FactBindingInput] = Field(min_length=1)


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


class JobEventOutput(BaseModel):
    id: UUID
    event_type: str
    from_state: JobState | None
    to_state: JobState
    attempt_count: int
    error_code: str | None
    error_detail: str | None
    event_sequence: int
    created_at: datetime


class ImportAttemptOutput(BaseModel):
    id: UUID
    job_id: UUID
    source_id: UUID
    attempt_token: int
    stage: Literal["started", "parsed", "succeeded", "failed"]
    source_url_digest: str
    resolution_digest: str | None
    response_digest: str | None
    snapshot_id: UUID | None
    error_code: str | None
    attempt_sequence: int
    created_at: datetime


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
    revision_kind: Literal["fact_rebind"] | None
    actor_kind: Literal["local_operator"] | None
    reason_code: Literal["fact_rebind"] | None
    operation_input_digest: str | None
    created_at: datetime


class ScriptFactContractItem(BaseModel):
    id: UUID
    claim: str
    status: FactStatus
    snapshot_id: UUID


class ScriptFactContractOutput(BaseModel):
    selected: list[ScriptFactContractItem]
    excluded: list[ScriptFactContractItem]


class ScriptOutput(BaseModel):
    generation: ScriptGenerationOutput
    versions: list[ScriptVersionOutput]
    fact_contract: ScriptFactContractOutput


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
