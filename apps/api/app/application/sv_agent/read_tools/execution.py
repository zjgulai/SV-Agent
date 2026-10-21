from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.runtime_records import ActorStamp
from app.domain.sv_agent.tool_runs import ToolRun
from app.ports.sv_agent_tool_journal import ToolRunJournal

from .contracts import (
    ReadToolName,
    ReadToolOutput,
)
from .errors import ReadToolSourceFailure
from .registry import (
    ReadToolContractViolation,
    ReadToolUnavailable,
    StaticReadToolRegistry,
)


@dataclass(frozen=True, slots=True)
class ReadToolExecutionContext:
    task_id: UUID
    task_revision: int
    run_id: UUID
    run_revision: int
    initiated_by: ActorStamp
    executed_by: ActorStamp

    def __post_init__(self) -> None:
        if self.task_revision < 1 or self.run_revision < 1:
            raise ValueError("read_tool_execution_revision_invalid")


@dataclass(frozen=True, slots=True)
class ReadToolExecution:
    tool_run: ToolRun
    output: ReadToolOutput | None


class ReadToolExecutionService:
    def __init__(
        self,
        registry: StaticReadToolRegistry,
        journal: ToolRunJournal,
    ) -> None:
        self._registry = registry
        self._journal = journal

    async def execute(
        self,
        context: ReadToolExecutionContext,
        tool_name: ReadToolName | str,
        payload: Mapping[str, object],
    ) -> ReadToolExecution:
        command = self._registry.validate_input(tool_name, payload)
        descriptor = self._registry.describe(command.tool)
        input_digest = canonical_digest(
            {
                "tool_name": descriptor.name.value,
                "tool_version": descriptor.version,
                "input": command.model_dump(mode="json"),
            }
        )
        pending = ToolRun.new(
            task_id=context.task_id,
            task_revision=context.task_revision,
            run_id=context.run_id,
            run_revision=context.run_revision,
            tool_name=descriptor.name.value,
            tool_version=descriptor.version,
            intent_summary=descriptor.intent_summary,
            input_digest=input_digest,
        )
        pending = await self._journal.create(
            pending,
            initiated_by=context.initiated_by,
            executed_by=context.executed_by,
        )
        running = pending.start()
        running = await self._journal.save(
            running,
            expected_revision=pending.revision,
            initiated_by=context.initiated_by,
            executed_by=context.executed_by,
        )

        try:
            output = await self._registry.invoke(command)
        except ReadToolUnavailable:
            unavailable = running.unavailable(
                stable_error_code="TOOL_UNAVAILABLE",
                recovery_action=(
                    "Enable the registered local read adapter, then start a new ToolRun."
                ),
            )
            unavailable = await self._journal.save(
                unavailable,
                expected_revision=running.revision,
                initiated_by=context.initiated_by,
                executed_by=context.executed_by,
            )
            return ReadToolExecution(tool_run=unavailable, output=None)
        except ReadToolSourceFailure as exc:
            return await self._record_failure(context, running, exc)
        except ReadToolContractViolation as exc:
            failure = ReadToolSourceFailure(
                exc.code,
                "Repair the registered read adapter contract before retrying.",
            )
            return await self._record_failure(context, running, failure)
        except Exception:  # noqa: BLE001 - boundary converts unknown failures to safe facts.
            failure = ReadToolSourceFailure(
                "TOOL_READ_FAILED",
                "Verify the authoritative source is readable, then start a new ToolRun.",
            )
            return await self._record_failure(context, running, failure)

        completed = running.complete()
        result_digest = canonical_digest(output.model_dump(mode="json"))
        completed = await self._journal.save(
            completed,
            expected_revision=running.revision,
            result_digest=result_digest,
            initiated_by=context.initiated_by,
            executed_by=context.executed_by,
        )
        return ReadToolExecution(tool_run=completed, output=output)

    async def _record_failure(
        self,
        context: ReadToolExecutionContext,
        running: ToolRun,
        failure: ReadToolSourceFailure,
    ) -> ReadToolExecution:
        failed = running.failed(
            stable_error_code=failure.stable_error_code,
            recovery_action=failure.recovery_action,
        )
        failed = await self._journal.save(
            failed,
            expected_revision=running.revision,
            initiated_by=context.initiated_by,
            executed_by=context.executed_by,
        )
        return ReadToolExecution(tool_run=failed, output=None)
