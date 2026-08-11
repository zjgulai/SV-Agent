from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.jobs.errors import InvalidJobTransition


class JobType(StrEnum):
    PRODUCT_IMPORT = "product_import"
    SCRIPT_GENERATION = "script_generation"


class JobState(StrEnum):
    QUEUED = "queued"
    FETCHING = "fetching"
    PARSING = "parsing"
    GENERATING = "generating"
    VALIDATING = "validating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


TERMINAL_STATES = {JobState.SUCCEEDED, JobState.FAILED, JobState.VALIDATION_FAILED}

_TRANSITIONS: dict[JobType, dict[JobState, set[JobState]]] = {
    JobType.PRODUCT_IMPORT: {
        JobState.QUEUED: {JobState.FETCHING, JobState.FAILED},
        JobState.FETCHING: {JobState.PARSING, JobState.FAILED},
        JobState.PARSING: {JobState.SUCCEEDED, JobState.FAILED},
    },
    JobType.SCRIPT_GENERATION: {
        JobState.QUEUED: {JobState.GENERATING, JobState.FAILED},
        JobState.GENERATING: {JobState.VALIDATING, JobState.FAILED},
        JobState.VALIDATING: {
            JobState.SUCCEEDED,
            JobState.VALIDATION_FAILED,
            JobState.FAILED,
        },
    },
}


@dataclass(frozen=True, slots=True)
class Job:
    id: UUID
    job_type: JobType
    idempotency_key: str
    state: JobState
    input_digest: str
    attempt_count: int
    error_code: str | None
    error_detail: str | None
    result_id: UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def new(
        cls,
        job_type: JobType,
        idempotency_key: str,
        input_digest: str,
        *,
        id: UUID | None = None,
        result_id: UUID | None = None,
    ) -> "Job":
        if len(input_digest) != 64:
            raise ValueError("input_digest must be a SHA-256 hex digest")
        return cls(
            id=id or uuid4(),
            job_type=job_type,
            idempotency_key=idempotency_key,
            state=JobState.QUEUED,
            input_digest=input_digest,
            attempt_count=0,
            error_code=None,
            error_detail=None,
            result_id=result_id,
            created_at=datetime.now(UTC),
            started_at=None,
            finished_at=None,
        )

    def transition_to(
        self,
        state: JobState,
        *,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> "Job":
        if state not in _TRANSITIONS[self.job_type].get(self.state, set()):
            raise InvalidJobTransition(f"{self.job_type}: {self.state} -> {state}")
        now = datetime.now(UTC)
        starts_attempt = self.state is JobState.QUEUED and state not in TERMINAL_STATES
        return replace(
            self,
            state=state,
            attempt_count=self.attempt_count + (1 if starts_attempt else 0),
            started_at=now if starts_attempt else self.started_at,
            finished_at=now if state in TERMINAL_STATES else None,
            error_code=error_code,
            error_detail=error_detail,
        )

    def register_retry(self) -> "Job":
        if self.state in TERMINAL_STATES or self.state is JobState.QUEUED:
            raise InvalidJobTransition(f"cannot retry job in {self.state}")
        return replace(self, attempt_count=self.attempt_count + 1)
