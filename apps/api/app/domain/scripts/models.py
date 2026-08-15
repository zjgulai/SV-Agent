from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.products.promotion import PromotionRender


class ScriptPhase(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    purpose: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)


class ScriptShot(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    phase_key: str
    role: str | None = None
    voiceover: str
    visual: str
    action: str
    caption: str
    acceptance_shot: str
    supported_fact_ids: list[UUID]
    product_claims: list[str] = Field(default_factory=list)
    promotion: PromotionRender | None = None


class ScriptDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_duration_seconds: int = Field(gt=0)
    language: str
    audience: str
    snapshot_id: UUID | None = None
    phases: list[ScriptPhase]
    shots: list[ScriptShot]
    titles: list[str]
    tags: list[str]
    shooting_list: list[str]


class FindingSeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"


class ValidationFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    path: str
    message: str
    severity: FindingSeverity = FindingSeverity.BLOCKING
    evidence: str | None = None


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    findings: list[ValidationFinding]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def blocking(self) -> list[ValidationFinding]:
        return [item for item in self.findings if item.severity is FindingSeverity.BLOCKING]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def acceptable(self) -> bool:
        return not self.blocking
