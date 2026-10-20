from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.sv_agent.runtime_records import EffectClass, ToolRunStatus

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_text(value: str, *, field: str, maximum: int) -> str:
    if not value or value != value.strip() or len(value) > maximum:
        raise ValueError(f"{field}_invalid")
    return value


def _require_digest(value: str, *, field: str) -> str:
    if _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field}_invalid")
    return value


@dataclass(frozen=True, slots=True)
class ToolArtifactRef:
    artifact_type: str
    artifact_id: str
    artifact_version: int
    artifact_digest: str

    def __post_init__(self) -> None:
        _require_text(self.artifact_type, field="artifact_type", maximum=64)
        _require_text(self.artifact_id, field="artifact_id", maximum=255)
        if self.artifact_version < 1:
            raise ValueError("artifact_version_invalid")
        _require_digest(self.artifact_digest, field="artifact_digest")

    def as_payload(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "artifact_digest": self.artifact_digest,
        }


@dataclass(frozen=True, slots=True)
class ToolRun:
    id: UUID
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    revision: int
    tool_name: str
    tool_version: str
    intent_summary: str
    input_digest: str
    effect_class: EffectClass
    approval_request_id: UUID | None
    approval_request_version: int | None
    idempotency_key: str | None
    attempt_token: int
    status: ToolRunStatus
    artifact_refs: tuple[ToolArtifactRef, ...]
    stable_error_code: str | None
    recovery_action: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.task_revision < 1 or self.run_revision < 1 or self.revision < 1:
            raise ValueError("tool_run_revision_invalid")
        if self.attempt_token < 1:
            raise ValueError("attempt_token_invalid")
        _require_text(self.tool_name, field="tool_name", maximum=128)
        _require_text(self.tool_version, field="tool_version", maximum=64)
        _require_text(self.intent_summary, field="intent_summary", maximum=1000)
        _require_digest(self.input_digest, field="input_digest")
        if self.effect_class is EffectClass.READ:
            if self.approval_request_id is not None or self.approval_request_version is not None:
                raise ValueError("read_tool_approval_ref_invalid")
        elif self.approval_request_id is None or self.approval_request_version is None:
            raise ValueError("write_tool_approval_ref_required")
        if (self.approval_request_id is None) != (self.approval_request_version is None):
            raise ValueError("approval_ref_incomplete")
        if self.idempotency_key is not None:
            _require_text(self.idempotency_key, field="idempotency_key", maximum=255)
        if self.updated_at < self.created_at:
            raise ValueError("tool_run_time_invalid")
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("tool_run_time_invalid")
        if self.finished_at is not None and (
            self.started_at is None or self.finished_at < self.started_at
        ):
            raise ValueError("tool_run_time_invalid")
        self._validate_state_shape()

    @classmethod
    def new(
        cls,
        *,
        task_id: UUID,
        task_revision: int,
        run_id: UUID,
        run_revision: int,
        tool_name: str,
        tool_version: str,
        intent_summary: str,
        input_digest: str,
        id: UUID | None = None,
        idempotency_key: str | None = None,
        created_at: datetime | None = None,
    ) -> ToolRun:
        now = created_at or datetime.now(UTC)
        return cls(
            id=id or uuid4(),
            task_id=task_id,
            task_revision=task_revision,
            run_id=run_id,
            run_revision=run_revision,
            revision=1,
            tool_name=tool_name,
            tool_version=tool_version,
            intent_summary=intent_summary,
            input_digest=input_digest,
            effect_class=EffectClass.READ,
            approval_request_id=None,
            approval_request_version=None,
            idempotency_key=idempotency_key,
            attempt_token=1,
            status=ToolRunStatus.PENDING,
            artifact_refs=(),
            stable_error_code=None,
            recovery_action=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )

    def start(self, *, at: datetime | None = None) -> ToolRun:
        self._require_status(ToolRunStatus.PENDING)
        now = at or datetime.now(UTC)
        return replace(
            self,
            revision=self.revision + 1,
            status=ToolRunStatus.RUNNING,
            started_at=now,
            updated_at=now,
        )

    def complete(
        self,
        *,
        artifact_refs: tuple[ToolArtifactRef, ...] = (),
        at: datetime | None = None,
    ) -> ToolRun:
        return self._finish(
            status=ToolRunStatus.COMPLETED,
            artifact_refs=artifact_refs,
            stable_error_code=None,
            recovery_action=None,
            at=at,
        )

    def failed(
        self,
        *,
        stable_error_code: str,
        recovery_action: str,
        at: datetime | None = None,
    ) -> ToolRun:
        return self._finish(
            status=ToolRunStatus.FAILED,
            artifact_refs=(),
            stable_error_code=stable_error_code,
            recovery_action=recovery_action,
            at=at,
        )

    def unavailable(
        self,
        *,
        stable_error_code: str,
        recovery_action: str,
        at: datetime | None = None,
    ) -> ToolRun:
        return self._finish(
            status=ToolRunStatus.UNAVAILABLE,
            artifact_refs=(),
            stable_error_code=stable_error_code,
            recovery_action=recovery_action,
            at=at,
        )

    def _finish(
        self,
        *,
        status: ToolRunStatus,
        artifact_refs: tuple[ToolArtifactRef, ...],
        stable_error_code: str | None,
        recovery_action: str | None,
        at: datetime | None,
    ) -> ToolRun:
        self._require_status(ToolRunStatus.RUNNING)
        if status in {ToolRunStatus.FAILED, ToolRunStatus.UNAVAILABLE}:
            _require_text(
                stable_error_code or "",
                field="stable_error_code",
                maximum=64,
            )
            _require_text(
                recovery_action or "",
                field="recovery_action",
                maximum=1000,
            )
        now = at or datetime.now(UTC)
        return replace(
            self,
            revision=self.revision + 1,
            status=status,
            artifact_refs=artifact_refs,
            stable_error_code=stable_error_code,
            recovery_action=recovery_action,
            finished_at=now,
            updated_at=now,
        )

    def _require_status(self, expected: ToolRunStatus) -> None:
        if self.status is not expected:
            raise ValueError(f"tool_run_transition_invalid:{self.status.value}->{expected.value}")

    def _validate_state_shape(self) -> None:
        if self.status is ToolRunStatus.PENDING:
            if self.revision != 1:
                raise ValueError("tool_run_revision_status_invalid")
            if self.started_at is not None or self.finished_at is not None:
                raise ValueError("pending_tool_run_time_invalid")
        elif self.status is ToolRunStatus.RUNNING:
            if self.revision != 2:
                raise ValueError("tool_run_revision_status_invalid")
            if self.started_at is None or self.finished_at is not None:
                raise ValueError("running_tool_run_time_invalid")
        else:
            if self.revision != 3:
                raise ValueError("tool_run_revision_status_invalid")
            if self.started_at is None or self.finished_at is None:
                raise ValueError("terminal_tool_run_time_invalid")
        if self.status in {ToolRunStatus.FAILED, ToolRunStatus.UNAVAILABLE}:
            _require_text(
                self.stable_error_code or "",
                field="stable_error_code",
                maximum=64,
            )
            _require_text(
                self.recovery_action or "",
                field="recovery_action",
                maximum=1000,
            )
        elif self.stable_error_code is not None or self.recovery_action is not None:
            raise ValueError("successful_tool_run_error_invalid")
