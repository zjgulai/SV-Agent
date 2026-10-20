from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.sv_agent_models import (
    SvRunRecord,
    SvTaskRecord,
    SvToolRunEventRecord,
    SvToolRunRecord,
)
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.errors import (
    JournalIntegrityError,
    RunNotFound,
    RunRevisionConflict,
    TaskNotFound,
    TaskRevisionConflict,
    ToolRunNotFound,
    ToolRunRevisionConflict,
)
from app.domain.sv_agent.runtime_records import (
    ActorStamp,
    EffectClass,
    ToolRunEventType,
    ToolRunStatus,
    validate_event_payload,
)
from app.domain.sv_agent.tool_runs import ToolArtifactRef, ToolRun


class SvToolRunRepository:
    """Flush-only ToolRun head and factual event journal."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        tool_run: ToolRun,
        *,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> ToolRun:
        if tool_run.revision != 1 or tool_run.status is not ToolRunStatus.PENDING:
            raise ValueError("tool_run_create_state_invalid")
        await self._validate_runtime_binding(tool_run)
        self.session.add(_record_from_tool_run(tool_run))
        await self.session.flush()
        await self._append_event(
            tool_run,
            event_type=ToolRunEventType.CREATED,
            initiated_by=initiated_by,
            executed_by=executed_by,
        )
        return tool_run

    async def save(
        self,
        tool_run: ToolRun,
        *,
        expected_revision: int,
        result_digest: str | None = None,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> ToolRun:
        if expected_revision < 1 or tool_run.revision != expected_revision + 1:
            raise ToolRunRevisionConflict("tool run revision must advance by one")
        event_type = _event_type(tool_run.status)
        previous_status = _previous_status(tool_run.status)
        if tool_run.status is ToolRunStatus.COMPLETED:
            if result_digest is None or not _is_sha256(result_digest):
                raise ValueError("completed_tool_run_result_digest_invalid")
        elif result_digest is not None:
            raise ValueError("non_completed_tool_run_result_digest_invalid")
        updated = await self.session.scalar(
            update(SvToolRunRecord)
            .where(
                SvToolRunRecord.id == tool_run.id,
                SvToolRunRecord.revision == expected_revision,
                SvToolRunRecord.status == previous_status.value,
                SvToolRunRecord.attempt_token == tool_run.attempt_token,
            )
            .values(
                revision=tool_run.revision,
                attempt_token=tool_run.attempt_token,
                status=tool_run.status.value,
                artifact_refs=[item.as_payload() for item in tool_run.artifact_refs],
                stable_error_code=tool_run.stable_error_code,
                recovery_action=tool_run.recovery_action,
                started_at=tool_run.started_at,
                finished_at=tool_run.finished_at,
                updated_at=tool_run.updated_at,
            )
            .returning(SvToolRunRecord.id)
        )
        if updated is None:
            exists = await self.session.scalar(
                select(SvToolRunRecord.id).where(SvToolRunRecord.id == tool_run.id)
            )
            if exists is None:
                raise ToolRunNotFound(str(tool_run.id))
            raise ToolRunRevisionConflict(
                f"expected tool run revision {expected_revision} is stale"
            )
        await self._append_event(
            tool_run,
            event_type=event_type,
            result_digest=result_digest,
            initiated_by=initiated_by,
            executed_by=executed_by,
        )
        return tool_run

    async def get(self, tool_run_id: UUID) -> ToolRun | None:
        record = await self.session.get(SvToolRunRecord, tool_run_id)
        return _tool_run_from_record(record) if record is not None else None

    async def _validate_runtime_binding(self, tool_run: ToolRun) -> None:
        task = await self.session.scalar(
            select(SvTaskRecord).where(SvTaskRecord.id == tool_run.task_id).with_for_update()
        )
        if task is None:
            raise TaskNotFound(str(tool_run.task_id))
        if task.current_revision != tool_run.task_revision:
            raise TaskRevisionConflict(f"expected task revision {tool_run.task_revision} is stale")
        run = await self.session.scalar(
            select(SvRunRecord).where(SvRunRecord.id == tool_run.run_id).with_for_update()
        )
        if run is None or run.task_id != tool_run.task_id:
            raise RunNotFound(str(tool_run.run_id))
        if run.revision != tool_run.run_revision or run.task_revision != tool_run.task_revision:
            raise RunRevisionConflict(f"expected run revision {tool_run.run_revision} is stale")

    async def _append_event(
        self,
        tool_run: ToolRun,
        *,
        event_type: ToolRunEventType,
        result_digest: str | None = None,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> None:
        payload = validate_event_payload(
            {
                "artifact_refs": [item.as_payload() for item in tool_run.artifact_refs],
                "attempt_token": tool_run.attempt_token,
                "input_digest": tool_run.input_digest,
                "recovery_action": tool_run.recovery_action,
                "result_digest": result_digest,
                "revision": tool_run.revision,
                "stable_error_code": tool_run.stable_error_code,
                "status": tool_run.status.value,
                "tool_name": tool_run.tool_name,
                "tool_run_id": str(tool_run.id),
                "tool_version": tool_run.tool_version,
            }
        )
        self.session.add(
            SvToolRunEventRecord(
                id=uuid4(),
                event_type=event_type.value,
                tool_run_id=tool_run.id,
                task_id=tool_run.task_id,
                task_revision=tool_run.task_revision,
                run_id=tool_run.run_id,
                run_revision=tool_run.run_revision,
                attempt_token=tool_run.attempt_token,
                payload=payload,
                payload_digest=canonical_digest(payload),
                initiated_by_kind=initiated_by.kind.value,
                initiated_by_ref=initiated_by.ref,
                executed_by_kind=executed_by.kind.value,
                executed_by_ref=executed_by.ref,
            )
        )
        await self.session.flush()


def _event_type(status: ToolRunStatus) -> ToolRunEventType:
    mapping = {
        ToolRunStatus.RUNNING: ToolRunEventType.STARTED,
        ToolRunStatus.COMPLETED: ToolRunEventType.COMPLETED,
        ToolRunStatus.FAILED: ToolRunEventType.FAILED,
        ToolRunStatus.UNAVAILABLE: ToolRunEventType.UNAVAILABLE,
        ToolRunStatus.UNKNOWN: ToolRunEventType.EFFECT_UNKNOWN,
    }
    try:
        return mapping[status]
    except KeyError as exc:
        raise ValueError(f"tool_run_save_state_invalid:{status.value}") from exc


def _previous_status(status: ToolRunStatus) -> ToolRunStatus:
    if status is ToolRunStatus.RUNNING:
        return ToolRunStatus.PENDING
    if status in {
        ToolRunStatus.COMPLETED,
        ToolRunStatus.FAILED,
        ToolRunStatus.UNAVAILABLE,
        ToolRunStatus.UNKNOWN,
    }:
        return ToolRunStatus.RUNNING
    raise ValueError(f"tool_run_save_state_invalid:{status.value}")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _record_from_tool_run(tool_run: ToolRun) -> SvToolRunRecord:
    return SvToolRunRecord(
        id=tool_run.id,
        task_id=tool_run.task_id,
        task_revision=tool_run.task_revision,
        run_id=tool_run.run_id,
        run_revision=tool_run.run_revision,
        revision=tool_run.revision,
        tool_name=tool_run.tool_name,
        tool_version=tool_run.tool_version,
        intent_summary=tool_run.intent_summary,
        input_digest=tool_run.input_digest,
        effect_class=tool_run.effect_class.value,
        approval_request_id=tool_run.approval_request_id,
        approval_request_version=tool_run.approval_request_version,
        idempotency_key=tool_run.idempotency_key,
        attempt_token=tool_run.attempt_token,
        status=tool_run.status.value,
        artifact_refs=[item.as_payload() for item in tool_run.artifact_refs],
        stable_error_code=tool_run.stable_error_code,
        recovery_action=tool_run.recovery_action,
        started_at=tool_run.started_at,
        finished_at=tool_run.finished_at,
        created_at=tool_run.created_at,
        updated_at=tool_run.updated_at,
    )


def _tool_run_from_record(record: SvToolRunRecord) -> ToolRun:
    try:
        artifact_refs = tuple(
            ToolArtifactRef(
                artifact_type=str(item["artifact_type"]),
                artifact_id=str(item["artifact_id"]),
                artifact_version=int(item["artifact_version"]),
                artifact_digest=str(item["artifact_digest"]),
            )
            for item in record.artifact_refs
        )
        return ToolRun(
            id=record.id,
            task_id=record.task_id,
            task_revision=record.task_revision,
            run_id=record.run_id,
            run_revision=record.run_revision,
            revision=record.revision,
            tool_name=record.tool_name,
            tool_version=record.tool_version,
            intent_summary=record.intent_summary,
            input_digest=record.input_digest,
            effect_class=EffectClass(record.effect_class),
            approval_request_id=record.approval_request_id,
            approval_request_version=record.approval_request_version,
            idempotency_key=record.idempotency_key,
            attempt_token=record.attempt_token,
            status=ToolRunStatus(record.status),
            artifact_refs=artifact_refs,
            stable_error_code=record.stable_error_code,
            recovery_action=record.recovery_action,
            started_at=record.started_at,
            finished_at=record.finished_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise JournalIntegrityError("tool_run_record_invalid") from exc
