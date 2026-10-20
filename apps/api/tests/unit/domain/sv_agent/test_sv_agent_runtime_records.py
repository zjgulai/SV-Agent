from uuid import UUID

import pytest

from app.domain.sv_agent.errors import JournalIntegrityError
from app.domain.sv_agent.runtime_records import (
    ActorKind,
    ActorStamp,
    EventStream,
    ReplayEntry,
    ReplayQuery,
    TaskEventType,
)

TASK_ID = UUID("00000000-0000-0000-0000-000000000101")


def test_replay_entry_accepts_a_known_factual_task_event() -> None:
    entry = ReplayEntry(
        event_id=UUID("00000000-0000-0000-0000-000000000102"),
        event_sequence=7,
        stream=EventStream.TASK,
        event_type=TaskEventType.TASK_CREATED,
        task_id=TASK_ID,
        run_id=None,
        task_revision=1,
        run_revision=None,
        payload={
            "brief_digest": "a" * 64,
            "task_revision_ref": f"{TASK_ID}:1",
            "to_revision": 1,
        },
        payload_digest="2c06237d0e42cec09c76bca3e7ea8c9bd39d9fed5f3d92ba389be8bdc3f840d7",
    )

    assert entry.event_sequence == 7
    assert entry.event_type is TaskEventType.TASK_CREATED


def test_replay_entry_rejects_private_reasoning_fields() -> None:
    with pytest.raises(JournalIntegrityError, match="private_event_field") as exc_info:
        ReplayEntry(
            event_id=UUID("00000000-0000-0000-0000-000000000102"),
            event_sequence=7,
            stream=EventStream.TASK,
            event_type=TaskEventType.TASK_CREATED,
            task_id=TASK_ID,
            run_id=None,
            task_revision=1,
            run_revision=None,
            payload={"chain_of_thought": "must never be persisted"},
            payload_digest="a" * 64,
        )

    assert exc_info.value.code == "JOURNAL_INTEGRITY_ERROR"


@pytest.mark.parametrize(
    ("after_sequence", "through_sequence", "limit"),
    ((-1, None, 100), (2, 1, 100), (None, None, 0), (None, None, 201)),
)
def test_replay_query_rejects_invalid_snapshot_boundaries(
    after_sequence: int | None,
    through_sequence: int | None,
    limit: int,
) -> None:
    with pytest.raises(ValueError, match="replay_query_invalid"):
        ReplayQuery(
            task_id=TASK_ID,
            after_sequence=after_sequence,
            through_sequence=through_sequence,
            limit=limit,
        )


def test_actor_stamp_requires_an_opaque_non_blank_reference() -> None:
    actor = ActorStamp(kind=ActorKind.HUMAN, ref="local-reviewer")

    assert actor.kind is ActorKind.HUMAN
    assert actor.ref == "local-reviewer"

    with pytest.raises(ValueError, match="actor_ref_invalid"):
        ActorStamp(kind=ActorKind.HUMAN, ref=" ")
