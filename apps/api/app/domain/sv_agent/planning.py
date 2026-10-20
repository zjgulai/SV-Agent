from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    CreativeDimension,
    PrimaryMechanism,
    dimensions_for_mechanism,
)
from app.domain.sv_agent.errors import InvalidRunPlan
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ApprovalDecision,
    ApprovalGateKind,
    ArtifactType,
)

MAX_RUN_PLAN_PAYLOAD_BYTES = 256 * 1024


def _is_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _require_text(value: str, code: str) -> None:
    if not value or value != value.strip():
        raise InvalidRunPlan(code)


def _require_digest(value: str, code: str) -> None:
    if not _is_digest(value):
        raise InvalidRunPlan(code)


def _require_uuid(value: UUID, code: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidRunPlan(code)


def _require_axis(
    primary_mechanism: PrimaryMechanism,
    creative_dimension: CreativeDimension,
) -> None:
    if not isinstance(primary_mechanism, PrimaryMechanism) or not isinstance(
        creative_dimension, CreativeDimension
    ):
        raise InvalidRunPlan("run_plan_axis_invalid")
    if creative_dimension not in dimensions_for_mechanism(primary_mechanism):
        raise InvalidRunPlan("run_plan_axis_invalid")


class PlanInputKind(StrEnum):
    TASK_BRIEF = "task_brief"
    ROUTE_EVIDENCE = "route_evidence"
    FACT_SCOPE_EVIDENCE = "fact_scope_evidence"
    CATALOG = "catalog"


class FactScope(StrEnum):
    PRODUCT_CLAIMS = "product_claims"
    NO_PRODUCT_CLAIMS = "no_product_claims"


class FactScopeState(StrEnum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    STALE = "stale"
    BLOCKED = "blocked"


class FactSubjectBinding(StrEnum):
    PRODUCT = "product"
    NOT_APPLICABLE = "not_applicable"


class MediaMode(StrEnum):
    ANALYSIS_ONLY = "analysis_only"
    CONTROLLED_MEDIA = "controlled_media"


class CapabilityExecutionMode(StrEnum):
    PLANNING_ONLY = "planning_only"


class ApprovalAuthority(StrEnum):
    UNVERIFIED_ATTRIBUTION = "unverified_attribution"
    VERIFIED_HUMAN = "verified_human"


class OrchestrationDisposition(StrEnum):
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_INPUT = "awaiting_input"
    READY = "ready"
    PLAN_COMPLETE = "plan_complete"


@dataclass(frozen=True, slots=True)
class PlanInputRef:
    kind: PlanInputKind
    ref: str
    version: int
    digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PlanInputKind):
            raise InvalidRunPlan("plan_input_ref_invalid")
        _require_text(self.ref, "plan_input_ref_invalid")
        if self.version < 1:
            raise InvalidRunPlan("plan_input_ref_invalid")
        _require_digest(self.digest, "plan_input_ref_invalid")


@dataclass(frozen=True, slots=True)
class ArtifactHandle:
    artifact_type: ArtifactType
    artifact_id: str
    version: int
    digest: str
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    lineage_verified: bool

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_type, ArtifactType):
            raise InvalidRunPlan("artifact_handle_invalid")
        _require_text(self.artifact_id, "artifact_handle_invalid")
        _require_uuid(self.task_id, "artifact_handle_invalid")
        _require_uuid(self.run_id, "artifact_handle_invalid")
        if self.version < 1 or self.task_revision < 1 or self.run_revision < 1:
            raise InvalidRunPlan("artifact_handle_invalid")
        _require_digest(self.digest, "artifact_handle_invalid")
        if not isinstance(self.lineage_verified, bool):
            raise InvalidRunPlan("artifact_handle_invalid")

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.artifact_type,
            self.artifact_id,
            self.version,
            self.task_id,
            self.task_revision,
            self.run_id,
            self.run_revision,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type.value,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "digest": self.digest,
            "task_id": str(self.task_id),
            "task_revision": self.task_revision,
            "run_id": str(self.run_id),
            "run_revision": self.run_revision,
            "lineage_verified": self.lineage_verified,
        }


@dataclass(frozen=True, slots=True)
class FactScopeEvidence:
    scope: FactScope
    ref: str
    version: int
    digest: str
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    lineage_verified: bool
    subject_binding: FactSubjectBinding
    claim_mapping_count: int
    eligible_fact_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.scope, FactScope):
            raise InvalidRunPlan("fact_scope_evidence_invalid")
        _require_text(self.ref, "fact_scope_evidence_invalid")
        _require_uuid(self.task_id, "fact_scope_evidence_invalid")
        _require_uuid(self.run_id, "fact_scope_evidence_invalid")
        if self.version < 1 or self.task_revision < 1 or self.run_revision < 1:
            raise InvalidRunPlan("fact_scope_evidence_invalid")
        _require_digest(self.digest, "fact_scope_evidence_invalid")
        if not isinstance(self.lineage_verified, bool) or not isinstance(
            self.subject_binding, FactSubjectBinding
        ):
            raise InvalidRunPlan("fact_scope_evidence_invalid")
        if self.claim_mapping_count < 0 or self.eligible_fact_count < 0:
            raise InvalidRunPlan("fact_scope_evidence_invalid")
        if self.scope is FactScope.NO_PRODUCT_CLAIMS and (
            self.subject_binding is not FactSubjectBinding.NOT_APPLICABLE
            or self.claim_mapping_count != 0
            or self.eligible_fact_count != 0
        ):
            raise InvalidRunPlan("fact_scope_evidence_invalid")
        if self.scope is FactScope.PRODUCT_CLAIMS and (
            self.subject_binding is not FactSubjectBinding.PRODUCT
            or self.claim_mapping_count < 1
            or self.eligible_fact_count < 1
        ):
            raise InvalidRunPlan("fact_scope_evidence_invalid")

    def to_payload(self) -> dict[str, object]:
        return {
            "scope": self.scope.value,
            "ref": self.ref,
            "version": self.version,
            "digest": self.digest,
            "task_id": str(self.task_id),
            "task_revision": self.task_revision,
            "run_id": str(self.run_id),
            "run_revision": self.run_revision,
            "lineage_verified": self.lineage_verified,
            "subject_binding": self.subject_binding.value,
            "claim_mapping_count": self.claim_mapping_count,
            "eligible_fact_count": self.eligible_fact_count,
        }


@dataclass(frozen=True, slots=True)
class ApprovalHandle:
    approval_request_id: UUID
    request_version: int
    request_digest: str
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    gate_kind: ApprovalGateKind
    artifact_type: ArtifactType
    artifact_id: str
    artifact_version: int
    artifact_digest: str
    precondition_digest: str

    def __post_init__(self) -> None:
        _require_uuid(self.approval_request_id, "approval_handle_invalid")
        _require_uuid(self.task_id, "approval_handle_invalid")
        _require_uuid(self.run_id, "approval_handle_invalid")
        if (
            self.request_version < 1
            or self.task_revision < 1
            or self.run_revision < 1
            or self.artifact_version < 1
        ):
            raise InvalidRunPlan("approval_handle_invalid")
        if not isinstance(self.gate_kind, ApprovalGateKind) or not isinstance(
            self.artifact_type, ArtifactType
        ):
            raise InvalidRunPlan("approval_handle_invalid")
        _require_text(self.artifact_id, "approval_handle_invalid")
        _require_digest(self.request_digest, "approval_handle_invalid")
        _require_digest(self.artifact_digest, "approval_handle_invalid")
        _require_digest(self.precondition_digest, "approval_handle_invalid")

    @property
    def request_identity(self) -> tuple[UUID, int]:
        return self.approval_request_id, self.request_version

    def to_payload(self) -> dict[str, object]:
        return {
            "approval_request_id": str(self.approval_request_id),
            "request_version": self.request_version,
            "request_digest": self.request_digest,
            "task_id": str(self.task_id),
            "task_revision": self.task_revision,
            "run_id": str(self.run_id),
            "run_revision": self.run_revision,
            "gate_kind": self.gate_kind.value,
            "artifact_type": self.artifact_type.value,
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "artifact_digest": self.artifact_digest,
            "precondition_digest": self.precondition_digest,
        }


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    primary_mechanism: PrimaryMechanism
    creative_dimension: CreativeDimension
    evidence: ArtifactHandle

    def __post_init__(self) -> None:
        _require_axis(self.primary_mechanism, self.creative_dimension)
        if (
            not isinstance(self.evidence, ArtifactHandle)
            or self.evidence.artifact_type is not ArtifactType.DECOMPOSITION_MAP
            or not self.evidence.lineage_verified
        ):
            raise InvalidRunPlan("route_evidence_invalid")


@dataclass(frozen=True, slots=True)
class ArtifactAvailableGuard:
    handle: ArtifactHandle

    def __post_init__(self) -> None:
        if not isinstance(self.handle, ArtifactHandle) or not self.handle.lineage_verified:
            raise InvalidRunPlan("artifact_guard_invalid")


@dataclass(frozen=True, slots=True)
class RouteIsGuard:
    primary_mechanism: PrimaryMechanism
    creative_dimension: CreativeDimension

    def __post_init__(self) -> None:
        _require_axis(self.primary_mechanism, self.creative_dimension)


@dataclass(frozen=True, slots=True)
class ApprovalGrantedGuard:
    handle: ApprovalHandle

    def __post_init__(self) -> None:
        if not isinstance(self.handle, ApprovalHandle):
            raise InvalidRunPlan("approval_guard_invalid")


@dataclass(frozen=True, slots=True)
class FactScopeSatisfiedGuard:
    evidence: FactScopeEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, FactScopeEvidence) or not self.evidence.lineage_verified:
            raise InvalidRunPlan("fact_scope_guard_invalid")


@dataclass(frozen=True, slots=True)
class MediaModeGuard:
    expected_mode: MediaMode

    def __post_init__(self) -> None:
        if not isinstance(self.expected_mode, MediaMode):
            raise InvalidRunPlan("media_mode_guard_invalid")


type PlanGuard = (
    ArtifactAvailableGuard
    | RouteIsGuard
    | ApprovalGrantedGuard
    | FactScopeSatisfiedGuard
    | MediaModeGuard
)


def _guard_payload(guard: PlanGuard) -> dict[str, object]:
    if isinstance(guard, ArtifactAvailableGuard):
        return {"kind": "artifact_available", "handle": guard.handle.to_payload()}
    if isinstance(guard, RouteIsGuard):
        return {
            "kind": "route_is",
            "primary_mechanism": guard.primary_mechanism.value,
            "creative_dimension": guard.creative_dimension.value,
        }
    if isinstance(guard, ApprovalGrantedGuard):
        return {"kind": "approval_granted", "handle": guard.handle.to_payload()}
    if isinstance(guard, FactScopeSatisfiedGuard):
        return {"kind": "fact_scope_satisfied", "evidence": guard.evidence.to_payload()}
    if isinstance(guard, MediaModeGuard):
        return {"kind": "media_mode", "mode": guard.expected_mode.value}
    raise InvalidRunPlan("run_plan_guard_invalid")


@dataclass(frozen=True, slots=True)
class RunPlanStep:
    step_id: str
    order: int
    capability_name: str
    capability_version: str
    execution_mode: CapabilityExecutionMode
    guards: tuple[PlanGuard, ...]

    def __post_init__(self) -> None:
        _require_text(self.step_id, "run_plan_step_invalid")
        _require_text(self.capability_name, "run_plan_step_invalid")
        _require_text(self.capability_version, "run_plan_step_invalid")
        if (
            self.order < 1
            or not isinstance(self.execution_mode, CapabilityExecutionMode)
            or not isinstance(self.guards, tuple)
        ):
            raise InvalidRunPlan("run_plan_step_invalid")
        for guard in self.guards:
            _guard_payload(guard)

    @classmethod
    def approval_step(
        cls,
        *,
        step_id: str,
        order: int,
        capability_name: str,
        approval_handle: ApprovalHandle,
        capability_version: str = "1.0.0",
    ) -> RunPlanStep:
        return cls(
            step_id=step_id,
            order=order,
            capability_name=capability_name,
            capability_version=capability_version,
            execution_mode=CapabilityExecutionMode.PLANNING_ONLY,
            guards=(ApprovalGrantedGuard(handle=approval_handle),),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "capability_name": self.capability_name,
            "capability_version": self.capability_version,
            "execution_mode": self.execution_mode.value,
            "guards": [_guard_payload(guard) for guard in self.guards],
        }


@dataclass(frozen=True, slots=True)
class RunPlan:
    schema_version: str
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    version: int
    workflow_name: str
    workflow_version: str
    capability_catalog_version: str
    capability_catalog_digest: str
    primary_mechanism: PrimaryMechanism
    creative_dimension: CreativeDimension
    steps: tuple[RunPlanStep, ...]
    input_refs: tuple[PlanInputRef, ...]
    limitations: tuple[str, ...]
    plan_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != "sv-run-plan/v1":
            raise InvalidRunPlan("run_plan_schema_unsupported")
        _require_uuid(self.task_id, "run_plan_identity_invalid")
        _require_uuid(self.run_id, "run_plan_identity_invalid")
        if self.task_revision < 1 or self.run_revision < 1 or self.version < 1:
            raise InvalidRunPlan("run_plan_revision_invalid")
        _require_text(self.workflow_name, "run_plan_workflow_invalid")
        _require_text(self.workflow_version, "run_plan_workflow_invalid")
        _require_text(self.capability_catalog_version, "run_plan_catalog_invalid")
        _require_digest(self.capability_catalog_digest, "run_plan_catalog_invalid")
        _require_axis(self.primary_mechanism, self.creative_dimension)
        if not self.steps or not self.input_refs or not self.limitations:
            raise InvalidRunPlan("run_plan_content_required")
        if tuple(step.order for step in self.steps) != tuple(range(1, len(self.steps) + 1)):
            raise InvalidRunPlan("run_plan_step_order_invalid")
        step_ids = tuple(step.step_id for step in self.steps)
        if len(step_ids) != len(set(step_ids)):
            raise InvalidRunPlan("run_plan_step_duplicate")
        if len(self.input_refs) != len(
            {(item.kind, item.ref, item.version, item.digest) for item in self.input_refs}
        ):
            raise InvalidRunPlan("run_plan_input_ref_duplicate")
        if len(self.input_refs) != len(
            {(item.kind, item.ref, item.version) for item in self.input_refs}
        ):
            raise InvalidRunPlan("run_plan_input_ref_conflict")
        if len(self.input_refs) != len(PlanInputKind) or {
            item.kind for item in self.input_refs
        } != set(PlanInputKind):
            raise InvalidRunPlan("run_plan_input_kinds_invalid")
        task_brief_ref = self._input_ref_for(PlanInputKind.TASK_BRIEF)
        catalog_ref = self._input_ref_for(PlanInputKind.CATALOG)
        if (
            task_brief_ref.ref != f"task-brief:{self.task_id}"
            or task_brief_ref.version != self.task_revision
        ):
            raise InvalidRunPlan("run_plan_task_brief_ref_invalid")
        if (
            catalog_ref.ref != "workflow-catalog:static"
            or catalog_ref.digest != self.capability_catalog_digest
        ):
            raise InvalidRunPlan("run_plan_catalog_ref_invalid")
        if any(not item or item != item.strip() for item in self.limitations):
            raise InvalidRunPlan("run_plan_limitation_invalid")
        self._validate_guard_scope()
        payload = self.to_payload()
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        if len(serialized) > MAX_RUN_PLAN_PAYLOAD_BYTES:
            raise InvalidRunPlan("run_plan_payload_too_large")
        object.__setattr__(self, "plan_digest", canonical_digest(payload))

    def _validate_guard_scope(self) -> None:
        route_input = self._input_ref_for(PlanInputKind.ROUTE_EVIDENCE)
        fact_scope_input = self._input_ref_for(PlanInputKind.FACT_SCOPE_EVIDENCE)
        for step in self.steps:
            for guard in step.guards:
                if isinstance(guard, ArtifactAvailableGuard):
                    self._validate_evidence_scope(
                        task_id=guard.handle.task_id,
                        task_revision=guard.handle.task_revision,
                        run_id=guard.handle.run_id,
                        run_revision=guard.handle.run_revision,
                    )
                    if (
                        route_input.ref
                        != f"{guard.handle.artifact_type.value}:{guard.handle.artifact_id}"
                        or route_input.version != guard.handle.version
                        or route_input.digest != guard.handle.digest
                    ):
                        raise InvalidRunPlan("run_plan_route_input_mismatch")
                elif isinstance(guard, FactScopeSatisfiedGuard):
                    self._validate_evidence_scope(
                        task_id=guard.evidence.task_id,
                        task_revision=guard.evidence.task_revision,
                        run_id=guard.evidence.run_id,
                        run_revision=guard.evidence.run_revision,
                    )
                    if (
                        fact_scope_input.ref != guard.evidence.ref
                        or fact_scope_input.version != guard.evidence.version
                        or fact_scope_input.digest != guard.evidence.digest
                    ):
                        raise InvalidRunPlan("run_plan_fact_scope_input_mismatch")
                elif isinstance(guard, RouteIsGuard):
                    if (
                        guard.primary_mechanism is not self.primary_mechanism
                        or guard.creative_dimension is not self.creative_dimension
                    ):
                        raise InvalidRunPlan("run_plan_route_guard_mismatch")
                elif isinstance(guard, ApprovalGrantedGuard):
                    handle = guard.handle
                    if (
                        handle.task_id != self.task_id
                        or handle.task_revision != self.task_revision
                        or handle.run_id != self.run_id
                        or handle.run_revision != self.run_revision
                    ):
                        raise InvalidRunPlan("run_plan_guard_scope_invalid")

    def _input_ref_for(self, kind: PlanInputKind) -> PlanInputRef:
        matches = tuple(item for item in self.input_refs if item.kind is kind)
        if len(matches) != 1:
            raise InvalidRunPlan("run_plan_input_kinds_invalid")
        return matches[0]

    def _validate_evidence_scope(
        self,
        *,
        task_id: UUID,
        task_revision: int,
        run_id: UUID,
        run_revision: int,
    ) -> None:
        if (
            task_id != self.task_id
            or task_revision != self.task_revision
            or run_id != self.run_id
            or run_revision > self.run_revision
        ):
            raise InvalidRunPlan("run_plan_guard_scope_invalid")

    @classmethod
    def create(
        cls,
        *,
        task_id: UUID,
        task_revision: int,
        run_id: UUID,
        run_revision: int,
        version: int,
        workflow_name: str,
        workflow_version: str,
        capability_catalog_version: str,
        capability_catalog_digest: str,
        primary_mechanism: PrimaryMechanism,
        creative_dimension: CreativeDimension,
        steps: tuple[RunPlanStep, ...],
        input_refs: tuple[PlanInputRef, ...],
        limitations: tuple[str, ...],
    ) -> RunPlan:
        return cls(
            schema_version="sv-run-plan/v1",
            task_id=task_id,
            task_revision=task_revision,
            run_id=run_id,
            run_revision=run_revision,
            version=version,
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            capability_catalog_version=capability_catalog_version,
            capability_catalog_digest=capability_catalog_digest,
            primary_mechanism=primary_mechanism,
            creative_dimension=creative_dimension,
            steps=steps,
            input_refs=input_refs,
            limitations=limitations,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "task_id": str(self.task_id),
            "task_revision": self.task_revision,
            "run_id": str(self.run_id),
            "run_revision": self.run_revision,
            "version": self.version,
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "capability_catalog_version": self.capability_catalog_version,
            "capability_catalog_digest": self.capability_catalog_digest,
            "primary_mechanism": self.primary_mechanism.value,
            "creative_dimension": self.creative_dimension.value,
            "steps": [step.to_payload() for step in self.steps],
            "input_refs": [
                {
                    "kind": item.kind.value,
                    "ref": item.ref,
                    "version": item.version,
                    "digest": item.digest,
                }
                for item in self.input_refs
            ],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    handle: ArtifactHandle

    def __post_init__(self) -> None:
        if not isinstance(self.handle, ArtifactHandle):
            raise InvalidRunPlan("artifact_snapshot_invalid")


@dataclass(frozen=True, slots=True)
class ApprovalSnapshot:
    handle: ApprovalHandle
    decision: ApprovalDecision
    actor_kind: ActorKind
    authority: ApprovalAuthority
    stale: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.handle, ApprovalHandle)
            or not isinstance(self.decision, ApprovalDecision)
            or not isinstance(self.actor_kind, ActorKind)
            or not isinstance(self.authority, ApprovalAuthority)
            or not isinstance(self.stale, bool)
        ):
            raise InvalidRunPlan("approval_snapshot_invalid")
        if (
            self.authority is ApprovalAuthority.VERIFIED_HUMAN
            and self.actor_kind is not ActorKind.HUMAN
        ):
            raise InvalidRunPlan("approval_snapshot_invalid")


@dataclass(frozen=True, slots=True)
class PrerequisiteSnapshot:
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    artifacts: tuple[ArtifactSnapshot, ...]
    approvals: tuple[ApprovalSnapshot, ...]
    primary_mechanism: PrimaryMechanism
    creative_dimension: CreativeDimension
    fact_scope_evidence: FactScopeEvidence | None
    fact_scope_state: FactScopeState
    media_mode: MediaMode

    def __post_init__(self) -> None:
        _require_uuid(self.task_id, "prerequisite_snapshot_invalid")
        _require_uuid(self.run_id, "prerequisite_snapshot_invalid")
        if self.task_revision < 1 or self.run_revision < 1:
            raise InvalidRunPlan("prerequisite_snapshot_invalid")
        if any(not isinstance(item, ArtifactSnapshot) for item in self.artifacts) or any(
            not isinstance(item, ApprovalSnapshot) for item in self.approvals
        ):
            raise InvalidRunPlan("prerequisite_snapshot_invalid")
        _require_axis(self.primary_mechanism, self.creative_dimension)
        if not isinstance(self.fact_scope_state, FactScopeState):
            raise InvalidRunPlan("fact_scope_snapshot_invalid")
        if self.fact_scope_evidence is not None and not isinstance(
            self.fact_scope_evidence, FactScopeEvidence
        ):
            raise InvalidRunPlan("fact_scope_snapshot_invalid")
        if self.fact_scope_state is FactScopeState.SATISFIED and self.fact_scope_evidence is None:
            raise InvalidRunPlan("fact_scope_snapshot_invalid")
        if self.fact_scope_state is FactScopeState.MISSING and self.fact_scope_evidence is not None:
            raise InvalidRunPlan("fact_scope_snapshot_invalid")
        if not isinstance(self.media_mode, MediaMode):
            raise InvalidRunPlan("media_mode_snapshot_invalid")


@dataclass(frozen=True, slots=True)
class OrchestrationDecision:
    disposition: OrchestrationDisposition
    next_step_id: str | None
    stable_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, OrchestrationDisposition):
            raise InvalidRunPlan("orchestration_decision_invalid")
        if self.disposition is OrchestrationDisposition.READY:
            _require_text(self.next_step_id or "", "orchestration_decision_invalid")
        elif self.next_step_id is not None:
            raise InvalidRunPlan("orchestration_decision_invalid")
