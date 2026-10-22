from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvApprovalRequestRecord,
    SvArtifactRecord,
    SvCommandReceiptRecord,
    SvDecisionEventRecord,
    SvRunPlanRecord,
    SvRunRecord,
    SvRuntimeLineageLinkRecord,
    SvTaskEventRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvToolJobLinkRecord,
    SvToolRunEventRecord,
    SvToolRunRecord,
)
from app.adapters.db.sv_agent_repository import SvAgentRepository
from app.api.routes import sv_agent as sv_agent_route
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import (
    EventDigestMismatch,
    EventSchemaUnsupported,
    JournalIntegrityError,
)
from app.domain.sv_agent.runtime_records import ActorKind, ActorStamp

_SV_RUNTIME_TABLES = (
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvRunRecord,
    SvRunPlanRecord,
    SvArtifactRecord,
    SvRuntimeLineageLinkRecord,
    SvApprovalRequestRecord,
    SvDecisionEventRecord,
    SvToolRunRecord,
    SvToolRunEventRecord,
    SvToolJobLinkRecord,
    SvCommandReceiptRecord,
    SvTaskEventRecord,
)


async def _runtime_row_counts(session: AsyncSession) -> tuple[int, ...]:
    counts: list[int] = []
    for model in _SV_RUNTIME_TABLES:
        value = await session.scalar(select(func.count()).select_from(model))
        counts.append(int(value or 0))
    return tuple(counts)


async def test_task_inbox_route_returns_only_the_read_only_persisted_projection(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    task = Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which Momcozy baby story should be tested next?",
            subject="Momcozy baby reaction story",
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
        id=UUID("24000000-0000-0000-0000-000000000001"),
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )
    await SvAgentRepository(db_session).create_task(
        task,
        idempotency_key="create-inbox-task",
        initiated_by=ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer"),
        executed_by=ActorStamp(kind=ActorKind.AGENT, ref="sv-agent"),
    )

    response = await client.get("/api/v1/sv-agent/tasks")

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "sv-task-inbox/v1",
        "authority": "postgresql",
        "ordering_policy_version": "sv-task-inbox-order/v1",
        "items": [
            {
                "task_id": str(task.id),
                "task_revision": 1,
                "goal_track": "brand_voice_social_resonance",
                "subject": "Momcozy baby reaction story",
                "decision_question": "Which Momcozy baby story should be tested next?",
                "active_run_id": None,
                "active_run_revision": None,
                "run_state": None,
                "pending_decision_count": 0,
                "pending_gate_kinds": [],
                "lane": "not_started",
                "ordering_reason": "run_not_started",
                "priority_at": "2026-10-21T08:00:00Z",
            }
        ],
        "truncated": False,
    }
    assert not {"render", "publish", "ship", "actions"} & set(response.json())


@pytest.mark.parametrize(
    ("error", "status", "code"),
    (
        (JournalIntegrityError("invalid current head"), 500, "JOURNAL_INTEGRITY_ERROR"),
        (SQLAlchemyError("database offline"), 503, "DATABASE_UNAVAILABLE"),
    ),
)
async def test_task_inbox_route_returns_stable_problem_details(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
) -> None:
    async def fail_inspection(_inbox: object) -> None:
        raise error

    monkeypatch.setattr(sv_agent_route.TaskInbox, "inspect", fail_inspection)

    response = await client.get("/api/v1/sv-agent/tasks")

    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


async def test_mission_control_route_returns_nested_read_only_task_projection(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    task = Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which Momcozy baby story should be tested next?",
            subject="Momcozy baby reaction story",
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
        id=UUID("24000000-0000-0000-0000-000000000002"),
        created_at=datetime(2026, 10, 21, 8, 30, tzinfo=UTC),
    )
    await SvAgentRepository(db_session).create_task(
        task,
        idempotency_key="create-mission-control-task",
        initiated_by=ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer"),
        executed_by=ActorStamp(kind=ActorKind.AGENT, ref="sv-agent"),
    )
    before = await _runtime_row_counts(db_session)

    response = await client.get(f"/api/v1/sv-agent/tasks/{task.id}")

    after = await _runtime_row_counts(db_session)
    assert response.status_code == 200
    assert after == before
    body = response.json()
    assert set(body) == {
        "schema_version",
        "authority",
        "task",
        "run",
        "stages",
        "current_stage",
        "plan",
        "blockers",
        "next_safe_action",
        "tool_runs",
        "tool_runs_truncated",
        "current_artifact",
        "explanation",
    }
    assert body["task"] == {
        "task_id": str(task.id),
        "task_revision": 1,
        "goal_track": "brand_voice_social_resonance",
        "decision_question": "Which Momcozy baby story should be tested next?",
        "subject": "Momcozy baby reaction story",
        "platform": "tiktok",
        "market": "US",
        "language": "en-US",
        "performance_window": {
            "start": "2026-10-01",
            "end": "2026-10-20",
            "timezone": "America/Los_Angeles",
        },
        "stop_condition": "Stop before provider execution or publication.",
        "initial_rights_state": "analysis_only",
    }
    assert body["run"] is None
    assert body["plan"] is None
    assert body["current_artifact"] is None
    assert len(body["stages"]) == 7
    assert body["current_stage"] == "reference_admission"
    assert body["next_safe_action"]["reason_code"] == "PLAN_REQUEST_PREVIEW_ONLY"
    assert body["next_safe_action"]["execution_available"] is False
    assert body["tool_runs"] == []
    assert body["tool_runs_truncated"] is False
    forbidden_keys = {
        "payload",
        "digest",
        "actor",
        "idempotency_key",
        "private_reasoning",
        "actions",
    }
    assert forbidden_keys.isdisjoint(_nested_keys(body))


async def test_evidence_artifact_route_returns_a_read_only_closed_projection(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    task = Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which Momcozy baby story should be tested next?",
            subject="Momcozy baby reaction story",
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
        id=UUID("24000000-0000-0000-0000-000000000003"),
        created_at=datetime(2026, 10, 21, 8, 45, tzinfo=UTC),
    )
    await SvAgentRepository(db_session).create_task(
        task,
        idempotency_key="create-evidence-workspace-task",
        initiated_by=ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer"),
        executed_by=ActorStamp(kind=ActorKind.AGENT, ref="sv-agent"),
    )
    before = await _runtime_row_counts(db_session)

    response = await client.get(f"/api/v1/sv-agent/tasks/{task.id}/artifacts")

    after = await _runtime_row_counts(db_session)
    assert response.status_code == 200
    assert after == before
    body = response.json()
    assert set(body) == {
        "schema_version",
        "authority",
        "task",
        "run",
        "graph",
        "evidence_planes",
        "comparison",
        "explicit_non_effects",
    }
    assert body["schema_version"] == "sv-evidence-artifacts/v1"
    assert body["authority"] == "postgresql"
    assert body["task"] == {
        "task_id": str(task.id),
        "task_revision": 1,
        "subject": "Momcozy baby reaction story",
        "performance_window": {
            "start": "2026-10-01",
            "end": "2026-10-20",
            "timezone": "America/Los_Angeles",
        },
    }
    assert body["run"] is None
    assert body["graph"]["public_code"] == "RUN_NOT_STARTED"
    assert [plane["kind"] for plane in body["evidence_planes"]] == [
        "product_truth",
        "performance",
        "experiment",
        "asset",
    ]
    assert body["comparison"] == {
        "state": "unavailable",
        "public_code": "COMPARISON_VERSION_REFS_UNAVAILABLE",
        "script_ref": None,
        "control_version_ref": None,
        "variant_version_ref": None,
        "limitations": [
            "No canonical artifact declares typed immutable Control and Variant ScriptVersion roles."
        ],
    }
    forbidden_keys = {
        "payload",
        "digest",
        "source_locator",
        "product_snapshot_id",
        "private_reasoning",
        "actions",
    }
    assert forbidden_keys.isdisjoint(_nested_keys(body))


async def test_evidence_artifact_route_returns_stable_task_not_found_problem(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/sv-agent/tasks/24000000-0000-0000-0000-000000000097/artifacts"
    )

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "TASK_NOT_FOUND"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    (
        (JournalIntegrityError("invalid graph"), 500, "JOURNAL_INTEGRITY_ERROR"),
        (SQLAlchemyError("database offline"), 503, "DATABASE_UNAVAILABLE"),
    ),
)
async def test_evidence_artifact_route_returns_stable_problem_details(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
) -> None:
    async def fail_inspection(_workspace: object, _task_id: UUID) -> None:
        raise error

    monkeypatch.setattr(
        sv_agent_route.EvidenceArtifactWorkspace,
        "inspect",
        fail_inspection,
    )

    response = await client.get(
        "/api/v1/sv-agent/tasks/24000000-0000-0000-0000-000000000096/artifacts"
    )

    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


async def test_approval_replay_route_returns_a_read_only_closed_projection(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    task = Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which Momcozy baby story should be reviewed next?",
            subject="Momcozy baby reaction story",
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
        id=UUID("24000000-0000-0000-0000-000000000004"),
        created_at=datetime(2026, 10, 21, 9, 0, tzinfo=UTC),
    )
    await SvAgentRepository(db_session).create_task(
        task,
        idempotency_key="create-approval-replay-task",
        initiated_by=ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer"),
        executed_by=ActorStamp(kind=ActorKind.AGENT, ref="sv-agent"),
    )
    before = await _runtime_row_counts(db_session)

    response = await client.get(f"/api/v1/sv-agent/tasks/{task.id}/replay")

    after = await _runtime_row_counts(db_session)
    assert response.status_code == 200
    assert after == before
    body = response.json()
    assert set(body) == {
        "schema_version",
        "authority",
        "task",
        "run",
        "summary",
        "decision_vocabulary",
        "decision_available",
        "approvals",
        "approvals_truncated",
        "timeline",
        "explicit_non_effects",
    }
    assert body["schema_version"] == "sv-approval-replay/v1"
    assert body["authority"] == "postgresql"
    assert body["task"] == {
        "task_id": str(task.id),
        "task_revision": 1,
        "subject": "Momcozy baby reaction story",
    }
    assert body["run"] is None
    assert body["summary"] == {"pending": 0, "decided": 0, "stale": 0}
    assert body["decision_vocabulary"] == [
        "approve",
        "reject",
        "request_evidence",
        "stop",
    ]
    assert body["decision_available"] is False
    assert body["approvals"] == []
    assert body["approvals_truncated"] is False
    assert [entry["kind"] for entry in body["timeline"]["entries"]] == ["task_event"]
    assert body["timeline"]["truncated"] is False
    assert body["explicit_non_effects"] == [
        "does_not_write_postgresql",
        "does_not_decide_approvals",
        "does_not_advance_task_or_run",
        "does_not_call_providers",
        "does_not_render_or_publish",
    ]
    forbidden_keys = {
        "payload",
        "digest",
        "request_digest",
        "artifact_id",
        "approval_request_id",
        "actor",
        "rationale",
        "private_reasoning",
        "actions",
    }
    assert forbidden_keys.isdisjoint(_nested_keys(body))


async def test_approval_replay_route_returns_stable_task_not_found_problem(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/sv-agent/tasks/24000000-0000-0000-0000-000000000095/replay"
    )

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "TASK_NOT_FOUND"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    (
        (
            EventSchemaUnsupported("unsupported replay schema"),
            500,
            "EVENT_SCHEMA_UNSUPPORTED",
        ),
        (EventDigestMismatch("invalid replay digest"), 500, "EVENT_DIGEST_MISMATCH"),
        (JournalIntegrityError("invalid replay binding"), 500, "JOURNAL_INTEGRITY_ERROR"),
        (SQLAlchemyError("database offline"), 503, "DATABASE_UNAVAILABLE"),
    ),
)
async def test_approval_replay_route_returns_stable_problem_details(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
) -> None:
    async def fail_inspection(_workspace: object, _task_id: UUID) -> None:
        raise error

    monkeypatch.setattr(
        sv_agent_route.ApprovalReplayWorkspace,
        "inspect",
        fail_inspection,
    )

    response = await client.get(
        "/api/v1/sv-agent/tasks/24000000-0000-0000-0000-000000000094/replay"
    )

    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


async def test_mission_control_route_returns_stable_task_not_found_problem(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/sv-agent/tasks/24000000-0000-0000-0000-000000000099")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "TASK_NOT_FOUND"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    (
        (JournalIntegrityError("invalid current head"), 500, "JOURNAL_INTEGRITY_ERROR"),
        (SQLAlchemyError("database offline"), 503, "DATABASE_UNAVAILABLE"),
    ),
)
async def test_mission_control_route_returns_stable_problem_details(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
) -> None:
    async def fail_inspection(_control: object, _task_id: UUID) -> None:
        raise error

    monkeypatch.setattr(sv_agent_route.MissionControl, "inspect", fail_inspection)

    response = await client.get("/api/v1/sv-agent/tasks/24000000-0000-0000-0000-000000000098")

    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code


def _nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {nested for child in value.values() for nested in _nested_keys(child)}
    if isinstance(value, list):
        return {nested for child in value for nested in _nested_keys(child)}
    return set()
