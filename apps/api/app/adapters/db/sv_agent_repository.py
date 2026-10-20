from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, literal, select, text, union_all, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvCommandReceiptRecord,
    SvDecisionEventRecord,
    SvTaskEventRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
    SvToolRunEventRecord,
)
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import (
    EventSchemaUnsupported,
    IdempotencyConflict,
    InvalidTaskRevision,
    JournalIntegrityError,
    TaskNotFound,
    TaskRevisionConflict,
)
from app.domain.sv_agent.runtime_records import (
    ActorStamp,
    DecisionEventType,
    EventStream,
    EventType,
    ReplayEntry,
    ReplayPage,
    ReplayQuery,
    TaskEventType,
    ToolRunEventType,
    validate_event_payload,
)

_CREATE_TASK_SCOPE = "sv.task.create.v1"


@dataclass(frozen=True, slots=True)
class TaskWriteResult:
    task: Task
    replayed: bool
    event_sequence: int


class SvAgentRepository:
    """Flush-only persistence for the SV-Agent factual runtime.

    The caller owns transaction commit and rollback. This adapter does not expose
    generic event append or approval-decision mutation surfaces.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(
        self,
        task: Task,
        *,
        idempotency_key: str,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> TaskWriteResult:
        if task.revision != 1:
            raise InvalidTaskRevision("new task revision must be one")
        key = _validate_idempotency_key(idempotency_key)
        input_digest = canonical_digest(
            {
                "command_type": "task.create.v1",
                "task_id": task.id,
                "task_revision": task.revision,
                "brief": task.brief,
            }
        )
        await self._lock_receipt_key(_CREATE_TASK_SCOPE, key)
        replayed = await self._replay_receipt(
            scope=_CREATE_TASK_SCOPE,
            key=key,
            input_digest=input_digest,
        )
        if replayed is not None:
            return replayed

        receipt_id = uuid4()
        event_sequence = await self._next_event_sequence()
        event_payload = validate_event_payload(
            {
                "brief_digest": canonical_digest(task.brief),
                "task_revision_ref": f"{task.id}:{task.revision}",
                "to_revision": task.revision,
            }
        )
        result_payload = {
            "task_id": str(task.id),
            "task_revision": task.revision,
            "event_sequence": event_sequence,
        }

        self.session.add(
            SvTaskRecord(
                id=task.id,
                current_revision=task.revision,
                active_run_id=None,
                summary=_task_summary(task),
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )
        await self.session.flush()
        self.session.add(_task_revision_record(task))
        await self.session.flush()
        self.session.add(
            SvCommandReceiptRecord(
                id=receipt_id,
                task_id=task.id,
                idempotency_scope=_CREATE_TASK_SCOPE,
                idempotency_key=key,
                command_type="task.create.v1",
                expected_task_revision=None,
                input_digest=input_digest,
                result_payload=result_payload,
                result_digest=canonical_digest(result_payload),
            )
        )
        await self.session.flush()
        self.session.add(
            SvTaskEventRecord(
                id=uuid4(),
                event_sequence=event_sequence,
                event_type=TaskEventType.TASK_CREATED.value,
                task_id=task.id,
                run_id=None,
                task_revision=task.revision,
                run_revision=None,
                payload=event_payload,
                payload_digest=canonical_digest(event_payload),
                initiated_by_kind=initiated_by.kind.value,
                initiated_by_ref=initiated_by.ref,
                executed_by_kind=executed_by.kind.value,
                executed_by_ref=executed_by.ref,
                causation_receipt_id=receipt_id,
            )
        )
        await self.session.flush()
        return TaskWriteResult(task=task, replayed=False, event_sequence=event_sequence)

    async def get_task(self, task_id: UUID) -> Task | None:
        head = await self.session.get(SvTaskRecord, task_id)
        if head is None:
            return None
        revision = await self.session.get(
            SvTaskRevisionRecord,
            (task_id, head.current_revision),
        )
        if revision is None:
            raise JournalIntegrityError("task_head_revision_missing")
        return _task_from_records(head, revision)

    async def revise_task(
        self,
        task: Task,
        *,
        expected_revision: int,
        idempotency_key: str,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> TaskWriteResult:
        if expected_revision < 1 or task.revision != expected_revision + 1:
            raise InvalidTaskRevision("revised task must advance expected revision by one")
        key = _validate_idempotency_key(idempotency_key)
        scope = f"sv.task.{task.id}.revise.v1"
        input_digest = canonical_digest(
            {
                "command_type": "task.revise.v1",
                "task_id": task.id,
                "expected_task_revision": expected_revision,
                "task_revision": task.revision,
                "brief": task.brief,
            }
        )
        await self._lock_receipt_key(scope, key)
        replayed = await self._replay_receipt(
            scope=scope,
            key=key,
            input_digest=input_digest,
        )
        if replayed is not None:
            return replayed

        previous_created_at = await self.session.scalar(
            update(SvTaskRecord)
            .where(
                SvTaskRecord.id == task.id,
                SvTaskRecord.current_revision == expected_revision,
            )
            .values(
                current_revision=task.revision,
                summary=_task_summary(task),
                updated_at=task.updated_at,
            )
            .returning(SvTaskRecord.created_at)
        )
        if previous_created_at is None:
            exists = await self.session.scalar(
                select(SvTaskRecord.id).where(SvTaskRecord.id == task.id)
            )
            if exists is None:
                raise TaskNotFound(str(task.id))
            raise TaskRevisionConflict(f"expected task revision {expected_revision} is stale")
        if previous_created_at != task.created_at:
            raise JournalIntegrityError("task_created_at_mismatch")

        receipt_id = uuid4()
        event_sequence = await self._next_event_sequence()
        event_payload = validate_event_payload(
            {
                "brief_digest": canonical_digest(task.brief),
                "from_revision": expected_revision,
                "task_revision_ref": f"{task.id}:{task.revision}",
                "to_revision": task.revision,
            }
        )
        result_payload = {
            "task_id": str(task.id),
            "task_revision": task.revision,
            "event_sequence": event_sequence,
        }
        self.session.add(_task_revision_record(task))
        await self.session.flush()
        self.session.add(
            SvCommandReceiptRecord(
                id=receipt_id,
                task_id=task.id,
                idempotency_scope=scope,
                idempotency_key=key,
                command_type="task.revise.v1",
                expected_task_revision=expected_revision,
                input_digest=input_digest,
                result_payload=result_payload,
                result_digest=canonical_digest(result_payload),
            )
        )
        await self.session.flush()
        self.session.add(
            SvTaskEventRecord(
                id=uuid4(),
                event_sequence=event_sequence,
                event_type=TaskEventType.TASK_REVISED.value,
                task_id=task.id,
                run_id=None,
                task_revision=task.revision,
                run_revision=None,
                payload=event_payload,
                payload_digest=canonical_digest(event_payload),
                initiated_by_kind=initiated_by.kind.value,
                initiated_by_ref=initiated_by.ref,
                executed_by_kind=executed_by.kind.value,
                executed_by_ref=executed_by.ref,
                causation_receipt_id=receipt_id,
            )
        )
        await self.session.flush()
        return TaskWriteResult(task=task, replayed=False, event_sequence=event_sequence)

    async def read_replay(self, query: ReplayQuery) -> ReplayPage:
        events = _replay_union(query.task_id).subquery()
        if query.through_sequence is None:
            snapshot = await self.session.scalar(select(func.max(events.c.event_sequence)))
            through_sequence = int(snapshot or 0)
        else:
            through_sequence = query.through_sequence

        statement = (
            select(events)
            .where(events.c.event_sequence > (query.after_sequence or 0))
            .where(events.c.event_sequence <= through_sequence)
            .order_by(events.c.event_sequence)
            .limit(query.limit + 1)
        )
        rows = (await self.session.execute(statement)).mappings().all()
        has_more = len(rows) > query.limit
        visible_rows = rows[: query.limit]
        entries = tuple(_replay_entry_from_row(dict(row)) for row in visible_rows)
        next_after_sequence = entries[-1].event_sequence if has_more and entries else None
        return ReplayPage(
            task_id=query.task_id,
            entries=entries,
            snapshot_through_sequence=through_sequence,
            next_after_sequence=next_after_sequence,
        )

    async def _lock_receipt_key(self, scope: str, key: str) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"{scope}:{key}"},
        )

    async def _replay_receipt(
        self,
        *,
        scope: str,
        key: str,
        input_digest: str,
    ) -> TaskWriteResult | None:
        receipt = await self.session.scalar(
            select(SvCommandReceiptRecord).where(
                SvCommandReceiptRecord.idempotency_scope == scope,
                SvCommandReceiptRecord.idempotency_key == key,
            )
        )
        if receipt is None:
            return None
        if receipt.input_digest != input_digest:
            raise IdempotencyConflict("idempotency key was used for a different command")
        if canonical_digest(receipt.result_payload) != receipt.result_digest:
            raise JournalIntegrityError("command_receipt_digest_mismatch")
        task_revision = receipt.result_payload.get("task_revision")
        event_sequence = receipt.result_payload.get("event_sequence")
        if not isinstance(task_revision, int) or not isinstance(event_sequence, int):
            raise JournalIntegrityError("command_receipt_result_invalid")
        task = await self._get_task_revision(receipt.task_id, task_revision)
        if task is None:
            raise JournalIntegrityError("command_receipt_task_revision_missing")
        return TaskWriteResult(task=task, replayed=True, event_sequence=event_sequence)

    async def _get_task_revision(self, task_id: UUID, revision_number: int) -> Task | None:
        head = await self.session.get(SvTaskRecord, task_id)
        revision = await self.session.get(
            SvTaskRevisionRecord,
            (task_id, revision_number),
        )
        if head is None or revision is None:
            return None
        return _task_from_records(head, revision)

    async def _next_event_sequence(self) -> int:
        sequence = await self.session.scalar(select(func.nextval("sv_runtime_event_sequence")))
        if not isinstance(sequence, int) or sequence < 1:
            raise JournalIntegrityError("event_sequence_unavailable")
        return sequence


def _validate_idempotency_key(value: str) -> str:
    if not value or value != value.strip() or len(value) > 255:
        raise ValueError("idempotency_key_invalid")
    return value


def _task_summary(task: Task) -> dict[str, Any]:
    return {
        "goal_track": task.brief.goal_track.value,
        "platform": task.brief.platform.value,
        "subject": task.brief.subject,
    }


def _task_revision_record(task: Task) -> SvTaskRevisionRecord:
    return SvTaskRevisionRecord(
        task_id=task.id,
        revision=task.revision,
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
        created_at=task.updated_at,
    )


def _task_from_records(head: SvTaskRecord, revision: SvTaskRevisionRecord) -> Task:
    brief = TaskBrief(
        goal_track=GoalTrack(revision.goal_track),
        decision_question=revision.decision_question,
        subject=revision.subject,
        platform=TargetPlatform(revision.platform),
        market=revision.market,
        language=revision.language,
        performance_window=PerformanceWindow(
            start=revision.performance_start,
            end=revision.performance_end,
            timezone=revision.performance_timezone,
        ),
        stop_condition=revision.stop_condition,
        initial_rights_state=RightsState(revision.initial_rights_state),
    )
    if canonical_digest(brief) != revision.brief_digest:
        raise JournalIntegrityError("task_brief_digest_mismatch")
    return Task(
        id=head.id,
        revision=revision.revision,
        brief=brief,
        created_at=head.created_at,
        updated_at=revision.created_at,
    )


def _replay_union(task_id: UUID) -> Any:
    task_events = select(
        SvTaskEventRecord.id.label("event_id"),
        SvTaskEventRecord.event_sequence,
        literal(EventStream.TASK.value).label("stream"),
        SvTaskEventRecord.event_type,
        SvTaskEventRecord.task_id,
        SvTaskEventRecord.run_id,
        SvTaskEventRecord.task_revision,
        SvTaskEventRecord.run_revision,
        SvTaskEventRecord.payload,
        SvTaskEventRecord.payload_digest,
    ).where(SvTaskEventRecord.task_id == task_id)
    tool_events = select(
        SvToolRunEventRecord.id.label("event_id"),
        SvToolRunEventRecord.event_sequence,
        literal(EventStream.TOOL_RUN.value).label("stream"),
        SvToolRunEventRecord.event_type,
        SvToolRunEventRecord.task_id,
        SvToolRunEventRecord.run_id,
        SvToolRunEventRecord.task_revision,
        SvToolRunEventRecord.run_revision,
        SvToolRunEventRecord.payload,
        SvToolRunEventRecord.payload_digest,
    ).where(SvToolRunEventRecord.task_id == task_id)
    decision_events = select(
        SvDecisionEventRecord.id.label("event_id"),
        SvDecisionEventRecord.event_sequence,
        literal(EventStream.DECISION.value).label("stream"),
        SvDecisionEventRecord.event_type,
        SvDecisionEventRecord.task_id,
        SvDecisionEventRecord.run_id,
        SvDecisionEventRecord.task_revision,
        SvDecisionEventRecord.run_revision,
        SvDecisionEventRecord.payload,
        SvDecisionEventRecord.payload_digest,
    ).where(SvDecisionEventRecord.task_id == task_id)
    return union_all(task_events, tool_events, decision_events)


def _replay_entry_from_row(row: dict[str, Any]) -> ReplayEntry:
    try:
        stream = EventStream(row["stream"])
        event_type: EventType
        if stream is EventStream.TASK:
            event_type = TaskEventType(row["event_type"])
        elif stream is EventStream.TOOL_RUN:
            event_type = ToolRunEventType(row["event_type"])
        else:
            event_type = DecisionEventType(row["event_type"])
    except (KeyError, ValueError) as exc:
        raise EventSchemaUnsupported("event_type_unknown") from exc
    return ReplayEntry(
        event_id=row["event_id"],
        event_sequence=row["event_sequence"],
        stream=stream,
        event_type=event_type,
        task_id=row["task_id"],
        run_id=row["run_id"],
        task_revision=row["task_revision"],
        run_revision=row["run_revision"],
        payload=row["payload"],
        payload_digest=row["payload_digest"],
    )
