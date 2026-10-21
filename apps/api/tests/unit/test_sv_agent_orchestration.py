from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.application.sv_agent.orchestration import (
    OrchestrationEvaluator,
    PlanningDisposition,
    RunPlanner,
    StaticWorkflowCatalog,
)
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    CreativeDimension,
    GoalTrack,
    PerformanceWindow,
    PrimaryMechanism,
    RightsState,
    Run,
    RunState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import InvalidRunPlan
from app.domain.sv_agent.planning import (
    ApprovalAuthority,
    ApprovalHandle,
    ApprovalSnapshot,
    ArtifactAvailableGuard,
    ArtifactHandle,
    ArtifactSnapshot,
    CapabilityExecutionMode,
    FactScope,
    FactScopeEvidence,
    FactScopeSatisfiedGuard,
    FactScopeState,
    FactSubjectBinding,
    MediaMode,
    MediaModeGuard,
    OrchestrationDisposition,
    PlanInputKind,
    PlanInputRef,
    PrerequisiteSnapshot,
    RouteCandidate,
    RouteIsGuard,
    RunPlan,
    RunPlanStep,
)
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ApprovalDecision,
    ApprovalGateKind,
    ArtifactType,
)

TASK_ID = UUID("00000000-0000-0000-0000-000000000101")
RUN_ID = UUID("00000000-0000-0000-0000-000000000201")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000301")
EVIDENCE_DIGEST = "a" * 64


def _task(goal_track: GoalTrack = GoalTrack.PRODUCT_REPLICATION) -> Task:
    brief = TaskBrief.create(
        goal_track=goal_track,
        decision_question="Which bounded mechanism should this run test?",
        subject="Momcozy baby-care social content",
        platform=TargetPlatform.TIKTOK,
        market="US",
        language="en-US",
        performance_window=PerformanceWindow(
            start=date(2026, 10, 1),
            end=date(2026, 10, 7),
            timezone="America/Los_Angeles",
        ),
        stop_condition="Stop at the declared review gate.",
        initial_rights_state=RightsState.ANALYSIS_ONLY,
    )
    return Task.new(brief, id=TASK_ID, created_at=datetime(2026, 10, 21, tzinfo=UTC))


def _planning_run(*, task_id: UUID = TASK_ID, task_revision: int = 1) -> Run:
    return Run.new(
        task_id=task_id,
        task_revision=task_revision,
        id=RUN_ID,
        created_at=datetime(2026, 10, 21, tzinfo=UTC),
    ).transition_to(RunState.PLANNING)


def _artifact_handle(
    *,
    digest: str = EVIDENCE_DIGEST,
    task_id: UUID = TASK_ID,
    run_revision: int = 2,
) -> ArtifactHandle:
    return ArtifactHandle(
        artifact_type=ArtifactType.DECOMPOSITION_MAP,
        artifact_id="dm-001",
        version=1,
        digest=digest,
        task_id=task_id,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=run_revision,
        lineage_verified=True,
    )


def _fact_evidence(
    scope: FactScope = FactScope.PRODUCT_CLAIMS,
    *,
    digest: str = "b" * 64,
    task_id: UUID = TASK_ID,
    run_revision: int = 2,
) -> FactScopeEvidence:
    return FactScopeEvidence(
        scope=scope,
        ref="fact-map:fm-001" if scope is FactScope.PRODUCT_CLAIMS else "claim-scope:none",
        version=1,
        digest=digest,
        task_id=task_id,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=run_revision,
        lineage_verified=True,
        subject_binding=(
            FactSubjectBinding.PRODUCT
            if scope is FactScope.PRODUCT_CLAIMS
            else FactSubjectBinding.NOT_APPLICABLE
        ),
        claim_mapping_count=1 if scope is FactScope.PRODUCT_CLAIMS else 0,
        eligible_fact_count=1 if scope is FactScope.PRODUCT_CLAIMS else 0,
    )


def _candidate(
    mechanism: PrimaryMechanism = PrimaryMechanism.ATTENTION_GRAMMAR,
    dimension: CreativeDimension = CreativeDimension.HOOK_TRIGGER,
    *,
    digest: str = EVIDENCE_DIGEST,
) -> RouteCandidate:
    return RouteCandidate(
        primary_mechanism=mechanism,
        creative_dimension=dimension,
        evidence=_artifact_handle(digest=digest),
    )


def _plan_input_refs(*, catalog_digest: str = "c" * 64) -> tuple[PlanInputRef, ...]:
    return (
        PlanInputRef(
            kind=PlanInputKind.TASK_BRIEF,
            ref=f"task-brief:{TASK_ID}",
            version=1,
            digest="9" * 64,
        ),
        PlanInputRef(
            kind=PlanInputKind.ROUTE_EVIDENCE,
            ref="decomposition_map:dm-001",
            version=1,
            digest=EVIDENCE_DIGEST,
        ),
        PlanInputRef(
            kind=PlanInputKind.FACT_SCOPE_EVIDENCE,
            ref="fact-map:fm-001",
            version=1,
            digest="b" * 64,
        ),
        PlanInputRef(
            kind=PlanInputKind.CATALOG,
            ref="workflow-catalog:static",
            version=1,
            digest=catalog_digest,
        ),
    )


def test_static_catalog_is_closed_digest_bound_and_planning_only() -> None:
    catalog = StaticWorkflowCatalog()

    assert catalog.version == "1.0.0"
    assert len(catalog.digest) == 64
    assert {item.primary_mechanism for item in catalog.descriptors} == set(PrimaryMechanism)
    assert len({item.workflow_name for item in catalog.descriptors}) == 6
    assert all(
        item.execution_mode is CapabilityExecutionMode.PLANNING_ONLY
        and item.capability_name.startswith("planning.viral.")
        for item in catalog.descriptors
    )
    with pytest.raises(FrozenInstanceError):
        catalog.descriptors = ()  # type: ignore[misc]


def test_planner_does_not_guess_when_route_evidence_is_missing() -> None:
    run = _planning_run()
    outcome = RunPlanner().compile(
        task=_task(),
        run=run,
        candidates=(),
        fact_scope_evidence=_fact_evidence(),
    )

    assert outcome.disposition is PlanningDisposition.AWAITING_INPUT
    assert outcome.stable_code == "primary_mechanism_required"
    assert outcome.run == run
    assert outcome.plan is None


def test_planner_blocks_ambiguous_routes_without_changing_run() -> None:
    run = _planning_run()
    outcome = RunPlanner().compile(
        task=_task(),
        run=run,
        candidates=(
            _candidate(),
            _candidate(
                PrimaryMechanism.TREND_NATIVE,
                CreativeDimension.TEMPLATE_GRAMMAR,
                digest="d" * 64,
            ),
        ),
        fact_scope_evidence=_fact_evidence(),
    )

    assert outcome.disposition is PlanningDisposition.BLOCKED
    assert outcome.stable_code == "primary_mechanism_ambiguous"
    assert outcome.run == run
    assert outcome.plan is None


def test_unique_route_compiles_plan_bound_to_all_authoritative_inputs() -> None:
    task = _task()
    fact_evidence = _fact_evidence()
    outcome = RunPlanner().compile(
        task=task,
        run=_planning_run(),
        candidates=(_candidate(),),
        fact_scope_evidence=fact_evidence,
    )

    assert outcome.disposition is PlanningDisposition.PLAN_COMPILED
    assert outcome.plan is not None
    assert outcome.run.state is RunState.PLANNING
    assert outcome.run.primary_mechanism is PrimaryMechanism.ATTENTION_GRAMMAR
    assert outcome.plan.run_revision == outcome.run.revision
    assert outcome.plan.workflow_name == "viral-replication.attention-grammar"
    assert outcome.plan.capability_catalog_digest == StaticWorkflowCatalog().digest
    assert {item.kind for item in outcome.plan.input_refs} == set(PlanInputKind)
    assert next(
        item for item in outcome.plan.input_refs if item.kind is PlanInputKind.TASK_BRIEF
    ).digest == canonical_digest(task.brief)
    assert (
        next(
            item
            for item in outcome.plan.input_refs
            if item.kind is PlanInputKind.FACT_SCOPE_EVIDENCE
        ).digest
        == fact_evidence.digest
    )


@pytest.mark.parametrize("scope", tuple(FactScope))
def test_brand_voice_uses_explicit_fact_scope_instead_of_guessing(scope: FactScope) -> None:
    outcome = RunPlanner().compile(
        task=_task(GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE),
        run=_planning_run(),
        candidates=(_candidate(),),
        fact_scope_evidence=_fact_evidence(scope),
    )

    assert outcome.plan is not None
    guard = next(
        guard
        for guard in outcome.plan.steps[0].guards
        if isinstance(guard, FactScopeSatisfiedGuard)
    )
    assert guard.evidence.scope is scope


@pytest.mark.parametrize(
    "candidates",
    (
        (),
        (_candidate(),),
        (
            _candidate(),
            _candidate(
                PrimaryMechanism.TREND_NATIVE,
                CreativeDimension.TEMPLATE_GRAMMAR,
                digest="d" * 64,
            ),
        ),
    ),
)
def test_product_replication_rejects_no_product_claim_scope_before_routing(
    candidates: tuple[RouteCandidate, ...],
) -> None:
    with pytest.raises(InvalidRunPlan, match="product_replication_fact_scope_invalid"):
        RunPlanner().compile(
            task=_task(GoalTrack.PRODUCT_REPLICATION),
            run=_planning_run(),
            candidates=candidates,
            fact_scope_evidence=_fact_evidence(FactScope.NO_PRODUCT_CLAIMS),
        )


@pytest.mark.parametrize(
    "candidates",
    (
        (),
        (_candidate(),),
        (
            _candidate(),
            _candidate(
                PrimaryMechanism.TREND_NATIVE,
                CreativeDimension.TEMPLATE_GRAMMAR,
                digest="d" * 64,
            ),
        ),
    ),
)
def test_catalog_integrity_is_checked_before_routing(
    candidates: tuple[RouteCandidate, ...],
) -> None:
    catalog = StaticWorkflowCatalog()
    object.__setattr__(catalog, "descriptors", ())

    with pytest.raises(InvalidRunPlan, match="workflow_catalog_invalid"):
        RunPlanner(catalog).compile(
            task=_task(),
            run=_planning_run(),
            candidates=candidates,
            fact_scope_evidence=_fact_evidence(),
        )


def test_plan_digest_changes_with_brief_fact_or_catalog_digest() -> None:
    task = _task()
    run = _planning_run()
    baseline = RunPlanner().compile(
        task=task,
        run=run,
        candidates=(_candidate(),),
        fact_scope_evidence=_fact_evidence(),
    )
    changed_brief = RunPlanner().compile(
        task=replace(
            task,
            brief=replace(task.brief, decision_question="What should the next test prove?"),
        ),
        run=run,
        candidates=(_candidate(),),
        fact_scope_evidence=_fact_evidence(),
    )
    changed_fact = RunPlanner().compile(
        task=task,
        run=run,
        candidates=(_candidate(),),
        fact_scope_evidence=_fact_evidence(digest="e" * 64),
    )
    changed_catalog = RunPlanner(StaticWorkflowCatalog(version="1.0.1")).compile(
        task=task,
        run=run,
        candidates=(_candidate(),),
        fact_scope_evidence=_fact_evidence(),
    )

    plans = (baseline.plan, changed_brief.plan, changed_fact.plan, changed_catalog.plan)
    assert all(plan is not None for plan in plans)
    assert len({plan.plan_digest for plan in plans if plan is not None}) == 4


@pytest.mark.parametrize(
    ("task", "run"),
    (
        (_task(), _planning_run(task_id=UUID("00000000-0000-0000-0000-000000000999"))),
        (_task(), _planning_run(task_revision=2)),
    ),
)
def test_planner_rejects_task_run_identity_mismatch(task: Task, run: Run) -> None:
    with pytest.raises(InvalidRunPlan, match="task_run_binding_invalid"):
        RunPlanner().compile(
            task=task,
            run=run,
            candidates=(_candidate(),),
            fact_scope_evidence=_fact_evidence(),
        )


def test_planner_rejects_cross_scope_route_or_fact_evidence() -> None:
    other_task_id = UUID("00000000-0000-0000-0000-000000000999")
    with pytest.raises(InvalidRunPlan, match="route_evidence_scope_mismatch"):
        RunPlanner().compile(
            task=_task(),
            run=_planning_run(),
            candidates=(
                RouteCandidate(
                    primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
                    creative_dimension=CreativeDimension.HOOK_TRIGGER,
                    evidence=_artifact_handle(task_id=other_task_id),
                ),
            ),
            fact_scope_evidence=_fact_evidence(),
        )
    with pytest.raises(InvalidRunPlan, match="fact_scope_evidence_scope_mismatch"):
        RunPlanner().compile(
            task=_task(),
            run=_planning_run(),
            candidates=(_candidate(),),
            fact_scope_evidence=_fact_evidence(task_id=other_task_id),
        )


def test_invalid_authoritative_scope_precedes_ambiguous_route_disposition() -> None:
    other_task_id = UUID("00000000-0000-0000-0000-000000000999")
    candidates = (
        _candidate(),
        RouteCandidate(
            primary_mechanism=PrimaryMechanism.TREND_NATIVE,
            creative_dimension=CreativeDimension.TEMPLATE_GRAMMAR,
            evidence=_artifact_handle(task_id=other_task_id, digest="d" * 64),
        ),
    )
    with pytest.raises(InvalidRunPlan, match="route_evidence_scope_mismatch"):
        RunPlanner().compile(
            task=_task(),
            run=_planning_run(),
            candidates=candidates,
            fact_scope_evidence=_fact_evidence(),
        )

    with pytest.raises(InvalidRunPlan, match="fact_scope_evidence_scope_mismatch"):
        RunPlanner().compile(
            task=_task(),
            run=_planning_run(),
            candidates=(),
            fact_scope_evidence=_fact_evidence(task_id=other_task_id),
        )


def _guarded_plan() -> RunPlan:
    return RunPlan.create(
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=3,
        version=1,
        workflow_name="viral-replication.attention-grammar",
        workflow_version="1.0.0",
        capability_catalog_version="1.0.0",
        capability_catalog_digest="c" * 64,
        primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
        creative_dimension=CreativeDimension.HOOK_TRIGGER,
        steps=(
            RunPlanStep(
                step_id="inspect-route",
                order=1,
                capability_name="planning.viral.attention-grammar",
                capability_version="1.0.0",
                execution_mode=CapabilityExecutionMode.PLANNING_ONLY,
                guards=(
                    ArtifactAvailableGuard(handle=_artifact_handle()),
                    RouteIsGuard(
                        primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
                        creative_dimension=CreativeDimension.HOOK_TRIGGER,
                    ),
                    FactScopeSatisfiedGuard(evidence=_fact_evidence()),
                    MediaModeGuard(expected_mode=MediaMode.ANALYSIS_ONLY),
                ),
            ),
        ),
        input_refs=_plan_input_refs(),
        limitations=("local-only",),
    )


def _ready_snapshot() -> PrerequisiteSnapshot:
    return PrerequisiteSnapshot(
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=3,
        artifacts=(ArtifactSnapshot(handle=_artifact_handle()),),
        approvals=(),
        primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
        creative_dimension=CreativeDimension.HOOK_TRIGGER,
        fact_scope_evidence=_fact_evidence(),
        fact_scope_state=FactScopeState.SATISFIED,
        media_mode=MediaMode.ANALYSIS_ONLY,
    )


def test_evaluator_is_pure_ready_then_plan_complete() -> None:
    evaluator = OrchestrationEvaluator()
    plan = _guarded_plan()
    snapshot = _ready_snapshot()
    first = evaluator.evaluate(plan=plan, snapshot=snapshot, completed_step_ids=())
    repeated = evaluator.evaluate(plan=plan, snapshot=snapshot, completed_step_ids=())
    complete = evaluator.evaluate(
        plan=plan, snapshot=snapshot, completed_step_ids=("inspect-route",)
    )

    assert first == repeated
    assert first.disposition is OrchestrationDisposition.READY
    assert first.next_step_id == "inspect-route"
    assert complete.disposition is OrchestrationDisposition.PLAN_COMPLETE


def test_evaluator_rejects_non_contiguous_completed_step_prefix() -> None:
    source = _guarded_plan()
    plan = replace(
        source,
        steps=(source.steps[0], replace(source.steps[0], step_id="second", order=2)),
    )
    with pytest.raises(InvalidRunPlan, match="completed_step_invalid"):
        OrchestrationEvaluator().evaluate(
            plan=plan,
            snapshot=_ready_snapshot(),
            completed_step_ids=("second",),
        )


def test_evaluator_blocks_cross_scope_snapshot() -> None:
    snapshot = replace(
        _ready_snapshot(),
        task_id=UUID("00000000-0000-0000-0000-000000000999"),
    )
    decision = OrchestrationEvaluator().evaluate(
        plan=_guarded_plan(), snapshot=snapshot, completed_step_ids=()
    )
    assert decision.disposition is OrchestrationDisposition.BLOCKED
    assert decision.stable_codes == ("prerequisite_scope_mismatch",)


def test_evaluator_binds_snapshot_axis_to_plan_axis() -> None:
    decision = OrchestrationEvaluator().evaluate(
        plan=_guarded_plan(),
        snapshot=replace(
            _ready_snapshot(),
            primary_mechanism=PrimaryMechanism.TREND_NATIVE,
            creative_dimension=CreativeDimension.TEMPLATE_GRAMMAR,
        ),
        completed_step_ids=(),
    )
    assert decision.disposition is OrchestrationDisposition.BLOCKED
    assert decision.stable_codes == ("route_mismatch",)


def test_evaluator_blocks_conflicting_artifact_snapshot_order_independently() -> None:
    first = ArtifactSnapshot(handle=_artifact_handle())
    second = ArtifactSnapshot(handle=_artifact_handle(digest="d" * 64))
    evaluator = OrchestrationEvaluator()
    decisions = {
        evaluator.evaluate(
            plan=_guarded_plan(),
            snapshot=replace(_ready_snapshot(), artifacts=order),
            completed_step_ids=(),
        )
        for order in ((first, second), (second, first))
    }
    assert len(decisions) == 1
    decision = decisions.pop()
    assert decision.disposition is OrchestrationDisposition.BLOCKED
    assert decision.stable_codes == ("artifact_snapshot_conflict",)


def _approval_handle() -> ApprovalHandle:
    return ApprovalHandle(
        approval_request_id=APPROVAL_ID,
        request_version=1,
        request_digest="d" * 64,
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=3,
        gate_kind=ApprovalGateKind.REPLICATION_CONTRACT,
        artifact_type=ArtifactType.REPLICATION_CONTRACT,
        artifact_id="rc-001",
        artifact_version=1,
        artifact_digest="e" * 64,
        precondition_digest="f" * 64,
    )


def _approval_plan() -> RunPlan:
    return RunPlan.create(
        task_id=TASK_ID,
        task_revision=1,
        run_id=RUN_ID,
        run_revision=3,
        version=1,
        workflow_name="approval-test",
        workflow_version="1.0.0",
        capability_catalog_version="1.0.0",
        capability_catalog_digest="c" * 64,
        primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
        creative_dimension=CreativeDimension.HOOK_TRIGGER,
        steps=(
            RunPlanStep.approval_step(
                step_id="approve-contract",
                order=1,
                capability_name="planning.viral.contract-review",
                approval_handle=_approval_handle(),
            ),
        ),
        input_refs=_plan_input_refs(),
        limitations=("local-only",),
    )


def _approval_snapshot(
    *,
    decision: ApprovalDecision = ApprovalDecision.APPROVE,
    actor_kind: ActorKind = ActorKind.HUMAN,
    authority: ApprovalAuthority = ApprovalAuthority.VERIFIED_HUMAN,
    stale: bool = False,
    handle: ApprovalHandle | None = None,
) -> ApprovalSnapshot:
    return ApprovalSnapshot(
        handle=handle or _approval_handle(),
        decision=decision,
        actor_kind=actor_kind,
        authority=authority,
        stale=stale,
    )


def test_evaluator_requires_exact_verified_human_approval() -> None:
    evaluator = OrchestrationEvaluator()
    base = _ready_snapshot()
    plan = _approval_plan()
    missing = evaluator.evaluate(plan=plan, snapshot=base, completed_step_ids=())
    unverified = evaluator.evaluate(
        plan=plan,
        snapshot=replace(
            base,
            approvals=(_approval_snapshot(authority=ApprovalAuthority.UNVERIFIED_ATTRIBUTION),),
        ),
        completed_step_ids=(),
    )
    verified = evaluator.evaluate(
        plan=plan,
        snapshot=replace(base, approvals=(_approval_snapshot(),)),
        completed_step_ids=(),
    )

    assert missing.stable_codes == ("approval_required",)
    assert unverified.stable_codes == ("human_approval_required",)
    assert verified.disposition is OrchestrationDisposition.READY


@pytest.mark.parametrize(
    ("decision", "stale", "expected_disposition", "expected_code"),
    (
        (ApprovalDecision.REJECT, False, OrchestrationDisposition.BLOCKED, "approval_rejected"),
        (ApprovalDecision.STOP, False, OrchestrationDisposition.BLOCKED, "approval_rejected"),
        (
            ApprovalDecision.REQUEST_EVIDENCE,
            False,
            OrchestrationDisposition.AWAITING_INPUT,
            "approval_requested_evidence",
        ),
        (ApprovalDecision.APPROVE, True, OrchestrationDisposition.BLOCKED, "approval_stale"),
    ),
)
def test_evaluator_handles_all_non_ready_approval_states(
    decision: ApprovalDecision,
    stale: bool,
    expected_disposition: OrchestrationDisposition,
    expected_code: str,
) -> None:
    result = OrchestrationEvaluator().evaluate(
        plan=_approval_plan(),
        snapshot=replace(
            _ready_snapshot(),
            approvals=(_approval_snapshot(decision=decision, stale=stale),),
        ),
        completed_step_ids=(),
    )
    assert result.disposition is expected_disposition
    assert result.stable_codes == (expected_code,)


def test_approval_binding_mismatch_and_conflict_are_order_independent() -> None:
    mismatched = _approval_snapshot(
        handle=replace(_approval_handle(), precondition_digest="0" * 64)
    )
    approved = _approval_snapshot()
    stopped = _approval_snapshot(decision=ApprovalDecision.STOP)
    evaluator = OrchestrationEvaluator()
    plan = _approval_plan()
    base = _ready_snapshot()
    mismatch = evaluator.evaluate(
        plan=plan,
        snapshot=replace(base, approvals=(mismatched,)),
        completed_step_ids=(),
    )
    conflicts = {
        evaluator.evaluate(
            plan=plan,
            snapshot=replace(base, approvals=order),
            completed_step_ids=(),
        )
        for order in ((approved, stopped), (stopped, approved))
    }

    assert mismatch.stable_codes == ("approval_binding_mismatch",)
    assert len(conflicts) == 1
    conflict = conflicts.pop()
    assert conflict.disposition is OrchestrationDisposition.BLOCKED
    assert conflict.stable_codes == ("approval_snapshot_conflict",)
