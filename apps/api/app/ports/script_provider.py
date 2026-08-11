from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.scripts.models import ScriptDraft


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
    target_duration_seconds: int = Field(gt=0)
    language: str
    audience: str
    creative_pattern_key: str
    creative_pattern_version: str
    hook_type: str
    phase_sequence: tuple[str, ...] = Field(min_length=1)
    shot_roles: tuple[str, ...] = Field(min_length=1)


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
