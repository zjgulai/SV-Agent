from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.products.promotion import PromotionRender
from app.domain.scripts.models import ScriptDraft
from app.domain.scripts.patterns import CompiledPatternDefinition


class SupportedFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    claim: str
    claim_type: str


class ScriptGenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID
    title: str
    facts: list[SupportedFact] = Field(min_length=1)
    excluded_facts: list[SupportedFact] = Field(default_factory=list)
    target_duration_seconds: int = Field(gt=0)
    language: str
    audience: str
    pattern_definition: CompiledPatternDefinition
    promotion: PromotionRender | None = None


class ProviderError(Exception):
    code = "PROVIDER_ERROR"

    def __init__(self, message: str, *, attempt_count: int = 1) -> None:
        super().__init__(message)
        self.attempt_count = attempt_count


class ProviderRateLimited(ProviderError):
    code = "PROVIDER_RATE_LIMITED"


class ProviderUnavailable(ProviderError):
    code = "PROVIDER_UNAVAILABLE"


class ProviderOutputInvalid(ProviderError):
    code = "PROVIDER_OUTPUT_INVALID"


class ScriptProvider(Protocol):
    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft: ...
