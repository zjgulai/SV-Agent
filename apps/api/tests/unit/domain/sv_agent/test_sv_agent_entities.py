from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.domain.sv_agent.entities import (
    CreativeDimension,
    GoalTrack,
    PerformanceWindow,
    PrimaryMechanism,
    RightsState,
    Run,
    RunState,
    RunStateSemantics,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import (
    InvalidReplicationAxis,
    InvalidRunRevision,
    InvalidRunTransition,
    InvalidTaskBrief,
    InvalidTaskRevision,
)

TASK_ID = UUID("00000000-0000-0000-0000-000000000101")


def _brief(goal_track: GoalTrack = GoalTrack.PRODUCT_REPLICATION) -> TaskBrief:
    return TaskBrief.create(
        goal_track=goal_track,
        decision_question="Which bounded creative mechanism should this run test?",
        subject="Momcozy baby-care social content",
        platform=TargetPlatform.TIKTOK,
        market="us",
        language="en-US",
        performance_window=PerformanceWindow(
            start=date(2026, 10, 1),
            end=date(2026, 10, 7),
            timezone="America/Los_Angeles",
        ),
        stop_condition="Stop when the review-ready package is complete or blocked.",
        initial_rights_state=RightsState.ANALYSIS_ONLY,
    )


def test_new_run_starts_in_draft_and_can_enter_planning() -> None:
    run = Run.new(task_id=TASK_ID, task_revision=1)

    assert run.state is RunState.DRAFT
    assert run.transition_to(RunState.PLANNING).state is RunState.PLANNING


LEGAL_TRANSITIONS = {
    (RunState.DRAFT, RunState.PLANNING),
    (RunState.PLANNING, RunState.AWAITING_INPUT),
    (RunState.PLANNING, RunState.RUNNABLE),
    (RunState.PLANNING, RunState.BLOCKED),
    (RunState.PLANNING, RunState.STOPPED),
    (RunState.RUNNABLE, RunState.RUNNING),
    (RunState.RUNNING, RunState.AWAITING_INPUT),
    (RunState.RUNNING, RunState.AWAITING_APPROVAL),
    (RunState.RUNNING, RunState.BLOCKED),
    (RunState.RUNNING, RunState.COMPLETED_WITH_LIMITS),
    (RunState.RUNNING, RunState.FAILED),
    (RunState.RUNNING, RunState.STOPPED),
    (RunState.AWAITING_INPUT, RunState.PLANNING),
    (RunState.AWAITING_INPUT, RunState.STOPPED),
    (RunState.AWAITING_APPROVAL, RunState.RUNNING),
    (RunState.AWAITING_APPROVAL, RunState.PLANNING),
    (RunState.AWAITING_APPROVAL, RunState.BLOCKED),
    (RunState.AWAITING_APPROVAL, RunState.STOPPED),
    (RunState.BLOCKED, RunState.PLANNING),
    (RunState.BLOCKED, RunState.STOPPED),
    (RunState.FAILED, RunState.PLANNING),
    (RunState.FAILED, RunState.STOPPED),
}

PATHS_FROM_DRAFT = {
    RunState.DRAFT: (),
    RunState.PLANNING: (RunState.PLANNING,),
    RunState.AWAITING_INPUT: (RunState.PLANNING, RunState.AWAITING_INPUT),
    RunState.RUNNABLE: (RunState.PLANNING, RunState.RUNNABLE),
    RunState.RUNNING: (RunState.PLANNING, RunState.RUNNABLE, RunState.RUNNING),
    RunState.AWAITING_APPROVAL: (
        RunState.PLANNING,
        RunState.RUNNABLE,
        RunState.RUNNING,
        RunState.AWAITING_APPROVAL,
    ),
    RunState.BLOCKED: (RunState.PLANNING, RunState.BLOCKED),
    RunState.COMPLETED_WITH_LIMITS: (
        RunState.PLANNING,
        RunState.RUNNABLE,
        RunState.RUNNING,
        RunState.COMPLETED_WITH_LIMITS,
    ),
    RunState.FAILED: (
        RunState.PLANNING,
        RunState.RUNNABLE,
        RunState.RUNNING,
        RunState.FAILED,
    ),
    RunState.STOPPED: (RunState.PLANNING, RunState.STOPPED),
}


def _run_at(state: RunState) -> Run:
    run = Run.new(task_id=TASK_ID, task_revision=1)
    for next_state in PATHS_FROM_DRAFT[state]:
        if next_state is RunState.RUNNABLE:
            run = _select_default_axis(run)
        run = run.transition_to(next_state)
    return run


def _select_default_axis(run: Run) -> Run:
    return run.select_replication_axis(
        primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
        creative_dimension=CreativeDimension.HOOK_TRIGGER,
    )


@pytest.mark.parametrize(("source", "target"), sorted(LEGAL_TRANSITIONS))
def test_run_accepts_every_specified_transition(source: RunState, target: RunState) -> None:
    run = _run_at(source)
    if source is RunState.PLANNING and target is RunState.RUNNABLE:
        run = _select_default_axis(run)
    assert run.transition_to(target).state is target


INVALID_TRANSITIONS = sorted(
    (source, target)
    for source in RunState
    for target in RunState
    if (source, target) not in LEGAL_TRANSITIONS
)


@pytest.mark.parametrize(("source", "target"), INVALID_TRANSITIONS)
def test_run_rejects_every_unspecified_transition(source: RunState, target: RunState) -> None:
    with pytest.raises(InvalidRunTransition, match=f"{source} -> {target}"):
        _run_at(source).transition_to(target)


def test_succeeded_is_not_a_run_state() -> None:
    assert "succeeded" not in RunState


REPRESENTATIVE_REPLICATION_AXES = (
    (PrimaryMechanism.NARRATIVE_TRANSFORMATION, CreativeDimension.NARRATIVE_ARC),
    (PrimaryMechanism.PROOF_DEMONSTRATION, CreativeDimension.PROOF_DEVICE),
    (PrimaryMechanism.EXPERIENCE_POV, CreativeDimension.EXPERIENCE_POV),
    (PrimaryMechanism.ATTENTION_GRAMMAR, CreativeDimension.HOOK_TRIGGER),
    (PrimaryMechanism.CONVERSION_ACTION, CreativeDimension.CTA_INVITATION),
    (PrimaryMechanism.TREND_NATIVE, CreativeDimension.TEMPLATE_GRAMMAR),
)

VALID_REPLICATION_AXES = {
    (PrimaryMechanism.NARRATIVE_TRANSFORMATION, CreativeDimension.NARRATIVE_ARC),
    (PrimaryMechanism.PROOF_DEMONSTRATION, CreativeDimension.PROOF_DEVICE),
    (PrimaryMechanism.EXPERIENCE_POV, CreativeDimension.EXPERIENCE_POV),
    (PrimaryMechanism.ATTENTION_GRAMMAR, CreativeDimension.HOOK_TRIGGER),
    (PrimaryMechanism.ATTENTION_GRAMMAR, CreativeDimension.REVEAL_CADENCE),
    (PrimaryMechanism.ATTENTION_GRAMMAR, CreativeDimension.CAPTION_CADENCE),
    (PrimaryMechanism.ATTENTION_GRAMMAR, CreativeDimension.VISUAL_CONTRAST),
    (PrimaryMechanism.ATTENTION_GRAMMAR, CreativeDimension.SONIC_TIMING),
    (PrimaryMechanism.CONVERSION_ACTION, CreativeDimension.OBJECTION_RESOLUTION),
    (PrimaryMechanism.CONVERSION_ACTION, CreativeDimension.PROMOTION_CONTRACT),
    (PrimaryMechanism.CONVERSION_ACTION, CreativeDimension.CTA_INVITATION),
    (PrimaryMechanism.CONVERSION_ACTION, CreativeDimension.ACTION_PATH),
    (PrimaryMechanism.TREND_NATIVE, CreativeDimension.TREND_SIGNAL_BINDING),
    (PrimaryMechanism.TREND_NATIVE, CreativeDimension.TREND_SEMANTIC_FRAME),
    (PrimaryMechanism.TREND_NATIVE, CreativeDimension.TEMPLATE_GRAMMAR),
    (PrimaryMechanism.TREND_NATIVE, CreativeDimension.AUDIO_FUNCTION),
}


@pytest.mark.parametrize("goal_track", tuple(GoalTrack))
@pytest.mark.parametrize(
    ("primary_mechanism", "creative_dimension"), REPRESENTATIVE_REPLICATION_AXES
)
def test_task_goal_track_is_independent_from_run_replication_axis(
    goal_track: GoalTrack,
    primary_mechanism: PrimaryMechanism,
    creative_dimension: CreativeDimension,
) -> None:
    task = Task.new(_brief(goal_track))
    run = Run.new(task_id=task.id, task_revision=task.revision)
    run = run.transition_to(RunState.PLANNING).select_replication_axis(
        primary_mechanism=primary_mechanism,
        creative_dimension=creative_dimension,
    )

    assert task.brief.goal_track is goal_track
    assert run.primary_mechanism is primary_mechanism
    assert run.creative_dimension is creative_dimension
    assert run.task_id == task.id
    assert run.task_revision == task.revision


def test_task_brief_normalizes_market_without_changing_goal_semantics() -> None:
    brief = _brief(GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE)

    assert brief.market == "US"
    assert brief.goal_track is GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE


def test_task_brief_rejects_a_primary_mechanism_as_a_goal_track() -> None:
    with pytest.raises(InvalidTaskBrief) as exc_info:
        TaskBrief.create(
            goal_track=PrimaryMechanism.ATTENTION_GRAMMAR,  # type: ignore[arg-type]
            decision_question="What should this test?",
            subject="Momcozy baby-care social content",
            platform=TargetPlatform.TIKTOK,
            market="US",
            language="en-US",
            performance_window=PerformanceWindow(
                start=date(2026, 10, 1),
                end=date(2026, 10, 7),
                timezone="America/Los_Angeles",
            ),
            stop_condition="Stop at the declared gate.",
            initial_rights_state=RightsState.ANALYSIS_ONLY,
        )

    assert exc_info.value.code == "TASK_BRIEF_INVALID"


def test_task_brief_rejects_blank_required_fields() -> None:
    with pytest.raises(InvalidTaskBrief, match="task_brief_field_required"):
        TaskBrief.create(
            goal_track=GoalTrack.PRODUCT_REPLICATION,
            decision_question=" ",
            subject="Momcozy baby-care social content",
            platform=TargetPlatform.TIKTOK,
            market="US",
            language="en-US",
            performance_window=PerformanceWindow(
                start=date(2026, 10, 1),
                end=date(2026, 10, 7),
                timezone="America/Los_Angeles",
            ),
            stop_condition="Stop at the declared gate.",
            initial_rights_state=RightsState.ANALYSIS_ONLY,
        )


def test_task_revision_returns_a_new_immutable_task_snapshot() -> None:
    created_at = datetime(2026, 10, 21, tzinfo=UTC)
    updated_at = datetime(2026, 10, 22, tzinfo=UTC)
    original = Task.new(_brief(), id=TASK_ID, created_at=created_at)

    revised = original.revise(
        _brief(GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE),
        updated_at=updated_at,
    )

    assert revised.id == original.id
    assert revised.revision == 2
    assert revised.brief.goal_track is GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE
    assert revised.created_at == created_at
    assert revised.updated_at == updated_at
    assert original.revision == 1
    assert original.brief.goal_track is GoalTrack.PRODUCT_REPLICATION


@pytest.mark.parametrize(("primary_mechanism", "creative_dimension"), VALID_REPLICATION_AXES)
def test_run_accepts_each_closed_replication_axis(
    primary_mechanism: PrimaryMechanism,
    creative_dimension: CreativeDimension,
) -> None:
    run = _run_at(RunState.PLANNING).select_replication_axis(
        primary_mechanism=primary_mechanism,
        creative_dimension=creative_dimension,
    )

    assert (run.primary_mechanism, run.creative_dimension) == (
        primary_mechanism,
        creative_dimension,
    )


INVALID_REPLICATION_AXES = sorted(
    (primary_mechanism, creative_dimension)
    for primary_mechanism in PrimaryMechanism
    for creative_dimension in CreativeDimension
    if (primary_mechanism, creative_dimension) not in VALID_REPLICATION_AXES
)


@pytest.mark.parametrize(("primary_mechanism", "creative_dimension"), INVALID_REPLICATION_AXES)
def test_run_rejects_cross_mechanism_creative_dimensions(
    primary_mechanism: PrimaryMechanism,
    creative_dimension: CreativeDimension,
) -> None:
    with pytest.raises(InvalidReplicationAxis) as exc_info:
        _run_at(RunState.PLANNING).select_replication_axis(
            primary_mechanism=primary_mechanism,
            creative_dimension=creative_dimension,
        )

    assert exc_info.value.code == "REPLICATION_AXIS_INVALID"


def test_run_rejects_an_unknown_primary_mechanism_with_a_stable_error() -> None:
    with pytest.raises(InvalidReplicationAxis) as exc_info:
        _run_at(RunState.PLANNING).select_replication_axis(
            primary_mechanism="not-a-mechanism",  # type: ignore[arg-type]
            creative_dimension=CreativeDimension.HOOK_TRIGGER,
        )

    assert exc_info.value.code == "REPLICATION_AXIS_INVALID"


def test_run_cannot_replace_its_selected_replication_axis() -> None:
    run = _select_default_axis(_run_at(RunState.PLANNING))

    with pytest.raises(InvalidReplicationAxis, match="replication_axis_already_selected"):
        run.select_replication_axis(
            primary_mechanism=PrimaryMechanism.PROOF_DEMONSTRATION,
            creative_dimension=CreativeDimension.PROOF_DEVICE,
        )


def test_run_revision_advances_without_mutating_the_previous_value() -> None:
    draft = Run.new(task_id=TASK_ID, task_revision=1)
    planning = draft.transition_to(RunState.PLANNING)
    routed = _select_default_axis(planning)

    assert (draft.revision, planning.revision, routed.revision) == (1, 2, 3)
    assert draft.state is RunState.DRAFT
    assert planning.primary_mechanism is None


def test_run_cannot_become_runnable_without_a_replication_axis() -> None:
    run = _run_at(RunState.PLANNING)

    with pytest.raises(InvalidRunTransition, match="replication_axis_required"):
        run.transition_to(RunState.RUNNABLE)


def test_run_requires_a_positive_task_revision() -> None:
    with pytest.raises(InvalidTaskRevision) as exc_info:
        Run.new(task_id=TASK_ID, task_revision=0)

    assert exc_info.value.code == "TASK_REVISION_INVALID"


def test_rehydrated_run_rejects_an_invalid_replication_axis() -> None:
    now = datetime(2026, 10, 21, tzinfo=UTC)

    with pytest.raises(InvalidReplicationAxis, match="mechanism_component_invalid"):
        Run(
            id=UUID("00000000-0000-0000-0000-000000000102"),
            task_id=TASK_ID,
            task_revision=1,
            revision=1,
            state=RunState.PLANNING,
            primary_mechanism=PrimaryMechanism.ATTENTION_GRAMMAR,
            creative_dimension=CreativeDimension.PROOF_DEVICE,
            created_at=now,
            updated_at=now,
        )


def test_rehydrated_run_requires_a_positive_run_revision() -> None:
    now = datetime(2026, 10, 21, tzinfo=UTC)

    with pytest.raises(InvalidRunRevision) as exc_info:
        Run(
            id=UUID("00000000-0000-0000-0000-000000000102"),
            task_id=TASK_ID,
            task_revision=1,
            revision=0,
            state=RunState.DRAFT,
            primary_mechanism=None,
            creative_dimension=None,
            created_at=now,
            updated_at=now,
        )

    assert exc_info.value.code == "RUN_REVISION_INVALID"


@pytest.mark.parametrize(
    ("state", "semantics"),
    (
        (RunState.RUNNING, RunStateSemantics.ORCHESTRATION),
        (RunState.BLOCKED, RunStateSemantics.BUSINESS_DISPOSITION),
        (RunState.COMPLETED_WITH_LIMITS, RunStateSemantics.BUSINESS_DISPOSITION),
        (RunState.STOPPED, RunStateSemantics.BUSINESS_DISPOSITION),
        (RunState.AWAITING_APPROVAL, RunStateSemantics.APPROVAL_PAUSE),
        (RunState.FAILED, RunStateSemantics.TECHNICAL_TERMINAL),
    ),
)
def test_run_state_keeps_technical_business_and_approval_semantics_separate(
    state: RunState, semantics: RunStateSemantics
) -> None:
    assert _run_at(state).state_semantics is semantics


def test_invalid_transition_preserves_the_original_run_and_has_a_stable_code() -> None:
    original = _run_at(RunState.RUNNING)

    with pytest.raises(InvalidRunTransition) as exc_info:
        original.transition_to(RunState.PLANNING)

    assert exc_info.value.code == "RUN_TRANSITION_INVALID"
    assert original.state is RunState.RUNNING
