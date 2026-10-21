from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.storyboard_reviews import (
    StoryboardNotFoundError,
    StoryboardReviewService,
)
from app.application.storyboards import (
    StoryboardPreflightNotFoundError,
    StoryboardPreflightService,
)
from app.application.sv_agent.read_tools.contracts import (
    ReadResult,
    StoryboardApprovalEventProjection,
    StoryboardApprovalStateProjection,
    StoryboardApprovalStateQuery,
    StoryboardPreflightQuery,
    StoryboardPreviewQuery,
    StoryboardReadInput,
    StoryboardReadOutput,
    StoryboardReadValue,
)
from app.domain.scripts.models import ValidationReport


class StoryboardReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._preflight = StoryboardPreflightService(session)
        self._reviews = StoryboardReviewService(session)

    async def inspect(self, command: StoryboardReadInput) -> StoryboardReadOutput:
        query = command.query
        if isinstance(query, StoryboardPreflightQuery):
            return await self._inspect_preflight(query)
        if isinstance(query, StoryboardPreviewQuery):
            return await self._inspect_preview(query)
        return await self._inspect_approval(query)

    async def _inspect_preflight(
        self,
        query: StoryboardPreflightQuery,
    ) -> StoryboardReadOutput:
        try:
            preflight = await self._preflight.load(
                script_id=query.script_id,
                version_id=query.version_id,
            )
        except StoryboardPreflightNotFoundError:
            return self._not_found(
                "preflight",
                "SCRIPT_VERSION_NOT_FOUND",
                subject_ref=f"{query.script_id}:{query.version_id}",
            )
        return StoryboardReadOutput(
            action="preflight",
            result=ReadResult[StoryboardReadValue].found(preflight),
        )

    async def _inspect_preview(
        self,
        query: StoryboardPreviewQuery,
    ) -> StoryboardReadOutput:
        try:
            preview = await self._reviews.preview(query.storyboard_id)
        except StoryboardNotFoundError:
            return self._not_found(
                "preview",
                "STORYBOARD_NOT_FOUND",
                subject_ref=str(query.storyboard_id),
            )
        return StoryboardReadOutput(
            action="preview",
            result=ReadResult[StoryboardReadValue].found(preview),
        )

    async def _inspect_approval(
        self,
        query: StoryboardApprovalStateQuery,
    ) -> StoryboardReadOutput:
        try:
            state = await self._reviews.approval_state(query.storyboard_id)
        except StoryboardNotFoundError:
            return self._not_found(
                "approval_state",
                "STORYBOARD_NOT_FOUND",
                subject_ref=str(query.storyboard_id),
            )
        latest = state.latest_event
        projection = StoryboardApprovalStateProjection(
            storyboard_id=query.storyboard_id,
            status=state.status,
            latest_event=(
                StoryboardApprovalEventProjection(
                    id=latest.id,
                    storyboard_id=latest.storyboard_id,
                    decision=cast(Literal["approved", "rejected"], latest.decision),
                    reason=latest.reason,
                    storyboard_digest=latest.storyboard_digest,
                    preflight_digest=latest.preflight_digest,
                    approval_digest=latest.approval_digest,
                    validation_report=ValidationReport.model_validate(latest.validation_report),
                    event_sequence=latest.event_sequence,
                    created_at=latest.created_at,
                )
                if latest is not None
                else None
            ),
        )
        return StoryboardReadOutput(
            action="approval_state",
            result=ReadResult[StoryboardReadValue].found(projection),
        )

    @staticmethod
    def _not_found(
        action: Literal["preflight", "preview", "approval_state"],
        code: str,
        *,
        subject_ref: str,
    ) -> StoryboardReadOutput:
        return StoryboardReadOutput(
            action=action,
            result=ReadResult[StoryboardReadValue].not_found(
                code,
                subject_ref=subject_ref,
            ),
        )
