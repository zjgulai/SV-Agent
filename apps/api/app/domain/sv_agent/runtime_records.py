from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import UUID

from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.errors import (
    EventDigestMismatch,
    EventSchemaUnsupported,
    JournalIntegrityError,
)

MAX_EVENT_PAYLOAD_BYTES = 16 * 1024
MAX_ARTIFACT_PAYLOAD_BYTES = 256 * 1024

_PRIVATE_EVENT_FIELDS = frozenset(
    {
        "absolute_path",
        "chain_of_thought",
        "cookie",
        "credential",
        "credentials",
        "private_reasoning",
        "private_url",
        "raw_media",
        "reasoning",
    }
)


class EventStream(StrEnum):
    TASK = "task"
    TOOL_RUN = "tool_run"
    DECISION = "decision"


class TaskEventType(StrEnum):
    TASK_CREATED = "task.created.v1"
    TASK_REVISED = "task.revised.v1"
    RUN_CREATED = "run.created.v1"
    RUN_STATE_TRANSITIONED = "run.state_transitioned.v1"
    REPLICATION_AXIS_SELECTED = "run.replication_axis_selected.v1"
    RUN_PLAN_RECORDED = "run.plan_recorded.v1"
    ARTIFACT_RECORDED = "artifact.recorded.v1"
    RUNTIME_LINEAGE_VERIFIED = "runtime_lineage.verified.v1"
    APPROVAL_REQUESTED = "approval.requested.v1"


class ToolRunEventType(StrEnum):
    CREATED = "tool_run.created.v1"
    STARTED = "tool_run.started.v1"
    COMPLETED = "tool_run.completed.v1"
    FAILED = "tool_run.failed.v1"
    UNAVAILABLE = "tool_run.unavailable.v1"
    EFFECT_UNKNOWN = "tool_run.effect_unknown.v1"
    TECHNICAL_JOB_LINKED = "tool_run.technical_job_linked.v1"


class DecisionEventType(StrEnum):
    HUMAN_DECISION_RECORDED = "human_decision.recorded.v1"


class ToolRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class EffectClass(StrEnum):
    READ = "read"
    WRITE = "write"


class ArtifactType(StrEnum):
    REFERENCE_BUNDLE = "reference_bundle"
    DECOMPOSITION_MAP = "decomposition_map"
    PATTERN_HYPOTHESIS = "pattern_hypothesis"
    REPLICATION_PLAN = "replication_plan"
    FACT_MAP = "fact_map"
    REPLICATION_CONTRACT = "replication_contract"
    ADAPTATION_PACKAGE = "adaptation_package"
    MEDIA_INTEGRITY_RECORD = "media_integrity_record"
    REPLICATION_FINDING = "replication_finding"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    APPROVED = "approved"
    STALE = "stale"
    SUPERSEDED = "superseded"
    FINAL_WITH_LIMITS = "final_with_limits"


class EvidenceLevel(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"
    UNKNOWN = "unknown"


class ProofLevel(StrEnum):
    LOCAL = "local"
    CI = "ci"
    PRIVATE = "private"
    DEPLOYMENT = "deployment"
    LIVE = "live"
    PRODUCTION = "production"


class ApprovalGateKind(StrEnum):
    FACT = "fact"
    REPLICATION_CONTRACT = "replication_contract"
    STORYBOARD = "storyboard"
    REFERENCE_RIGHTS = "reference_rights"
    CHILD_SAFETY = "child_safety"
    MEDIA_INTEGRITY = "media_integrity"
    SOURCE_USE = "source_use"
    ORIGINALITY = "originality"
    LEGAL = "legal"
    COMMERCIAL = "commercial"
    PLATFORM = "platform"
    DEPLOYMENT = "deployment"
    PRODUCTION = "production"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_EVIDENCE = "request_evidence"
    STOP = "stop"


class ActorKind(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"
    OPERATOR = "operator"


@dataclass(frozen=True, slots=True)
class ActorStamp:
    kind: ActorKind
    ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ActorKind):
            raise TypeError("actor_kind_invalid")
        if not self.ref or self.ref != self.ref.strip() or len(self.ref) > 255:
            raise ValueError("actor_ref_invalid")


def _find_private_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in _PRIVATE_EVENT_FIELDS:
                return normalized_key
            nested = _find_private_field(item)
            if nested is not None:
                return nested
    elif isinstance(value, list | tuple):
        for item in value:
            nested = _find_private_field(item)
            if nested is not None:
                return nested
    return None


def validate_event_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    private_field = _find_private_field(normalized)
    if private_field is not None:
        raise JournalIntegrityError(f"private_event_field:{private_field}")
    try:
        serialized = json.dumps(
            normalized,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("event_payload_not_json") from exc
    if len(serialized) > MAX_EVENT_PAYLOAD_BYTES:
        raise JournalIntegrityError("event_payload_too_large")
    return normalized


EventType = TaskEventType | ToolRunEventType | DecisionEventType


@dataclass(frozen=True, slots=True)
class ReplayEntry:
    event_id: UUID
    event_sequence: int
    stream: EventStream
    event_type: EventType
    task_id: UUID
    run_id: UUID | None
    task_revision: int
    run_revision: int | None
    payload: Mapping[str, Any]
    payload_digest: str

    def __post_init__(self) -> None:
        if self.event_sequence < 1 or self.task_revision < 1:
            raise JournalIntegrityError("event_revision_invalid")
        if (self.run_id is None) != (self.run_revision is None):
            raise JournalIntegrityError("event_run_ref_incomplete")
        if self.run_revision is not None and self.run_revision < 1:
            raise JournalIntegrityError("event_run_revision_invalid")
        expected_type = {
            EventStream.TASK: TaskEventType,
            EventStream.TOOL_RUN: ToolRunEventType,
            EventStream.DECISION: DecisionEventType,
        }[self.stream]
        if not isinstance(self.event_type, expected_type):
            raise EventSchemaUnsupported("event_stream_type_mismatch")
        normalized = validate_event_payload(self.payload)
        if canonical_digest(normalized) != self.payload_digest:
            raise EventDigestMismatch("event_payload_digest_mismatch")
        object.__setattr__(self, "payload", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class ReplayQuery:
    task_id: UUID
    after_sequence: int | None = None
    through_sequence: int | None = None
    limit: int = 100

    def __post_init__(self) -> None:
        if self.after_sequence is not None and self.after_sequence < 0:
            raise ValueError("replay_query_invalid")
        if self.through_sequence is not None and self.through_sequence < 1:
            raise ValueError("replay_query_invalid")
        if (
            self.after_sequence is not None
            and self.through_sequence is not None
            and self.after_sequence >= self.through_sequence
        ):
            raise ValueError("replay_query_invalid")
        if not 1 <= self.limit <= 200:
            raise ValueError("replay_query_invalid")


@dataclass(frozen=True, slots=True)
class ReplayPage:
    task_id: UUID
    entries: tuple[ReplayEntry, ...]
    snapshot_through_sequence: int
    snapshot_event_count: int
    next_after_sequence: int | None
    integrity: str = "verified"

    def __post_init__(self) -> None:
        if (
            self.snapshot_through_sequence < 0
            or self.snapshot_event_count < 0
            or self.integrity != "verified"
        ):
            raise JournalIntegrityError("replay_page_invalid")
        if any(entry.task_id != self.task_id for entry in self.entries):
            raise JournalIntegrityError("replay_task_scope_mismatch")
        sequences = tuple(entry.event_sequence for entry in self.entries)
        if sequences != tuple(sorted(sequences)) or len(sequences) != len(set(sequences)):
            raise JournalIntegrityError("replay_sequence_invalid")
