from typing import Protocol
from uuid import UUID

from app.domain.sv_agent.runtime_records import ActorStamp
from app.domain.sv_agent.tool_runs import ToolRun


class ToolRunJournal(Protocol):
    async def create(
        self,
        tool_run: ToolRun,
        *,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> ToolRun: ...

    async def save(
        self,
        tool_run: ToolRun,
        *,
        expected_revision: int,
        result_digest: str | None = None,
        initiated_by: ActorStamp,
        executed_by: ActorStamp,
    ) -> ToolRun: ...

    async def get(self, tool_run_id: UUID) -> ToolRun | None: ...
