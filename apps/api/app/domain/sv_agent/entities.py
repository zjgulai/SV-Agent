from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.sv_agent.errors import (
    InvalidReplicationAxis,
    InvalidRunRevision,
    InvalidRunTransition,
    InvalidTaskBrief,
    InvalidTaskRevision,
)


class GoalTrack(StrEnum):
    PRODUCT_REPLICATION = "product_replication"
    BRAND_VOICE_SOCIAL_RESONANCE = "brand_voice_social_resonance"


class TargetPlatform(StrEnum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    OTHER = "other"


class RightsState(StrEnum):
    CONFIRMED_FOR_ANALYSIS = "confirmed_for_analysis"
    ANALYSIS_ONLY = "analysis_only"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"


class PrimaryMechanism(StrEnum):
    NARRATIVE_TRANSFORMATION = "narrative-transformation"
    PROOF_DEMONSTRATION = "proof-demonstration"
    EXPERIENCE_POV = "experience-pov"
    ATTENTION_GRAMMAR = "attention-grammar"
    CONVERSION_ACTION = "conversion-action"
    TREND_NATIVE = "trend-native"


class CreativeDimension(StrEnum):
    NARRATIVE_ARC = "narrative_arc"
    PROOF_DEVICE = "proof_device"
    EXPERIENCE_POV = "experience_pov"
    HOOK_TRIGGER = "hook_trigger"
    REVEAL_CADENCE = "reveal_cadence"
    CAPTION_CADENCE = "caption_cadence"
    VISUAL_CONTRAST = "visual_contrast"
    SONIC_TIMING = "sonic_timing"
    OBJECTION_RESOLUTION = "objection_resolution"
    PROMOTION_CONTRACT = "promotion_contract"
    CTA_INVITATION = "cta_invitation"
    ACTION_PATH = "action_path"
    TREND_SIGNAL_BINDING = "trend_signal_binding"
    TREND_SEMANTIC_FRAME = "trend_semantic_frame"
    TEMPLATE_GRAMMAR = "template_grammar"
    AUDIO_FUNCTION = "audio_function"


_MECHANISM_DIMENSIONS: dict[PrimaryMechanism, frozenset[CreativeDimension]] = {
    PrimaryMechanism.NARRATIVE_TRANSFORMATION: frozenset({CreativeDimension.NARRATIVE_ARC}),
    PrimaryMechanism.PROOF_DEMONSTRATION: frozenset({CreativeDimension.PROOF_DEVICE}),
    PrimaryMechanism.EXPERIENCE_POV: frozenset({CreativeDimension.EXPERIENCE_POV}),
    PrimaryMechanism.ATTENTION_GRAMMAR: frozenset(
        {
            CreativeDimension.HOOK_TRIGGER,
            CreativeDimension.REVEAL_CADENCE,
            CreativeDimension.CAPTION_CADENCE,
            CreativeDimension.VISUAL_CONTRAST,
            CreativeDimension.SONIC_TIMING,
        }
    ),
    PrimaryMechanism.CONVERSION_ACTION: frozenset(
        {
            CreativeDimension.OBJECTION_RESOLUTION,
            CreativeDimension.PROMOTION_CONTRACT,
            CreativeDimension.CTA_INVITATION,
            CreativeDimension.ACTION_PATH,
        }
    ),
    PrimaryMechanism.TREND_NATIVE: frozenset(
        {
            CreativeDimension.TREND_SIGNAL_BINDING,
            CreativeDimension.TREND_SEMANTIC_FRAME,
            CreativeDimension.TEMPLATE_GRAMMAR,
            CreativeDimension.AUDIO_FUNCTION,
        }
    ),
}


def dimensions_for_mechanism(
    primary_mechanism: PrimaryMechanism,
) -> frozenset[CreativeDimension]:
    if not isinstance(primary_mechanism, PrimaryMechanism):
        raise InvalidReplicationAxis("replication_axis_invalid")
    return _MECHANISM_DIMENSIONS[primary_mechanism]


@dataclass(frozen=True, slots=True)
class PerformanceWindow:
    start: date
    end: date
    timezone: str

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("performance_window_invalid")
        if not self.timezone.strip():
            raise ValueError("performance_window_timezone_required")


@dataclass(frozen=True, slots=True)
class TaskBrief:
    goal_track: GoalTrack
    decision_question: str
    subject: str
    platform: TargetPlatform
    market: str
    language: str
    performance_window: PerformanceWindow
    stop_condition: str
    initial_rights_state: RightsState

    def __post_init__(self) -> None:
        if not isinstance(self.goal_track, GoalTrack):
            raise InvalidTaskBrief("goal_track_invalid")
        if not isinstance(self.platform, TargetPlatform):
            raise InvalidTaskBrief("platform_invalid")
        if not isinstance(self.performance_window, PerformanceWindow):
            raise InvalidTaskBrief("performance_window_invalid")
        if not isinstance(self.initial_rights_state, RightsState):
            raise InvalidTaskBrief("initial_rights_state_invalid")
        required_fields = (
            self.decision_question,
            self.subject,
            self.market,
            self.language,
            self.stop_condition,
        )
        if any(not value or value != value.strip() for value in required_fields):
            raise InvalidTaskBrief("task_brief_field_required")
        if len(self.market) != 2 or not self.market.isalpha() or not self.market.isupper():
            raise InvalidTaskBrief("market_invalid")

    @classmethod
    def create(
        cls,
        *,
        goal_track: GoalTrack,
        decision_question: str,
        subject: str,
        platform: TargetPlatform,
        market: str,
        language: str,
        performance_window: PerformanceWindow,
        stop_condition: str,
        initial_rights_state: RightsState,
    ) -> "TaskBrief":
        if not isinstance(goal_track, GoalTrack):
            raise InvalidTaskBrief("goal_track_invalid")
        if not isinstance(platform, TargetPlatform):
            raise InvalidTaskBrief("platform_invalid")
        if not isinstance(performance_window, PerformanceWindow):
            raise InvalidTaskBrief("performance_window_invalid")
        if not isinstance(initial_rights_state, RightsState):
            raise InvalidTaskBrief("initial_rights_state_invalid")
        normalized = {
            "decision_question": decision_question.strip(),
            "subject": subject.strip(),
            "market": market.strip().upper(),
            "language": language.strip(),
            "stop_condition": stop_condition.strip(),
        }
        if any(not value for value in normalized.values()):
            raise InvalidTaskBrief("task_brief_field_required")
        if len(normalized["market"]) != 2 or not normalized["market"].isalpha():
            raise InvalidTaskBrief("market_invalid")
        return cls(
            goal_track=goal_track,
            decision_question=normalized["decision_question"],
            subject=normalized["subject"],
            platform=platform,
            market=normalized["market"],
            language=normalized["language"],
            performance_window=performance_window,
            stop_condition=normalized["stop_condition"],
            initial_rights_state=initial_rights_state,
        )


@dataclass(frozen=True, slots=True)
class Task:
    id: UUID
    revision: int
    brief: TaskBrief
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise InvalidTaskRevision("task revision must be positive")
        if not isinstance(self.brief, TaskBrief):
            raise InvalidTaskBrief("task_brief_invalid")

    @classmethod
    def new(
        cls,
        brief: TaskBrief,
        *,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> "Task":
        now = created_at or datetime.now(UTC)
        return cls(
            id=id or uuid4(),
            revision=1,
            brief=brief,
            created_at=now,
            updated_at=now,
        )

    def revise(
        self,
        brief: TaskBrief,
        *,
        updated_at: datetime | None = None,
    ) -> "Task":
        if not isinstance(brief, TaskBrief):
            raise InvalidTaskBrief("task_brief_invalid")
        return replace(
            self,
            revision=self.revision + 1,
            brief=brief,
            updated_at=updated_at or datetime.now(UTC),
        )


class RunState(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    AWAITING_INPUT = "awaiting_input"
    RUNNABLE = "runnable"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    COMPLETED_WITH_LIMITS = "completed_with_limits"
    FAILED = "failed"
    STOPPED = "stopped"


class RunStateSemantics(StrEnum):
    ORCHESTRATION = "orchestration"
    BUSINESS_DISPOSITION = "business_disposition"
    APPROVAL_PAUSE = "approval_pause"
    TECHNICAL_TERMINAL = "technical_terminal"


_RUN_STATE_SEMANTICS: dict[RunState, RunStateSemantics] = {
    RunState.DRAFT: RunStateSemantics.ORCHESTRATION,
    RunState.PLANNING: RunStateSemantics.ORCHESTRATION,
    RunState.AWAITING_INPUT: RunStateSemantics.ORCHESTRATION,
    RunState.RUNNABLE: RunStateSemantics.ORCHESTRATION,
    RunState.RUNNING: RunStateSemantics.ORCHESTRATION,
    RunState.AWAITING_APPROVAL: RunStateSemantics.APPROVAL_PAUSE,
    RunState.BLOCKED: RunStateSemantics.BUSINESS_DISPOSITION,
    RunState.COMPLETED_WITH_LIMITS: RunStateSemantics.BUSINESS_DISPOSITION,
    RunState.FAILED: RunStateSemantics.TECHNICAL_TERMINAL,
    RunState.STOPPED: RunStateSemantics.BUSINESS_DISPOSITION,
}


_RUN_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.DRAFT: frozenset({RunState.PLANNING}),
    RunState.PLANNING: frozenset(
        {
            RunState.AWAITING_INPUT,
            RunState.RUNNABLE,
            RunState.BLOCKED,
            RunState.STOPPED,
        }
    ),
    RunState.RUNNABLE: frozenset({RunState.RUNNING}),
    RunState.RUNNING: frozenset(
        {
            RunState.AWAITING_INPUT,
            RunState.AWAITING_APPROVAL,
            RunState.BLOCKED,
            RunState.COMPLETED_WITH_LIMITS,
            RunState.FAILED,
            RunState.STOPPED,
        }
    ),
    RunState.AWAITING_INPUT: frozenset({RunState.PLANNING, RunState.STOPPED}),
    RunState.AWAITING_APPROVAL: frozenset(
        {
            RunState.RUNNING,
            RunState.PLANNING,
            RunState.BLOCKED,
            RunState.STOPPED,
        }
    ),
    RunState.BLOCKED: frozenset({RunState.PLANNING, RunState.STOPPED}),
    RunState.FAILED: frozenset({RunState.PLANNING, RunState.STOPPED}),
}


@dataclass(frozen=True, slots=True)
class Run:
    id: UUID
    task_id: UUID
    task_revision: int
    revision: int
    state: RunState
    primary_mechanism: PrimaryMechanism | None
    creative_dimension: CreativeDimension | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.task_revision < 1:
            raise InvalidTaskRevision("task_revision must be positive")
        if self.revision < 1:
            raise InvalidRunRevision("run revision must be positive")
        if not isinstance(self.state, RunState):
            raise InvalidRunTransition("run_state_invalid")
        if (self.primary_mechanism is None) != (self.creative_dimension is None):
            raise InvalidReplicationAxis("replication_axis_incomplete")
        if self.primary_mechanism is not None:
            if not isinstance(self.primary_mechanism, PrimaryMechanism) or not isinstance(
                self.creative_dimension, CreativeDimension
            ):
                raise InvalidReplicationAxis("replication_axis_invalid")
            if self.creative_dimension not in _MECHANISM_DIMENSIONS[self.primary_mechanism]:
                raise InvalidReplicationAxis("mechanism_component_invalid")
        if self.state is RunState.DRAFT and self.primary_mechanism is not None:
            raise InvalidReplicationAxis("draft_cannot_have_replication_axis")
        if (
            self.state
            in {
                RunState.RUNNABLE,
                RunState.RUNNING,
                RunState.AWAITING_APPROVAL,
                RunState.COMPLETED_WITH_LIMITS,
                RunState.FAILED,
            }
            and self.primary_mechanism is None
        ):
            raise InvalidReplicationAxis("replication_axis_required")

    @classmethod
    def new(
        cls,
        *,
        task_id: UUID,
        task_revision: int,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> "Run":
        if task_revision < 1:
            raise InvalidTaskRevision("task_revision must be positive")
        now = created_at or datetime.now(UTC)
        return cls(
            id=id or uuid4(),
            task_id=task_id,
            task_revision=task_revision,
            revision=1,
            state=RunState.DRAFT,
            primary_mechanism=None,
            creative_dimension=None,
            created_at=now,
            updated_at=now,
        )

    def transition_to(self, state: RunState) -> "Run":
        if state not in _RUN_TRANSITIONS.get(self.state, frozenset()):
            raise InvalidRunTransition(f"{self.state} -> {state}")
        if state is RunState.RUNNABLE and (
            self.primary_mechanism is None or self.creative_dimension is None
        ):
            raise InvalidRunTransition("replication_axis_required")
        return replace(
            self,
            state=state,
            revision=self.revision + 1,
            updated_at=datetime.now(UTC),
        )

    @property
    def state_semantics(self) -> RunStateSemantics:
        return _RUN_STATE_SEMANTICS[self.state]

    def select_replication_axis(
        self,
        *,
        primary_mechanism: PrimaryMechanism,
        creative_dimension: CreativeDimension,
        updated_at: datetime | None = None,
    ) -> "Run":
        if self.state is not RunState.PLANNING:
            raise InvalidReplicationAxis("replication_axis_requires_planning")
        if self.primary_mechanism is not None or self.creative_dimension is not None:
            raise InvalidReplicationAxis("replication_axis_already_selected")
        if not isinstance(primary_mechanism, PrimaryMechanism) or not isinstance(
            creative_dimension, CreativeDimension
        ):
            raise InvalidReplicationAxis("replication_axis_invalid")
        if creative_dimension not in _MECHANISM_DIMENSIONS[primary_mechanism]:
            raise InvalidReplicationAxis("mechanism_component_invalid")
        return replace(
            self,
            primary_mechanism=primary_mechanism,
            creative_dimension=creative_dimension,
            revision=self.revision + 1,
            updated_at=updated_at or datetime.now(UTC),
        )
