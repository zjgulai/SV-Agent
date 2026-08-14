from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ScriptGenerationRecord,
    StoryboardApprovalEventRecord,
    StoryboardVersionRecord,
)
from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.application.storyboards import StoryboardPreflightNotFoundError, StoryboardPreflightService
from app.domain.common.canonical import canonical_digest
from app.domain.scripts.models import ScriptDraft
from app.domain.scripts.storyboard import (
    StoryboardPreflight,
    StoryboardPreview,
    compile_storyboard_preview,
    storyboard_digest,
    storyboard_preflight_digest,
)


class StoryboardNotFoundError(Exception):
    pass


class StoryboardNotReadyError(Exception):
    pass


class StoryboardApprovalStaleError(Exception):
    pass


class StoryboardIdempotencyConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StoredStoryboard:
    record: StoryboardVersionRecord
    created: bool


@dataclass(frozen=True, slots=True)
class StoredStoryboardApproval:
    record: StoryboardApprovalEventRecord
    created: bool


@dataclass(frozen=True, slots=True)
class StoryboardApprovalState:
    status: Literal["unreviewed", "approved", "rejected", "stale"]
    latest_event: StoryboardApprovalEventRecord | None


class StoryboardReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scripts = ScriptRepository(session)

    async def create(
        self,
        *,
        script_id: UUID,
        version_id: UUID,
        operation_key: str,
    ) -> StoredStoryboard:
        preflight, generation = await self._load_preflight(
            script_id=script_id,
            version_id=version_id,
            lock_facts=True,
        )
        if preflight.status != "ready":
            raise StoryboardNotReadyError(str(version_id))
        phase_sequence = tuple(
            str(item)
            for item in generation.configuration["pattern_definition"]["phase_sequence"]
        )
        preflight_digest = storyboard_preflight_digest(
            preflight,
            pattern_version=generation.pattern_version,
            phase_sequence=phase_sequence,
        )
        frozen_digest = storyboard_digest(
            preflight=preflight,
            preflight_digest=preflight_digest,
            pattern_version=generation.pattern_version,
            phase_sequence=phase_sequence,
        )
        existing = await self.scripts.get_storyboard_by_operation(
            script_version_id=version_id,
            operation_key=operation_key,
        )
        if existing is not None:
            if existing.storyboard_digest != frozen_digest:
                raise StoryboardIdempotencyConflictError(operation_key)
            return StoredStoryboard(record=existing, created=False)

        version = await self.scripts.get_version(version_id)
        if version is None:
            raise StoryboardNotFoundError(str(version_id))
        candidate = StoryboardVersionRecord(
            id=uuid4(),
            script_version_id=version_id,
            snapshot_id=preflight.snapshot_id,
            selected_fact_ids=[str(item.id) for item in preflight.selected_facts],
            excluded_fact_ids=[str(item.id) for item in preflight.excluded_facts],
            pattern_key=preflight.pattern_key,
            pattern_version=generation.pattern_version,
            phase_sequence=list(phase_sequence),
            draft=version.draft,
            validation_report=preflight.validation_report.model_dump(mode="json"),
            preflight_digest=preflight_digest,
            storyboard_digest=frozen_digest,
            preview_contract_version="p2.0-animatic-v1",
            operation_key=operation_key,
        )
        record, created = await self.scripts.insert_storyboard(candidate)
        if not created and record.storyboard_digest != frozen_digest:
            raise StoryboardIdempotencyConflictError(operation_key)
        return StoredStoryboard(record=record, created=created)

    async def get(self, storyboard_id: UUID) -> StoryboardVersionRecord:
        record = await self.scripts.get_storyboard(storyboard_id)
        if record is None:
            raise StoryboardNotFoundError(str(storyboard_id))
        return record

    async def preview(self, storyboard_id: UUID) -> StoryboardPreview:
        record = await self.get(storyboard_id)
        snapshot = await ProductRepository(self.session).get_snapshot(record.snapshot_id)
        if snapshot is None:
            raise StoryboardNotFoundError(str(storyboard_id))
        draft = ScriptDraft.model_validate(record.draft)
        return compile_storyboard_preview(
            storyboard_id=record.id,
            storyboard_digest=record.storyboard_digest,
            phases=draft.phases,
            shots=draft.shots,
            image_count=len(snapshot.images),
        )

    async def approve(
        self,
        *,
        storyboard_id: UUID,
        decision: Literal["approved", "rejected"],
        reason: str | None,
        operation_key: str,
    ) -> StoredStoryboardApproval:
        storyboard = await self.scripts.get_storyboard(storyboard_id, for_update=True)
        if storyboard is None:
            raise StoryboardNotFoundError(str(storyboard_id))
        preflight, generation = await self._load_preflight_for_storyboard(
            storyboard, lock_facts=True
        )
        if preflight.status != "ready":
            raise StoryboardApprovalStaleError(str(storyboard_id))
        phase_sequence = tuple(
            str(item)
            for item in generation.configuration["pattern_definition"]["phase_sequence"]
        )
        preflight_digest = storyboard_preflight_digest(
            preflight,
            pattern_version=generation.pattern_version,
            phase_sequence=phase_sequence,
        )
        normalized_reason = reason.strip() if reason else None
        approval_digest = canonical_digest(
            {
                "approval_contract_version": "p2.0-approval-v1",
                "storyboard_id": storyboard_id,
                "decision": decision,
                "reason": normalized_reason,
                "storyboard_digest": storyboard.storyboard_digest,
                "preflight_digest": preflight_digest,
            }
        )
        existing = await self.scripts.get_approval_event_by_operation(
            storyboard_id=storyboard_id,
            operation_key=operation_key,
        )
        if existing is not None:
            if existing.approval_digest != approval_digest:
                raise StoryboardIdempotencyConflictError(operation_key)
            return StoredStoryboardApproval(record=existing, created=False)
        candidate = StoryboardApprovalEventRecord(
            id=uuid4(),
            storyboard_id=storyboard_id,
            decision=decision,
            reason=normalized_reason,
            storyboard_digest=storyboard.storyboard_digest,
            preflight_digest=preflight_digest,
            approval_digest=approval_digest,
            validation_report=preflight.validation_report.model_dump(mode="json"),
            operation_key=operation_key,
        )
        record, created = await self.scripts.insert_approval_event(candidate)
        if not created and record.approval_digest != approval_digest:
            raise StoryboardIdempotencyConflictError(operation_key)
        return StoredStoryboardApproval(record=record, created=created)

    async def approval_state(self, storyboard_id: UUID) -> StoryboardApprovalState:
        storyboard = await self.get(storyboard_id)
        latest_event = await self.scripts.get_latest_approval_event(storyboard_id)
        if latest_event is None:
            return StoryboardApprovalState(status="unreviewed", latest_event=None)
        preflight, _generation = await self._load_preflight_for_storyboard(
            storyboard, lock_facts=False
        )
        if preflight.status != "ready":
            return StoryboardApprovalState(status="stale", latest_event=latest_event)
        return StoryboardApprovalState(
            status=cast(Literal["approved", "rejected"], latest_event.decision),
            latest_event=latest_event,
        )

    async def _load_preflight_for_storyboard(
        self, storyboard: StoryboardVersionRecord, *, lock_facts: bool
    ) -> tuple[StoryboardPreflight, ScriptGenerationRecord]:
        version = await self.scripts.get_version(storyboard.script_version_id)
        if version is None:
            raise StoryboardNotFoundError(str(storyboard.id))
        return await self._load_preflight(
            script_id=version.generation_id,
            version_id=version.id,
            lock_facts=lock_facts,
        )

    async def _load_preflight(
        self,
        *,
        script_id: UUID,
        version_id: UUID,
        lock_facts: bool,
    ) -> tuple[StoryboardPreflight, ScriptGenerationRecord]:
        generation = await self.scripts.get_generation(script_id)
        if generation is None:
            raise StoryboardNotFoundError(str(script_id))
        try:
            preflight = await StoryboardPreflightService(self.session).load(
                script_id=script_id,
                version_id=version_id,
                lock_facts=lock_facts,
            )
        except StoryboardPreflightNotFoundError as exc:
            raise StoryboardNotFoundError(str(version_id)) from exc
        return preflight, generation
