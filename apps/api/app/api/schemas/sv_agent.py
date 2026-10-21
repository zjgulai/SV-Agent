from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.application.sv_agent_evidence_workspace import (
    EvidencePlaneKind,
    WorkspaceAvailability,
)
from app.application.sv_agent_mission_control import StageKey, StageStatus
from app.application.sv_agent_task_inbox import (
    TaskInboxLane,
    TaskInboxOrderingReason,
)
from app.domain.sv_agent.entities import (
    CreativeDimension,
    GoalTrack,
    PrimaryMechanism,
    RightsState,
    RunState,
    TargetPlatform,
)
from app.domain.sv_agent.runtime_records import (
    ApprovalGateKind,
    ArtifactStatus,
    ArtifactType,
    EffectClass,
    EvidenceLevel,
    ProofLevel,
    ToolRunStatus,
)


class TaskInboxItemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: UUID
    task_revision: int
    goal_track: GoalTrack
    subject: str
    decision_question: str
    active_run_id: UUID | None
    active_run_revision: int | None
    run_state: RunState | None
    pending_decision_count: int
    pending_gate_kinds: list[ApprovalGateKind]
    lane: TaskInboxLane
    ordering_reason: TaskInboxOrderingReason
    priority_at: datetime


class TaskInboxOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["sv-task-inbox/v1"]
    authority: Literal["postgresql"]
    ordering_policy_version: Literal["sv-task-inbox-order/v1"]
    items: list[TaskInboxItemOutput]
    truncated: bool


class PerformanceWindowOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: date
    end: date
    timezone: str


class MissionTaskOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: UUID
    task_revision: int
    goal_track: GoalTrack
    decision_question: str
    subject: str
    platform: TargetPlatform
    market: str
    language: str
    performance_window: PerformanceWindowOutput
    stop_condition: str
    initial_rights_state: RightsState


class MissionRunOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    run_revision: int
    task_revision: int
    state: RunState
    primary_mechanism: PrimaryMechanism | None
    creative_dimension: CreativeDimension | None
    updated_at: datetime


class MissionStageOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: StageKey
    label: str
    status: StageStatus


class MissionPlanStepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str
    order: int
    capability_name: str
    capability_version: str
    execution_mode: Literal["planning_only"]


class MissionPlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ref: str
    version: int
    run_revision: int
    workflow_name: str
    workflow_version: str
    capability_catalog_version: str
    steps: list[MissionPlanStepOutput]
    limitations: list[str]
    created_at: datetime


class MissionBlockerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    source_ref: str


class MissionNextSafeActionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    label: str
    reason: str
    reason_code: str
    interaction_intent: str | None
    basis_refs: list[str]
    explicit_non_effects: list[str]
    execution_available: Literal[False]


class MissionToolRunOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ref: str
    tool_name: str
    tool_version: str
    intent_summary: str
    effect_class: EffectClass
    status: ToolRunStatus
    stable_error_code: str | None
    recovery_action: str | None
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime


class MissionArtifactOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ref: str
    artifact_type: ArtifactType
    version: int
    status: ArtifactStatus
    evidence_level: EvidenceLevel
    proof_level: ProofLevel
    created_at: datetime


class MissionCitationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    ref: str


class MissionExplanationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str
    citations: list[MissionCitationOutput]


class MissionControlOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["sv-mission-control/v1"]
    authority: Literal["postgresql"]
    task: MissionTaskOutput
    run: MissionRunOutput | None
    stages: list[MissionStageOutput]
    current_stage: StageKey
    plan: MissionPlanOutput | None
    blockers: list[MissionBlockerOutput]
    next_safe_action: MissionNextSafeActionOutput
    tool_runs: list[MissionToolRunOutput]
    tool_runs_truncated: bool
    current_artifact: MissionArtifactOutput | None
    explanation: MissionExplanationOutput


class EvidenceWorkspaceTaskOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: UUID
    task_revision: int
    subject: str
    performance_window: PerformanceWindowOutput


class EvidenceWorkspaceRunOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    run_revision: int
    state: RunState


class EvidenceSubjectOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: str
    market: str | None
    locale: str | None
    limitations: list[str]


class EvidenceSourceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str


class EvidenceWindowOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: date
    end: date
    timezone: str
    basis: Literal["artifact_observation", "task_scope"]


class EvidenceArtifactNodeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ref: str
    artifact_type: ArtifactType
    version: int
    status: ArtifactStatus
    evidence_level: EvidenceLevel
    proof_level: ProofLevel
    created_at: datetime
    is_conclusion: bool
    sources: list[EvidenceSourceOutput]
    subject: EvidenceSubjectOutput
    window: EvidenceWindowOutput | None
    limitations: list[str]


class EvidenceArtifactEdgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_ref: str
    target_ref: str
    kind: Literal["declared_input", "runtime_verified"]
    verification_state: Literal["declared_only", "verified"]


class EvidenceArtifactGraphOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["available", "unavailable"]
    public_code: str
    nodes: list[EvidenceArtifactNodeOutput]
    edges: list[EvidenceArtifactEdgeOutput]
    limitations: list[str]


class EvidencePlaneOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvidencePlaneKind
    state: WorkspaceAvailability
    public_code: str
    source: str
    subject: EvidenceSubjectOutput | None
    window: EvidenceWindowOutput | None
    proof_level: ProofLevel | None
    limitations: list[str]


class EvidenceComparisonOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["unavailable"]
    public_code: Literal["COMPARISON_VERSION_REFS_UNAVAILABLE"]
    script_ref: None
    control_version_ref: None
    variant_version_ref: None
    limitations: list[str]


class EvidenceArtifactWorkspaceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["sv-evidence-artifacts/v1"]
    authority: Literal["postgresql"]
    task: EvidenceWorkspaceTaskOutput
    run: EvidenceWorkspaceRunOutput | None
    graph: EvidenceArtifactGraphOutput
    evidence_planes: list[EvidencePlaneOutput]
    comparison: EvidenceComparisonOutput
    explicit_non_effects: list[str]
