from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvArtifactRecord,
    SvDecisionEventRecord,
    SvRunPlanRecord,
    SvRunRecord,
    SvTaskEventRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvToolRunEventRecord,
    SvToolRunRecord,
)
from app.application.sv_agent.approval_replay import ApprovalReplayWorkspace
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import JournalIntegrityError
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ActorStamp,
    DecisionEventType,
    TaskEventType,
    ToolRunEventType,
)

TASK_ID = UUID("31000000-0000-0000-0000-000000000001")
RUN_ID = UUID("31000000-0000-0000-0000-000000000002")
PLAN_ID = UUID("31000000-0000-0000-0000-000000000003")
ARTIFACT_ID = UUID("31000000-0000-0000-0000-000000000004")
APPROVAL_ID = UUID("31000000-0000-0000-0000-000000000005")
TOOL_RUN_ID = UUID("31000000-0000-0000-0000-000000000006")
HUMAN = ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer")
AGENT = ActorStamp(kind=ActorKind.AGENT, ref="sv-agent")


def _task(subject: str = "Momcozy baby reaction story") -> Task:
    return Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which Momcozy baby reaction story is ready for review?",
            subject=subject,
            platform=TargetPlatform.TIKTOK,
            market="US",
            language="en-US",
            performance_window=PerformanceWindow(
                start=date(2026, 10, 1),
                end=date(2026, 10, 20),
                timezone="America/Los_Angeles",
            ),
            stop_condition="Stop before provider execution or publication.",
            initial_rights_state=RightsState.ANALYSIS_ONLY,
        ),
        id=TASK_ID,
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )


async def _seed_reviewable_run(
    session: AsyncSession,
    *,
    decision_request_digest: str | None = None,
    limitation_message: str | None = None,
    approval_artifact_id: str | None = None,
    approval_artifact_digest: str | None = None,
    approval_artifact_type: str = "replication_contract",
    artifact_status: str = "awaiting_approval",
    tool_payload_id: str | None = None,
    tool_payload_overrides: dict[str, object] | None = None,
    tool_event_run_revision: int = 2,
    include_approval_event: bool = True,
    task_subject: str = "Momcozy baby reaction story",
) -> Task:
    task = _task(task_subject)
    created_at = datetime(2026, 10, 21, 8, 5, tzinfo=UTC)
    run = SvRunRecord(
        id=RUN_ID,
        task_id=task.id,
        task_revision=1,
        revision=2,
        state="awaiting_approval",
        primary_mechanism="experience-pov",
        creative_dimension="experience_pov",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(
        SvTaskRecord(
            id=task.id,
            current_revision=1,
            active_run_id=run.id,
            summary={"subject": task.brief.subject},
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    session.add(
        SvTaskRevisionRecord(
            task_id=task.id,
            revision=1,
            goal_track=task.brief.goal_track.value,
            decision_question=task.brief.decision_question,
            subject=task.brief.subject,
            platform=task.brief.platform.value,
            market=task.brief.market,
            language=task.brief.language,
            performance_start=task.brief.performance_window.start,
            performance_end=task.brief.performance_window.end,
            performance_timezone=task.brief.performance_window.timezone,
            stop_condition=task.brief.stop_condition,
            initial_rights_state=task.brief.initial_rights_state.value,
            brief_digest=canonical_digest(task.brief),
            created_at=task.created_at,
        )
    )
    await session.flush()
    session.add(run)
    await session.flush()

    created_payload = {"task_revision": 1}
    session.add(
        SvTaskEventRecord(
            id=UUID("31000000-0000-0000-0000-000000000009"),
            event_type=TaskEventType.TASK_CREATED.value,
            task_id=task.id,
            run_id=None,
            task_revision=1,
            run_revision=None,
            payload=created_payload,
            payload_digest=canonical_digest(created_payload),
            initiated_by_kind=HUMAN.kind.value,
            initiated_by_ref=HUMAN.ref,
            executed_by_kind=AGENT.kind.value,
            executed_by_ref=AGENT.ref,
            causation_receipt_id=None,
        )
    )
    await session.flush()

    plan_payload = {"schema_version": "sv-run-plan/v1", "summary": "Read-only review plan."}
    plan_digest = canonical_digest(plan_payload)
    session.add(
        SvRunPlanRecord(
            id=PLAN_ID,
            run_id=run.id,
            version=1,
            task_id=task.id,
            task_revision=1,
            run_revision=2,
            workflow_name="viral-replication.experience-pov",
            workflow_version="1.0.0",
            capability_catalog_version="1.0.0",
            plan_payload=plan_payload,
            plan_digest=plan_digest,
            input_refs=[],
            created_at=datetime(2026, 10, 21, 8, 6, tzinfo=UTC),
        )
    )
    artifact_payload = {"schema_version": "sv.replication-contract.v1"}
    artifact_digest = canonical_digest(artifact_payload)
    session.add(
        SvArtifactRecord(
            artifact_id=ARTIFACT_ID,
            version=1,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=2,
            artifact_type="replication_contract",
            schema_version="sv.replication-contract.v1",
            status=artifact_status,
            evidence_level="fact",
            proof_level="local",
            payload=artifact_payload,
            payload_digest=artifact_digest,
            input_refs=[],
            created_at=datetime(2026, 10, 21, 8, 7, tzinfo=UTC),
        )
    )
    request_digest = "a" * 64
    session.add(
        SvApprovalRequestRecord(
            id=APPROVAL_ID,
            request_version=1,
            request_digest=request_digest,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=2,
            gate_kind="replication_contract",
            artifact_type=approval_artifact_type,
            artifact_id=approval_artifact_id or str(ARTIFACT_ID),
            artifact_version=1,
            artifact_digest=approval_artifact_digest or artifact_digest,
            precondition_digest="b" * 64,
            predicted_effects=[{"effect": "allow_next_read_only_stage"}],
            explicit_non_effects=[{"effect": "publish"}],
            evidence_summary={"status": "bounded"},
            limitations=[
                {"message": limitation_message}
                if limitation_message is not None
                else {"code": "local_review_only"}
            ],
            stale_if=[{"field": "artifact_digest"}],
            created_at=datetime(2026, 10, 21, 8, 8, tzinfo=UTC),
        )
    )
    session.add(
        SvToolRunRecord(
            id=TOOL_RUN_ID,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=2,
            revision=1,
            tool_name="product_truth.inspect",
            tool_version="1.0.0",
            intent_summary="Read already-authoritative evidence.",
            input_digest="c" * 64,
            effect_class="read",
            approval_request_id=None,
            approval_request_version=None,
            idempotency_key=None,
            attempt_token=1,
            status="completed",
            artifact_refs=[],
            stable_error_code=None,
            recovery_action=None,
            started_at=datetime(2026, 10, 21, 8, 9, tzinfo=UTC),
            finished_at=datetime(2026, 10, 21, 8, 10, tzinfo=UTC),
        )
    )
    await session.flush()

    async def add_task_event(event_type: TaskEventType, payload: dict[str, object]) -> None:
        session.add(
            SvTaskEventRecord(
                id=UUID(int=UUID(event_type.value.encode().hex()[:32].ljust(32, "0")).int),
                event_type=event_type.value,
                task_id=task.id,
                run_id=run.id,
                task_revision=1,
                run_revision=2,
                payload=payload,
                payload_digest=canonical_digest(payload),
                initiated_by_kind=AGENT.kind.value,
                initiated_by_ref=AGENT.ref,
                executed_by_kind=AGENT.kind.value,
                executed_by_ref=AGENT.ref,
                causation_receipt_id=None,
            )
        )
        await session.flush()

    await add_task_event(
        TaskEventType.RUN_PLAN_RECORDED,
        {"run_plan_id": str(PLAN_ID), "version": 1, "digest": plan_digest},
    )
    await add_task_event(
        TaskEventType.ARTIFACT_RECORDED,
        {
            "artifact_id": str(ARTIFACT_ID),
            "artifact_type": "replication_contract",
            "version": 1,
            "digest": artifact_digest,
        },
    )
    if include_approval_event:
        await add_task_event(
            TaskEventType.APPROVAL_REQUESTED,
            {
                "approval_request_id": str(APPROVAL_ID),
                "request_version": 1,
                "request_digest": request_digest,
            },
        )

    tool_payload = {
        "artifact_refs": [],
        "attempt_token": 1,
        "input_digest": "c" * 64,
        "recovery_action": None,
        "result_digest": "d" * 64,
        "revision": 1,
        "stable_error_code": None,
        "status": "completed",
        "tool_name": "product_truth.inspect",
        "tool_run_id": tool_payload_id or str(TOOL_RUN_ID),
        "tool_version": "1.0.0",
    }
    tool_payload.update(tool_payload_overrides or {})
    session.add(
        SvToolRunEventRecord(
            id=UUID("31000000-0000-0000-0000-000000000007"),
            event_type=ToolRunEventType.COMPLETED.value,
            tool_run_id=TOOL_RUN_ID,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=tool_event_run_revision,
            attempt_token=1,
            payload=tool_payload,
            payload_digest=canonical_digest(tool_payload),
            initiated_by_kind=AGENT.kind.value,
            initiated_by_ref=AGENT.ref,
            executed_by_kind=AGENT.kind.value,
            executed_by_ref=AGENT.ref,
        )
    )
    await session.flush()

    decision_payload = {
        "approval_request_id": str(APPROVAL_ID),
        "decision": "approve",
    }
    session.add(
        SvDecisionEventRecord(
            id=UUID("31000000-0000-0000-0000-000000000008"),
            event_type=DecisionEventType.HUMAN_DECISION_RECORDED.value,
            approval_request_id=APPROVAL_ID,
            approval_request_version=1,
            request_digest=decision_request_digest or request_digest,
            task_id=task.id,
            task_revision=1,
            run_id=run.id,
            run_revision=2,
            decision="approve",
            rationale="Local review only.",
            payload=decision_payload,
            payload_digest=canonical_digest(decision_payload),
            decided_by_kind=HUMAN.kind.value,
            decided_by_ref=HUMAN.ref,
        )
    )
    await session.flush()
    return task


async def test_workspace_projects_version_bound_approval_and_ordered_replay(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(db_session)

    projection = await ApprovalReplayWorkspace(db_session).inspect(task.id)

    assert projection.schema_version == "sv-approval-replay/v1"
    assert projection.authority == "postgresql"
    assert projection.decision_vocabulary == (
        "approve",
        "reject",
        "request_evidence",
        "stop",
    )
    assert projection.decision_available is False
    assert projection.summary.pending == 0
    assert projection.summary.decided == 1
    assert projection.summary.stale == 0
    approval = projection.approvals[0]
    assert approval.gate_kind.value == "replication_contract"
    assert approval.target_artifact_type == "replication_contract"
    assert approval.target_version == 1
    assert approval.decision_state.value == "decided"
    assert approval.scope_state.value == "current"
    assert approval.decision is not None
    assert approval.decision.value == "approve"
    assert approval.predicted_effects == ("effect: allow_next_read_only_stage",)
    assert approval.explicit_non_effects == ("effect: publish",)
    assert approval.evidence == ("status: bounded",)
    assert approval.limitations == ("code: local_review_only",)
    assert approval.stale_conditions == ("field: artifact_digest",)

    kinds = [entry.kind.value for entry in projection.timeline.entries]
    assert kinds == [
        "task_event",
        "plan_revision",
        "artifact_revision",
        "approval_request",
        "tool_run",
        "decision",
    ]
    assert [entry.event_sequence for entry in projection.timeline.entries] == sorted(
        entry.event_sequence for entry in projection.timeline.entries
    )
    assert projection.timeline.truncated is False
    assert projection.explicit_non_effects == (
        "does_not_write_postgresql",
        "does_not_decide_approvals",
        "does_not_advance_task_or_run",
        "does_not_call_providers",
        "does_not_render_or_publish",
    )


async def test_workspace_fails_closed_on_decision_binding_drift(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(db_session, decision_request_digest="d" * 64)

    with pytest.raises(JournalIntegrityError, match="approval_decision_binding_invalid"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_private_paths_in_public_approval_statements(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(
        db_session,
        limitation_message="Review source at /Users/operator/private/source.mov",
    )

    with pytest.raises(JournalIntegrityError, match="approval_limitations_0_value_unsafe"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize(
    "limitation_message",
    (
        f"artifact {ARTIFACT_ID} is under review",
        f"digest {'e' * 64} was used",
        "source private/source.mov",
        r"source folder\secret.mov",
        r"source \\server\share\secret.mov",
        '{"foo":"bar"}',
        '["one","two"]',
        'payload {"token":"private-value"}',
        "JSON: [1,2]",
    ),
)
async def test_workspace_rejects_embedded_private_identifiers_in_public_statements(
    db_session: AsyncSession,
    limitation_message: str,
) -> None:
    task = await _seed_reviewable_run(
        db_session,
        limitation_message=limitation_message,
    )

    with pytest.raises(JournalIntegrityError, match="approval_limitations_0_value_unsafe"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize(
    "limitation_message",
    (
        "Bearer eyJhbGciOiJIUzI1NiJ9.private",
        "api key private-value",
        "secret private-value",
        "password hunter2",
        "Authorization: Bearer private-value",
        "credential private-value",
        "access_key private-value",
        "client_secret private-value",
    ),
)
async def test_workspace_rejects_credentials_in_public_statements(
    db_session: AsyncSession,
    limitation_message: str,
) -> None:
    task = await _seed_reviewable_run(
        db_session,
        limitation_message=limitation_message,
    )

    with pytest.raises(JournalIntegrityError, match="approval_limitations_0_value_unsafe"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize(
    "task_subject",
    (
        f"subject {ARTIFACT_ID}",
        f"subject {'e' * 64}",
        "subject private/source.mov",
        "Bearer private-token",
        '{"subject":"private"}',
    ),
)
async def test_workspace_rejects_unsafe_task_subjects(
    db_session: AsyncSession,
    task_subject: str,
) -> None:
    task = await _seed_reviewable_run(db_session, task_subject=task_subject)

    with pytest.raises(JournalIntegrityError, match="approval_task_subject_unsafe"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("approval_artifact_id", "31000000-0000-0000-0000-000000000099"),
        ("approval_artifact_digest", "f" * 64),
    ),
)
async def test_workspace_fails_closed_when_approval_target_binding_drifts(
    db_session: AsyncSession,
    field: str,
    value: str,
) -> None:
    task = await _seed_reviewable_run(db_session, **{field: value})

    with pytest.raises(JournalIntegrityError, match="approval_target_binding_invalid"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize("artifact_status", ("stale", "superseded"))
async def test_workspace_marks_an_inactive_target_as_stale(
    db_session: AsyncSession,
    artifact_status: str,
) -> None:
    task = await _seed_reviewable_run(db_session, artifact_status=artifact_status)

    projection = await ApprovalReplayWorkspace(db_session).inspect(task.id)

    assert projection.approvals[0].scope_state.value == "stale"
    assert projection.summary.stale == 1


async def test_workspace_marks_a_target_with_a_newer_version_as_stale(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(db_session)
    artifact_payload = {
        "schema_version": "sv.replication-contract.v1",
        "revision_note": "newer bounded version",
    }
    artifact_digest = canonical_digest(artifact_payload)
    db_session.add(
        SvArtifactRecord(
            artifact_id=ARTIFACT_ID,
            version=2,
            task_id=task.id,
            task_revision=1,
            run_id=RUN_ID,
            run_revision=2,
            artifact_type="replication_contract",
            schema_version="sv.replication-contract.v1",
            status="awaiting_approval",
            evidence_level="fact",
            proof_level="local",
            payload=artifact_payload,
            payload_digest=artifact_digest,
            input_refs=[],
            created_at=datetime(2026, 10, 21, 8, 11, tzinfo=UTC),
        )
    )
    event_payload = {
        "artifact_id": str(ARTIFACT_ID),
        "artifact_type": "replication_contract",
        "version": 2,
        "digest": artifact_digest,
    }
    db_session.add(
        SvTaskEventRecord(
            id=UUID("31000000-0000-0000-0000-000000000011"),
            event_type=TaskEventType.ARTIFACT_RECORDED.value,
            task_id=task.id,
            run_id=RUN_ID,
            task_revision=1,
            run_revision=2,
            payload=event_payload,
            payload_digest=canonical_digest(event_payload),
            initiated_by_kind=AGENT.kind.value,
            initiated_by_ref=AGENT.ref,
            executed_by_kind=AGENT.kind.value,
            executed_by_ref=AGENT.ref,
            causation_receipt_id=None,
        )
    )
    await db_session.flush()

    projection = await ApprovalReplayWorkspace(db_session).inspect(task.id)

    assert projection.approvals[0].scope_state.value == "stale"
    assert projection.summary.stale == 1


@pytest.mark.parametrize(
    "approval_artifact_type",
    ("script_version", "storyboard_version", "../../private"),
)
async def test_workspace_rejects_unknown_approval_target_types(
    db_session: AsyncSession,
    approval_artifact_type: str,
) -> None:
    task = await _seed_reviewable_run(
        db_session,
        approval_artifact_type=approval_artifact_type,
    )

    with pytest.raises(JournalIntegrityError, match="approval_target_type_unknown"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_tool_run_event_payload_binding_drift(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(
        db_session,
        tool_payload_id="31000000-0000-0000-0000-000000000099",
    )

    with pytest.raises(JournalIntegrityError, match="tool_run_event_binding_invalid"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("status", "running"),
        ("revision", 2),
        ("attempt_token", 2),
        ("input_digest", "e" * 64),
        ("tool_name", "product_truth.other"),
        ("tool_version", "2.0.0"),
    ),
)
async def test_workspace_rejects_tool_run_payload_contract_drift(
    db_session: AsyncSession,
    field: str,
    value: object,
) -> None:
    task = await _seed_reviewable_run(
        db_session,
        tool_payload_overrides={field: value},
    )

    with pytest.raises(JournalIntegrityError, match="tool_run_event_binding_invalid"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_tool_run_scope_drift(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(db_session, tool_event_run_revision=3)

    with pytest.raises(JournalIntegrityError, match="tool_run_event_binding_invalid"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_approval_rows_without_a_journal_event(
    db_session: AsyncSession,
) -> None:
    task = await _seed_reviewable_run(db_session, include_approval_event=False)

    with pytest.raises(JournalIntegrityError, match="approval_event_missing"):
        await ApprovalReplayWorkspace(db_session).inspect(task.id)


async def test_workspace_fails_closed_when_event_highwater_changes_mid_projection(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = await _seed_reviewable_run(db_session)
    workspace = ApprovalReplayWorkspace(db_session)
    original = workspace._load_decisions

    async def load_then_append_event(
        approvals: tuple[SvApprovalRequestRecord, ...],
        through_sequence: int,
    ) -> dict[tuple[UUID, int], SvDecisionEventRecord]:
        decisions = await original(approvals, through_sequence)
        payload = {"state": "awaiting_approval"}
        db_session.add(
            SvTaskEventRecord(
                id=UUID("31000000-0000-0000-0000-000000000010"),
                event_type=TaskEventType.RUN_STATE_TRANSITIONED.value,
                task_id=task.id,
                run_id=RUN_ID,
                task_revision=1,
                run_revision=2,
                payload=payload,
                payload_digest=canonical_digest(payload),
                initiated_by_kind=AGENT.kind.value,
                initiated_by_ref=AGENT.ref,
                executed_by_kind=AGENT.kind.value,
                executed_by_ref=AGENT.ref,
                causation_receipt_id=None,
            )
        )
        await db_session.flush()
        return decisions

    monkeypatch.setattr(workspace, "_load_decisions", load_then_append_event)

    with pytest.raises(JournalIntegrityError, match="approval_replay_snapshot_changed"):
        await workspace.inspect(task.id)


async def test_workspace_fails_closed_when_run_head_changes_mid_projection(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = await _seed_reviewable_run(db_session)
    workspace = ApprovalReplayWorkspace(db_session)
    original = workspace._load_decisions

    async def load_then_change_run(
        approvals: tuple[SvApprovalRequestRecord, ...],
        through_sequence: int,
    ) -> dict[tuple[UUID, int], SvDecisionEventRecord]:
        decisions = await original(approvals, through_sequence)
        await db_session.execute(
            update(SvRunRecord)
            .where(SvRunRecord.id == RUN_ID)
            .values(
                revision=3,
                state="blocked",
                updated_at=datetime(2026, 10, 21, 8, 11, tzinfo=UTC),
            )
        )
        return decisions

    monkeypatch.setattr(workspace, "_load_decisions", load_then_change_run)

    with pytest.raises(JournalIntegrityError, match="approval_replay_snapshot_changed"):
        await workspace.inspect(task.id)
