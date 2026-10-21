from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    CreativeDimension,
    GoalTrack,
    PrimaryMechanism,
    Run,
    RunState,
    Task,
    dimensions_for_mechanism,
)
from app.domain.sv_agent.errors import InvalidRunPlan
from app.domain.sv_agent.planning import (
    ApprovalAuthority,
    ApprovalGrantedGuard,
    ArtifactAvailableGuard,
    CapabilityExecutionMode,
    FactScope,
    FactScopeEvidence,
    FactScopeSatisfiedGuard,
    FactScopeState,
    MediaMode,
    MediaModeGuard,
    OrchestrationDecision,
    OrchestrationDisposition,
    PlanInputKind,
    PlanInputRef,
    PrerequisiteSnapshot,
    RouteCandidate,
    RouteIsGuard,
    RunPlan,
    RunPlanStep,
)
from app.domain.sv_agent.runtime_records import ActorKind, ApprovalDecision


@dataclass(frozen=True, slots=True)
class WorkflowDescriptor:
    workflow_name: str
    workflow_version: str
    primary_mechanism: PrimaryMechanism
    dimensions: frozenset[CreativeDimension]
    capability_name: str
    capability_version: str
    execution_mode: CapabilityExecutionMode

    def __post_init__(self) -> None:
        if (
            not self.workflow_name
            or self.workflow_name != self.workflow_name.strip()
            or not self.workflow_version
            or self.workflow_version != self.workflow_version.strip()
            or not self.capability_name
            or self.capability_name != self.capability_name.strip()
            or not self.capability_version
            or self.capability_version != self.capability_version.strip()
            or not isinstance(self.primary_mechanism, PrimaryMechanism)
            or not isinstance(self.execution_mode, CapabilityExecutionMode)
            or self.dimensions != dimensions_for_mechanism(self.primary_mechanism)
        ):
            raise InvalidRunPlan("workflow_descriptor_invalid")

    def to_payload(self) -> dict[str, object]:
        return {
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "primary_mechanism": self.primary_mechanism.value,
            "dimensions": sorted(item.value for item in self.dimensions),
            "capability_name": self.capability_name,
            "capability_version": self.capability_version,
            "execution_mode": self.execution_mode.value,
        }


@dataclass(frozen=True, slots=True, init=False)
class StaticWorkflowCatalog:
    input_version: ClassVar[int] = 1
    version: str
    descriptors: tuple[WorkflowDescriptor, ...]
    digest: str

    def __init__(self, *, version: str = "1.0.0") -> None:
        if not version or version != version.strip():
            raise InvalidRunPlan("workflow_catalog_invalid")
        descriptors = tuple(
            WorkflowDescriptor(
                workflow_name=f"viral-replication.{mechanism.value}",
                workflow_version="1.0.0",
                primary_mechanism=mechanism,
                dimensions=dimensions_for_mechanism(mechanism),
                capability_name=f"planning.viral.{mechanism.value}",
                capability_version="1.0.0",
                execution_mode=CapabilityExecutionMode.PLANNING_ONLY,
            )
            for mechanism in PrimaryMechanism
        )
        if len(descriptors) != 6 or len({item.primary_mechanism for item in descriptors}) != len(
            descriptors
        ):
            raise InvalidRunPlan("workflow_catalog_invalid")
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "descriptors", descriptors)
        object.__setattr__(self, "digest", canonical_digest(self.to_payload()))

    def to_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "descriptors": [item.to_payload() for item in self.descriptors],
        }

    def descriptor_for(self, mechanism: PrimaryMechanism) -> WorkflowDescriptor:
        self.assert_integrity()
        matches = tuple(item for item in self.descriptors if item.primary_mechanism is mechanism)
        if len(matches) != 1:
            raise InvalidRunPlan("workflow_descriptor_unavailable")
        return matches[0]

    def assert_integrity(self) -> None:
        if canonical_digest(self.to_payload()) != self.digest:
            raise InvalidRunPlan("workflow_catalog_invalid")


class PlanningDisposition(StrEnum):
    PLAN_COMPILED = "plan_compiled"
    AWAITING_INPUT = "awaiting_input"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PlanningOutcome:
    disposition: PlanningDisposition
    stable_code: str
    run: Run
    plan: RunPlan | None


class RunPlanner:
    def __init__(self, catalog: StaticWorkflowCatalog | None = None) -> None:
        self._catalog = catalog or StaticWorkflowCatalog()

    def compile(
        self,
        *,
        task: Task,
        run: Run,
        candidates: tuple[RouteCandidate, ...],
        fact_scope_evidence: FactScopeEvidence,
    ) -> PlanningOutcome:
        if run.task_id != task.id or run.task_revision != task.revision:
            raise InvalidRunPlan("task_run_binding_invalid")
        if run.state is not RunState.PLANNING:
            raise InvalidRunPlan("run_plan_requires_planning")
        if run.primary_mechanism is not None or run.creative_dimension is not None:
            raise InvalidRunPlan("run_plan_axis_already_selected")
        self._validate_authoritative_context(
            task=task,
            run=run,
            candidates=candidates,
            fact_scope_evidence=fact_scope_evidence,
        )
        if not candidates:
            return PlanningOutcome(
                disposition=PlanningDisposition.AWAITING_INPUT,
                stable_code="primary_mechanism_required",
                run=run,
                plan=None,
            )
        if len(candidates) != 1:
            return PlanningOutcome(
                disposition=PlanningDisposition.BLOCKED,
                stable_code="primary_mechanism_ambiguous",
                run=run,
                plan=None,
            )
        candidate = candidates[0]
        descriptor = self._catalog.descriptor_for(candidate.primary_mechanism)
        if candidate.creative_dimension not in descriptor.dimensions:
            raise InvalidRunPlan("workflow_dimension_invalid")
        selected_run = run.select_replication_axis(
            primary_mechanism=candidate.primary_mechanism,
            creative_dimension=candidate.creative_dimension,
            updated_at=run.updated_at,
        )
        task_brief_digest = canonical_digest(task.brief)
        plan = RunPlan.create(
            task_id=task.id,
            task_revision=task.revision,
            run_id=selected_run.id,
            run_revision=selected_run.revision,
            version=1,
            workflow_name=descriptor.workflow_name,
            workflow_version=descriptor.workflow_version,
            capability_catalog_version=self._catalog.version,
            capability_catalog_digest=self._catalog.digest,
            primary_mechanism=candidate.primary_mechanism,
            creative_dimension=candidate.creative_dimension,
            steps=(
                RunPlanStep(
                    step_id="inspect-route",
                    order=1,
                    capability_name=descriptor.capability_name,
                    capability_version=descriptor.capability_version,
                    execution_mode=descriptor.execution_mode,
                    guards=(
                        ArtifactAvailableGuard(handle=candidate.evidence),
                        RouteIsGuard(
                            primary_mechanism=candidate.primary_mechanism,
                            creative_dimension=candidate.creative_dimension,
                        ),
                        FactScopeSatisfiedGuard(evidence=fact_scope_evidence),
                        MediaModeGuard(expected_mode=MediaMode.ANALYSIS_ONLY),
                    ),
                ),
            ),
            input_refs=(
                PlanInputRef(
                    kind=PlanInputKind.TASK_BRIEF,
                    ref=f"task-brief:{task.id}",
                    version=task.revision,
                    digest=task_brief_digest,
                ),
                PlanInputRef(
                    kind=PlanInputKind.ROUTE_EVIDENCE,
                    ref=(
                        f"{candidate.evidence.artifact_type.value}:{candidate.evidence.artifact_id}"
                    ),
                    version=candidate.evidence.version,
                    digest=candidate.evidence.digest,
                ),
                PlanInputRef(
                    kind=PlanInputKind.FACT_SCOPE_EVIDENCE,
                    ref=fact_scope_evidence.ref,
                    version=fact_scope_evidence.version,
                    digest=fact_scope_evidence.digest,
                ),
                PlanInputRef(
                    kind=PlanInputKind.CATALOG,
                    ref="workflow-catalog:static",
                    version=self._catalog.input_version,
                    digest=self._catalog.digest,
                ),
            ),
            limitations=(
                "No database write, Tool dispatch, provider cost, render, publish, rights, commercial, deployment, or production approval.",
            ),
        )
        return PlanningOutcome(
            disposition=PlanningDisposition.PLAN_COMPILED,
            stable_code="run_plan_compiled",
            run=selected_run,
            plan=plan,
        )

    def _validate_authoritative_context(
        self,
        *,
        task: Task,
        run: Run,
        candidates: tuple[RouteCandidate, ...],
        fact_scope_evidence: FactScopeEvidence,
    ) -> None:
        self._catalog.assert_integrity()
        if not fact_scope_evidence.lineage_verified:
            raise InvalidRunPlan("fact_scope_evidence_unverified")
        if (
            task.brief.goal_track is GoalTrack.PRODUCT_REPLICATION
            and fact_scope_evidence.scope is FactScope.NO_PRODUCT_CLAIMS
        ):
            raise InvalidRunPlan("product_replication_fact_scope_invalid")
        self._require_evidence_scope(
            task=task,
            run=run,
            task_id=fact_scope_evidence.task_id,
            task_revision=fact_scope_evidence.task_revision,
            run_id=fact_scope_evidence.run_id,
            run_revision=fact_scope_evidence.run_revision,
            stable_code="fact_scope_evidence_scope_mismatch",
        )
        for candidate in candidates:
            self._require_evidence_scope(
                task=task,
                run=run,
                task_id=candidate.evidence.task_id,
                task_revision=candidate.evidence.task_revision,
                run_id=candidate.evidence.run_id,
                run_revision=candidate.evidence.run_revision,
                stable_code="route_evidence_scope_mismatch",
            )

    @staticmethod
    def _require_evidence_scope(
        *,
        task: Task,
        run: Run,
        task_id: object,
        task_revision: int,
        run_id: object,
        run_revision: int,
        stable_code: str,
    ) -> None:
        if (
            task_id != task.id
            or task_revision != task.revision
            or run_id != run.id
            or run_revision != run.revision
        ):
            raise InvalidRunPlan(stable_code)


class OrchestrationEvaluator:
    _PRIORITY: ClassVar[dict[OrchestrationDisposition, int]] = {
        OrchestrationDisposition.BLOCKED: 0,
        OrchestrationDisposition.AWAITING_APPROVAL: 1,
        OrchestrationDisposition.AWAITING_INPUT: 2,
    }

    def evaluate(
        self,
        *,
        plan: RunPlan,
        snapshot: PrerequisiteSnapshot,
        completed_step_ids: tuple[str, ...],
    ) -> OrchestrationDecision:
        if (
            snapshot.task_id != plan.task_id
            or snapshot.task_revision != plan.task_revision
            or snapshot.run_id != plan.run_id
            or snapshot.run_revision != plan.run_revision
        ):
            return OrchestrationDecision(
                disposition=OrchestrationDisposition.BLOCKED,
                next_step_id=None,
                stable_codes=("prerequisite_scope_mismatch",),
            )
        if (
            snapshot.primary_mechanism is not plan.primary_mechanism
            or snapshot.creative_dimension is not plan.creative_dimension
        ):
            return OrchestrationDecision(
                disposition=OrchestrationDisposition.BLOCKED,
                next_step_id=None,
                stable_codes=("route_mismatch",),
            )
        known_step_ids = tuple(step.step_id for step in plan.steps)
        if completed_step_ids != known_step_ids[: len(completed_step_ids)]:
            raise InvalidRunPlan("completed_step_invalid")
        next_step = next(
            (step for step in plan.steps if step.step_id not in completed_step_ids),
            None,
        )
        if next_step is None:
            return OrchestrationDecision(
                disposition=OrchestrationDisposition.PLAN_COMPLETE,
                next_step_id=None,
                stable_codes=(),
            )

        findings: list[tuple[OrchestrationDisposition, str]] = []
        for guard in next_step.guards:
            finding = self._evaluate_guard(guard=guard, snapshot=snapshot)
            if finding is not None:
                findings.append(finding)
        if not findings:
            return OrchestrationDecision(
                disposition=OrchestrationDisposition.READY,
                next_step_id=next_step.step_id,
                stable_codes=(),
            )
        disposition = min(findings, key=lambda finding: self._PRIORITY[finding[0]])[0]
        return OrchestrationDecision(
            disposition=disposition,
            next_step_id=None,
            stable_codes=tuple(code for state, code in findings if state is disposition),
        )

    def _evaluate_guard(
        self,
        *,
        guard: object,
        snapshot: PrerequisiteSnapshot,
    ) -> tuple[OrchestrationDisposition, str] | None:
        if isinstance(guard, ArtifactAvailableGuard):
            candidates = tuple(
                item for item in snapshot.artifacts if item.handle.identity == guard.handle.identity
            )
            if not candidates:
                return OrchestrationDisposition.AWAITING_INPUT, "artifact_required"
            if len(candidates) > 1:
                return OrchestrationDisposition.BLOCKED, "artifact_snapshot_conflict"
            artifact = candidates[0].handle
            if artifact.digest != guard.handle.digest:
                return OrchestrationDisposition.BLOCKED, "artifact_digest_mismatch"
            if not artifact.lineage_verified:
                return OrchestrationDisposition.BLOCKED, "artifact_lineage_unverified"
            return None
        if isinstance(guard, RouteIsGuard):
            if (
                snapshot.primary_mechanism is not guard.primary_mechanism
                or snapshot.creative_dimension is not guard.creative_dimension
            ):
                return OrchestrationDisposition.BLOCKED, "route_mismatch"
            return None
        if isinstance(guard, FactScopeSatisfiedGuard):
            if snapshot.fact_scope_state in {FactScopeState.STALE, FactScopeState.BLOCKED}:
                return OrchestrationDisposition.BLOCKED, "fact_scope_invalid"
            if snapshot.fact_scope_state is FactScopeState.MISSING:
                return OrchestrationDisposition.AWAITING_INPUT, "fact_scope_required"
            if snapshot.fact_scope_evidence != guard.evidence:
                return OrchestrationDisposition.BLOCKED, "fact_scope_mismatch"
            if not guard.evidence.lineage_verified:
                return OrchestrationDisposition.BLOCKED, "fact_scope_unverified"
            return None
        if isinstance(guard, MediaModeGuard):
            if snapshot.media_mode is not guard.expected_mode:
                return OrchestrationDisposition.AWAITING_INPUT, "media_mode_required"
            return None
        if isinstance(guard, ApprovalGrantedGuard):
            approvals = tuple(
                item
                for item in snapshot.approvals
                if item.handle.request_identity == guard.handle.request_identity
            )
            if not approvals:
                return OrchestrationDisposition.AWAITING_APPROVAL, "approval_required"
            if len(approvals) > 1:
                return OrchestrationDisposition.BLOCKED, "approval_snapshot_conflict"
            approval = approvals[0]
            if approval.handle != guard.handle:
                return OrchestrationDisposition.BLOCKED, "approval_binding_mismatch"
            if approval.stale:
                return OrchestrationDisposition.BLOCKED, "approval_stale"
            if (
                approval.authority is not ApprovalAuthority.VERIFIED_HUMAN
                or approval.actor_kind is not ActorKind.HUMAN
            ):
                return OrchestrationDisposition.BLOCKED, "human_approval_required"
            if approval.decision in {ApprovalDecision.REJECT, ApprovalDecision.STOP}:
                return OrchestrationDisposition.BLOCKED, "approval_rejected"
            if approval.decision is ApprovalDecision.REQUEST_EVIDENCE:
                return OrchestrationDisposition.AWAITING_INPUT, "approval_requested_evidence"
            if approval.decision is ApprovalDecision.APPROVE:
                return None
            raise InvalidRunPlan("approval_decision_invalid")
        raise InvalidRunPlan("run_plan_guard_invalid")
