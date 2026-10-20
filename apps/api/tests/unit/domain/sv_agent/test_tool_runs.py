from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.sv_agent.runtime_records import ToolRunStatus
from app.domain.sv_agent.tool_runs import ToolArtifactRef, ToolRun

TASK_ID = UUID("31000000-0000-0000-0000-000000000001")
RUN_ID = UUID("31000000-0000-0000-0000-000000000002")
TOOL_RUN_ID = UUID("31000000-0000-0000-0000-000000000003")
CREATED_AT = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)


def _new_tool_run() -> ToolRun:
    return ToolRun.new(
        task_id=TASK_ID,
        task_revision=2,
        run_id=RUN_ID,
        run_revision=3,
        tool_name="product_truth.inspect",
        tool_version="1.0.0",
        intent_summary="Inspect authoritative product truth without changing it.",
        input_digest="a" * 64,
        id=TOOL_RUN_ID,
        created_at=CREATED_AT,
    )


def test_read_tool_run_has_immutable_intent_and_explicit_lifecycle() -> None:
    pending = _new_tool_run()

    assert pending.status is ToolRunStatus.PENDING
    assert pending.revision == 1
    assert pending.attempt_token == 1
    assert pending.artifact_refs == ()

    started = pending.start(at=CREATED_AT)
    completed = started.complete(
        artifact_refs=(
            ToolArtifactRef(
                artifact_type="product_snapshot",
                artifact_id="snapshot-1",
                artifact_version=1,
                artifact_digest="b" * 64,
            ),
        ),
        at=CREATED_AT,
    )

    assert started.status is ToolRunStatus.RUNNING
    assert started.revision == 2
    assert completed.status is ToolRunStatus.COMPLETED
    assert completed.revision == 3
    assert completed.tool_name == pending.tool_name
    assert completed.input_digest == pending.input_digest
    assert completed.stable_error_code is None
    assert completed.recovery_action is None


@pytest.mark.parametrize("terminal", ["failed", "unavailable"])
def test_non_successful_terminal_states_require_stable_recovery(
    terminal: str,
) -> None:
    started = _new_tool_run().start(at=CREATED_AT)

    transition = getattr(started, terminal)
    with pytest.raises(ValueError, match="stable_error"):
        transition(stable_error_code="", recovery_action="Retry later.", at=CREATED_AT)
    with pytest.raises(ValueError, match="recovery_action"):
        transition(
            stable_error_code="TOOL_READ_FAILED",
            recovery_action="",
            at=CREATED_AT,
        )


def test_tool_run_rejects_illegal_transitions_and_invalid_digests() -> None:
    pending = _new_tool_run()

    with pytest.raises(ValueError, match="transition"):
        pending.complete(at=CREATED_AT)
    with pytest.raises(ValueError, match="input_digest"):
        ToolRun.new(
            task_id=TASK_ID,
            task_revision=1,
            run_id=RUN_ID,
            run_revision=1,
            tool_name="product_truth.inspect",
            tool_version="1.0.0",
            intent_summary="Inspect product truth.",
            input_digest="not-a-digest",
        )


def test_tool_run_revision_must_match_its_lifecycle_state() -> None:
    pending = _new_tool_run()
    running = pending.start(at=CREATED_AT)

    with pytest.raises(ValueError, match="revision_status"):
        replace(pending, revision=2)
    with pytest.raises(ValueError, match="revision_status"):
        replace(running, revision=3)
