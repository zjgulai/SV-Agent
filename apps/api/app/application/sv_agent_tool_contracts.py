from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.application.creative_comparison_lab import CreativeComparisonProjection
from app.domain.jobs.entities import JobState, JobType
from app.domain.products.entities import FactStatus
from app.domain.scripts.audience import AudienceProfileKey
from app.domain.scripts.models import ScriptDraft, ValidationReport
from app.domain.scripts.patterns import CompiledPatternDefinition, PatternLanguage
from app.domain.scripts.storyboard import StoryboardPreflight, StoryboardPreview


class ReadToolName(StrEnum):
    PRODUCT_TRUTH = "product_truth.inspect"
    PATTERN_CONTRACT = "pattern_contract.inspect"
    JOB = "job.inspect"
    SCRIPT = "script.inspect"
    STORYBOARD = "storyboard.inspect"
    CREATIVE_COMPARISON = "creative_comparison.inspect"


class ReadResultState(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class StrictToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadResult[T](StrictToolModel):
    state: ReadResultState
    value: T | None = None
    negative_evidence_code: str | None = Field(default=None, min_length=1, max_length=64)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_shape(self) -> ReadResult[T]:
        if self.state is ReadResultState.FOUND:
            if (
                self.value is None
                or self.negative_evidence_code is not None
                or self.subject_ref is not None
            ):
                raise ValueError("found_result_shape_invalid")
        elif (
            self.value is not None
            or self.negative_evidence_code is None
            or self.subject_ref is None
        ):
            raise ValueError("not_found_result_shape_invalid")
        return self

    @classmethod
    def found(cls, value: T) -> ReadResult[T]:
        return cls(state=ReadResultState.FOUND, value=value)

    @classmethod
    def not_found(cls, code: str, *, subject_ref: str) -> ReadResult[T]:
        return cls(
            state=ReadResultState.NOT_FOUND,
            value=None,
            negative_evidence_code=code,
            subject_ref=subject_ref,
        )


class ProductTruthReadInput(StrictToolModel):
    tool: Literal[ReadToolName.PRODUCT_TRUTH] = ReadToolName.PRODUCT_TRUTH
    product_id: UUID


class PatternContractReadInput(StrictToolModel):
    tool: Literal[ReadToolName.PATTERN_CONTRACT] = ReadToolName.PATTERN_CONTRACT
    pattern_key: str = Field(min_length=1, max_length=64)
    pattern_version: str = Field(min_length=1, max_length=32)
    duration_seconds: int = Field(ge=5, le=120)
    language: PatternLanguage
    audience_profile_key: AudienceProfileKey = "general"


class JobReadInput(StrictToolModel):
    tool: Literal[ReadToolName.JOB] = ReadToolName.JOB
    job_id: UUID
    include_events: bool = True
    include_import_attempts: bool = False
    event_limit: int = Field(default=100, ge=1, le=200)
    import_attempt_limit: int = Field(default=100, ge=1, le=200)


class ScriptInspectQuery(StrictToolModel):
    action: Literal["inspect"] = "inspect"
    script_id: UUID
    version_limit: int = Field(default=100, ge=1, le=200)


class ScriptVersionQuery(StrictToolModel):
    action: Literal["version"] = "version"
    script_id: UUID
    version_id: UUID


class ScriptDiffQuery(StrictToolModel):
    action: Literal["diff"] = "diff"
    script_id: UUID
    left_version_id: UUID
    right_version_id: UUID


class ScriptExportQuery(StrictToolModel):
    action: Literal["export"] = "export"
    script_id: UUID
    version_id: UUID
    format: Literal["json", "markdown"] = "json"


type ScriptReadQuery = Annotated[
    ScriptInspectQuery | ScriptVersionQuery | ScriptDiffQuery | ScriptExportQuery,
    Field(discriminator="action"),
]


class ScriptReadInput(StrictToolModel):
    tool: Literal[ReadToolName.SCRIPT] = ReadToolName.SCRIPT
    query: ScriptReadQuery


class StoryboardPreflightQuery(StrictToolModel):
    action: Literal["preflight"] = "preflight"
    script_id: UUID
    version_id: UUID


class StoryboardPreviewQuery(StrictToolModel):
    action: Literal["preview"] = "preview"
    storyboard_id: UUID


class StoryboardApprovalStateQuery(StrictToolModel):
    action: Literal["approval_state"] = "approval_state"
    storyboard_id: UUID


type StoryboardReadQuery = Annotated[
    StoryboardPreflightQuery | StoryboardPreviewQuery | StoryboardApprovalStateQuery,
    Field(discriminator="action"),
]


class StoryboardReadInput(StrictToolModel):
    tool: Literal[ReadToolName.STORYBOARD] = ReadToolName.STORYBOARD
    query: StoryboardReadQuery


class CreativeComparisonReadInput(StrictToolModel):
    tool: Literal[ReadToolName.CREATIVE_COMPARISON] = ReadToolName.CREATIVE_COMPARISON
    script_id: UUID
    control_version_id: UUID
    variant_version_id: UUID

    @model_validator(mode="after")
    def require_distinct_versions(self) -> CreativeComparisonReadInput:
        if self.control_version_id == self.variant_version_id:
            raise ValueError("comparison_versions_must_differ")
        return self


type ReadToolInput = Annotated[
    ProductTruthReadInput
    | PatternContractReadInput
    | JobReadInput
    | ScriptReadInput
    | StoryboardReadInput
    | CreativeComparisonReadInput,
    Field(discriminator="tool"),
]


class ProductSnapshotProjection(StrictToolModel):
    id: UUID
    source_id: UUID
    title: str
    description: str | None
    category_path: tuple[str, ...]
    images: tuple[str, ...]
    price_amount: Decimal | None
    price_currency: str | None
    canonical_digest: str
    created_at: datetime


class ProductFactProjection(StrictToolModel):
    id: UUID
    snapshot_id: UUID
    claim_type: str
    claim: str
    evidence_kind: str
    evidence_locator: str
    evidence_excerpt: str
    confidence: Decimal
    status: FactStatus
    updated_at: datetime


class ProductTruthProjection(StrictToolModel):
    product_id: UUID
    snapshot: ProductSnapshotProjection
    facts: tuple[ProductFactProjection, ...]


class ProductTruthReadOutput(StrictToolModel):
    tool: Literal[ReadToolName.PRODUCT_TRUTH] = ReadToolName.PRODUCT_TRUTH
    result: ReadResult[ProductTruthProjection]

    @classmethod
    def not_found(cls, *, product_id: UUID, code: str) -> ProductTruthReadOutput:
        return cls(
            result=ReadResult[ProductTruthProjection].not_found(
                code,
                subject_ref=str(product_id),
            )
        )


class PatternContractReadOutput(StrictToolModel):
    tool: Literal[ReadToolName.PATTERN_CONTRACT] = ReadToolName.PATTERN_CONTRACT
    result: ReadResult[CompiledPatternDefinition]


class JobProjection(StrictToolModel):
    id: UUID
    job_type: JobType
    state: JobState
    attempt_count: int
    error_code: str | None
    result_id: UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobEventProjection(StrictToolModel):
    id: UUID
    event_type: str
    from_state: JobState | None
    to_state: JobState
    attempt_count: int
    error_code: str | None
    event_sequence: int
    created_at: datetime


class ImportAttemptProjection(StrictToolModel):
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


class JobInspectionProjection(StrictToolModel):
    job: JobProjection
    events: tuple[JobEventProjection, ...]
    import_attempts: tuple[ImportAttemptProjection, ...]


class JobReadOutput(StrictToolModel):
    tool: Literal[ReadToolName.JOB] = ReadToolName.JOB
    result: ReadResult[JobInspectionProjection]


class ScriptGenerationProjection(StrictToolModel):
    id: UUID
    snapshot_id: UUID
    selected_fact_ids: tuple[UUID, ...]
    excluded_fact_ids: tuple[UUID, ...]
    target_duration_seconds: int
    language: str
    audience_profile_key: str
    pattern_key: str
    pattern_version: str
    provider: str
    model: str
    prompt_contract_version: str
    input_digest: str
    created_at: datetime


class ScriptVersionProjection(StrictToolModel):
    id: UUID
    generation_id: UUID
    parent_version_id: UUID | None
    draft: ScriptDraft
    validation_report: ValidationReport
    revision_kind: str | None
    actor_kind: str | None
    reason_code: str | None
    operation_input_digest: str | None
    created_at: datetime


class ScriptFactProjection(StrictToolModel):
    id: UUID
    snapshot_id: UUID
    claim: str
    status: FactStatus


class ScriptProjection(StrictToolModel):
    generation: ScriptGenerationProjection
    versions: tuple[ScriptVersionProjection, ...]
    selected_facts: tuple[ScriptFactProjection, ...]
    excluded_facts: tuple[ScriptFactProjection, ...]


class ScriptDiffEntry(StrictToolModel):
    path: str
    value: Any | None = None
    left: Any | None = None
    right: Any | None = None


class ScriptDiffProjection(StrictToolModel):
    script_id: UUID
    left_version_id: UUID
    right_version_id: UUID
    added: tuple[ScriptDiffEntry, ...]
    removed: tuple[ScriptDiffEntry, ...]
    changed: tuple[ScriptDiffEntry, ...]


class ScriptExportProjection(StrictToolModel):
    script_id: UUID
    version_id: UUID
    format: Literal["json", "markdown"]
    media_type: Literal["application/json", "text/markdown"]
    content: str


type ScriptReadValue = (
    ScriptProjection | ScriptVersionProjection | ScriptDiffProjection | ScriptExportProjection
)


class ScriptReadOutput(StrictToolModel):
    tool: Literal[ReadToolName.SCRIPT] = ReadToolName.SCRIPT
    action: Literal["inspect", "version", "diff", "export"]
    result: ReadResult[ScriptReadValue]

    @model_validator(mode="after")
    def require_action_result_match(self) -> ScriptReadOutput:
        if self.result.state is ReadResultState.NOT_FOUND:
            return self
        expected = {
            "inspect": ScriptProjection,
            "version": ScriptVersionProjection,
            "diff": ScriptDiffProjection,
            "export": ScriptExportProjection,
        }[self.action]
        if not isinstance(self.result.value, expected):
            raise ValueError("script_action_result_mismatch")  # noqa: TRY004
        return self


class StoryboardApprovalEventProjection(StrictToolModel):
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


class StoryboardApprovalStateProjection(StrictToolModel):
    storyboard_id: UUID
    status: Literal["unreviewed", "approved", "rejected", "stale"]
    latest_event: StoryboardApprovalEventProjection | None


type StoryboardReadValue = (
    StoryboardPreflight | StoryboardPreview | StoryboardApprovalStateProjection
)


class StoryboardReadOutput(StrictToolModel):
    tool: Literal[ReadToolName.STORYBOARD] = ReadToolName.STORYBOARD
    action: Literal["preflight", "preview", "approval_state"]
    result: ReadResult[StoryboardReadValue]

    @model_validator(mode="after")
    def require_action_result_match(self) -> StoryboardReadOutput:
        if self.result.state is ReadResultState.NOT_FOUND:
            return self
        expected = {
            "preflight": StoryboardPreflight,
            "preview": StoryboardPreview,
            "approval_state": StoryboardApprovalStateProjection,
        }[self.action]
        if not isinstance(self.result.value, expected):
            raise ValueError("storyboard_action_result_mismatch")  # noqa: TRY004
        return self


class CreativeComparisonReadOutput(StrictToolModel):
    tool: Literal[ReadToolName.CREATIVE_COMPARISON] = ReadToolName.CREATIVE_COMPARISON
    result: ReadResult[CreativeComparisonProjection]


type ReadToolOutput = Annotated[
    ProductTruthReadOutput
    | PatternContractReadOutput
    | JobReadOutput
    | ScriptReadOutput
    | StoryboardReadOutput
    | CreativeComparisonReadOutput,
    Field(discriminator="tool"),
]
