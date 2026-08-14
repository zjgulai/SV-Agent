from typing import Annotated, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ScriptGenerationRecord,
    ScriptVersionRecord,
    StoryboardApprovalEventRecord,
    StoryboardVersionRecord,
)
from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.adapters.db.session import get_db_session
from app.api.problems import ApiProblem
from app.api.routes.jobs import job_output
from app.api.schemas.scripts import (
    DeriveVersionInput,
    JobOutput,
    ScriptGenerationInput,
    ScriptGenerationOutput,
    ScriptOutput,
    ScriptVersionOutput,
    StoryboardApprovalEventOutput,
    StoryboardApprovalInput,
    StoryboardApprovalOutput,
    StoryboardVersionOutput,
    VersionDiffOutput,
)
from app.application.dispatch import mark_dispatch_failed
from app.application.exports import export_json, export_markdown
from app.application.generations import (
    CreativePatternNotFoundError,
    DurationNotSupportedError,
    FactSelectionInvalidError,
    FactsNotReadyError,
    GenerationCommand,
    GenerationIdempotencyConflictError,
    GenerationProductNotFoundError,
    GenerationService,
)
from app.application.storyboard_reviews import (
    StoryboardApprovalStaleError,
    StoryboardIdempotencyConflictError,
    StoryboardNotFoundError,
    StoryboardNotReadyError,
    StoryboardReviewService,
)
from app.application.storyboards import (
    StoryboardPreflightNotFoundError,
    StoryboardPreflightService,
)
from app.application.version_diff import diff_versions
from app.domain.jobs.entities import JobState
from app.domain.scripts.models import ScriptDraft, ValidationReport
from app.domain.scripts.patterns import CREATIVE_PATTERNS
from app.domain.scripts.storyboard import StoryboardPreflight, StoryboardPreview
from app.domain.scripts.validation import validate_script
from app.settings import provider_api_key_is_configured, settings
from app.worker.tasks import generate_script

router = APIRouter(tags=["scripts"])


def _generation_output(record: ScriptGenerationRecord) -> ScriptGenerationOutput:
    return ScriptGenerationOutput(
        id=record.id,
        snapshot_id=record.snapshot_id,
        selected_fact_ids=[UUID(item) for item in record.selected_fact_ids],
        excluded_fact_ids=[UUID(item) for item in record.excluded_fact_ids],
        configuration=record.configuration,
        pattern_key=record.pattern_key,
        pattern_version=record.pattern_version,
        provider=record.provider,
        model=record.model,
        prompt_contract_version=record.prompt_contract_version,
        input_digest=record.input_digest,
        created_at=record.created_at,
    )


def _version_output(record: ScriptVersionRecord) -> ScriptVersionOutput:
    return ScriptVersionOutput(
        id=record.id,
        generation_id=record.generation_id,
        parent_version_id=record.parent_version_id,
        draft=ScriptDraft.model_validate(record.draft),
        validation_report=ValidationReport.model_validate(record.validation_report),
        created_at=record.created_at,
    )


def _storyboard_output(record: StoryboardVersionRecord) -> StoryboardVersionOutput:
    return StoryboardVersionOutput(
        id=record.id,
        script_version_id=record.script_version_id,
        snapshot_id=record.snapshot_id,
        selected_fact_ids=[UUID(item) for item in record.selected_fact_ids],
        excluded_fact_ids=[UUID(item) for item in record.excluded_fact_ids],
        pattern_key=record.pattern_key,
        pattern_version=record.pattern_version,
        phase_sequence=record.phase_sequence,
        draft=ScriptDraft.model_validate(record.draft),
        validation_report=ValidationReport.model_validate(record.validation_report),
        preflight_digest=record.preflight_digest,
        storyboard_digest=record.storyboard_digest,
        preview_contract_version=record.preview_contract_version,
        created_at=record.created_at,
    )


def _storyboard_approval_event_output(
    record: StoryboardApprovalEventRecord,
) -> StoryboardApprovalEventOutput:
    return StoryboardApprovalEventOutput(
        id=record.id,
        storyboard_id=record.storyboard_id,
        decision=cast(Literal["approved", "rejected"], record.decision),
        reason=record.reason,
        storyboard_digest=record.storyboard_digest,
        preflight_digest=record.preflight_digest,
        approval_digest=record.approval_digest,
        validation_report=ValidationReport.model_validate(record.validation_report),
        event_sequence=record.event_sequence,
        created_at=record.created_at,
    )


async def _load_script(session: AsyncSession, script_id: UUID) -> ScriptOutput:
    repository = ScriptRepository(session)
    generation = await repository.get_generation(script_id)
    if generation is None:
        raise ApiProblem(
            status=404,
            code="SCRIPT_NOT_FOUND",
            title="Script not found",
            detail="The requested script does not exist.",
        )
    versions = await repository.list_versions(script_id)
    return ScriptOutput(
        generation=_generation_output(generation),
        versions=[_version_output(item) for item in versions],
    )


@router.post(
    "/api/v1/products/{product_id}/script-generations",
    response_model=JobOutput,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_script_generation(
    product_id: UUID,
    payload: ScriptGenerationInput,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> JobOutput:
    if settings.script_provider == "openai_compatible" and not provider_api_key_is_configured(
        settings.provider_api_key
    ):
        raise ApiProblem(
            status=503,
            code="PROVIDER_MISCONFIGURED",
            title="Script provider misconfigured",
            detail="The configured script provider is missing its API key.",
        )
    try:
        async with session.begin():
            queued = await GenerationService(session).queue(
                product_id=product_id,
                idempotency_key=idempotency_key,
                command=GenerationCommand(
                    target_duration_seconds=payload.target_duration_seconds,
                    language=payload.language,
                    audience=payload.audience,
                    creative_pattern_key=payload.creative_pattern_key,
                    selected_fact_ids=tuple(payload.selected_fact_ids),
                    excluded_fact_ids=tuple(payload.excluded_fact_ids),
                ),
                provider=settings.script_provider,
                model=(
                    settings.provider_model
                    if settings.script_provider == "openai_compatible"
                    else "deterministic-v1"
                ),
            )
    except GenerationProductNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="PRODUCT_NOT_FOUND",
            title="Product not found",
            detail="The requested product does not exist.",
        ) from exc
    except FactsNotReadyError as exc:
        raise ApiProblem(
            status=409,
            code="FACTS_NOT_READY",
            title="Facts are not ready",
            detail="Confirm or lock at least one product fact before generation.",
        ) from exc
    except FactSelectionInvalidError as exc:
        raise ApiProblem(
            status=422,
            code="FACT_SELECTION_INVALID",
            title="Fact selection invalid",
            detail="Selected and excluded facts must be unique, disjoint, and belong to the current snapshot.",
        ) from exc
    except CreativePatternNotFoundError as exc:
        raise ApiProblem(
            status=422,
            code="CREATIVE_PATTERN_NOT_FOUND",
            title="Creative pattern not found",
            detail="The selected creative pattern is unavailable.",
        ) from exc
    except DurationNotSupportedError as exc:
        raise ApiProblem(
            status=422,
            code="DURATION_NOT_SUPPORTED",
            title="Duration not supported",
            detail="The selected creative pattern does not support this duration.",
        ) from exc
    except GenerationIdempotencyConflictError as exc:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Idempotency conflict",
            detail="This Idempotency-Key was already used with different input.",
        ) from exc
    job = queued.job
    if queued.created or job.state is JobState.QUEUED:
        try:
            generate_script.delay(str(job.id))
        except Exception as exc:
            await mark_dispatch_failed(session, job.id)
            raise ApiProblem(
                status=503,
                code="BROKER_UNAVAILABLE",
                title="Background queue unavailable",
                detail="The generation task could not be dispatched.",
            ) from exc
    response.headers["Location"] = f"/api/v1/jobs/{job.id}"
    return job_output(job)


@router.get("/api/v1/scripts/{script_id}", response_model=ScriptOutput)
async def get_script(
    script_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScriptOutput:
    return await _load_script(session, script_id)


@router.get("/api/v1/scripts/{script_id}/versions", response_model=list[ScriptVersionOutput])
async def list_script_versions(
    script_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ScriptVersionOutput]:
    return (await _load_script(session, script_id)).versions


@router.get(
    "/api/v1/scripts/{script_id}/versions/{version_id}",
    response_model=ScriptVersionOutput,
)
async def get_script_version(
    script_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScriptVersionOutput:
    version = await ScriptRepository(session).get_version(version_id)
    if version is None or version.generation_id != script_id:
        raise ApiProblem(
            status=404,
            code="SCRIPT_VERSION_NOT_FOUND",
            title="Script version not found",
            detail="The requested script version does not exist.",
        )
    return _version_output(version)


@router.get(
    "/api/v1/scripts/{script_id}/versions/{version_id}/storyboard-preflight",
    response_model=StoryboardPreflight,
)
async def get_storyboard_preflight(
    script_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoryboardPreflight:
    try:
        return await StoryboardPreflightService(session).load(
            script_id=script_id, version_id=version_id
        )
    except StoryboardPreflightNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="SCRIPT_VERSION_NOT_FOUND",
            title="Script version not found",
            detail="The requested script version does not exist.",
        ) from exc


@router.post(
    "/api/v1/scripts/{script_id}/versions/{version_id}/storyboards",
    response_model=StoryboardVersionOutput,
    status_code=status.HTTP_201_CREATED,
)
async def create_storyboard(
    script_id: UUID,
    version_id: UUID,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> StoryboardVersionOutput:
    try:
        async with session.begin():
            stored = await StoryboardReviewService(session).create(
                script_id=script_id,
                version_id=version_id,
                operation_key=idempotency_key,
            )
    except StoryboardNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="STORYBOARD_NOT_FOUND",
            title="Storyboard not found",
            detail="The requested script version does not exist.",
        ) from exc
    except StoryboardNotReadyError as exc:
        raise ApiProblem(
            status=409,
            code="STORYBOARD_NOT_READY",
            title="Storyboard not ready",
            detail="The current fact and script contract must pass preflight first.",
        ) from exc
    except StoryboardIdempotencyConflictError as exc:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Idempotency conflict",
            detail="This key was already used with different storyboard input.",
        ) from exc
    if not stored.created:
        response.status_code = status.HTTP_200_OK
    return _storyboard_output(stored.record)


@router.get("/api/v1/storyboards/{storyboard_id}", response_model=StoryboardVersionOutput)
async def get_storyboard(
    storyboard_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoryboardVersionOutput:
    try:
        return _storyboard_output(await StoryboardReviewService(session).get(storyboard_id))
    except StoryboardNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="STORYBOARD_NOT_FOUND",
            title="Storyboard not found",
            detail="The requested storyboard does not exist.",
        ) from exc


@router.get(
    "/api/v1/storyboards/{storyboard_id}/preview",
    response_model=StoryboardPreview,
)
async def get_storyboard_preview(
    storyboard_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoryboardPreview:
    try:
        return await StoryboardReviewService(session).preview(storyboard_id)
    except StoryboardNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="STORYBOARD_NOT_FOUND",
            title="Storyboard not found",
            detail="The requested storyboard does not exist.",
        ) from exc


@router.post(
    "/api/v1/storyboards/{storyboard_id}/approval-events",
    response_model=StoryboardApprovalEventOutput,
    status_code=status.HTTP_201_CREATED,
)
async def create_storyboard_approval_event(
    storyboard_id: UUID,
    payload: StoryboardApprovalInput,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> StoryboardApprovalEventOutput:
    try:
        async with session.begin():
            stored = await StoryboardReviewService(session).approve(
                storyboard_id=storyboard_id,
                decision=payload.decision,
                reason=payload.reason,
                operation_key=idempotency_key,
            )
    except StoryboardNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="STORYBOARD_NOT_FOUND",
            title="Storyboard not found",
            detail="The requested storyboard does not exist.",
        ) from exc
    except StoryboardApprovalStaleError as exc:
        raise ApiProblem(
            status=409,
            code="STORYBOARD_APPROVAL_STALE",
            title="Storyboard approval stale",
            detail="The current fact and script contract no longer supports approval.",
        ) from exc
    except StoryboardIdempotencyConflictError as exc:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Idempotency conflict",
            detail="This key was already used with different approval input.",
        ) from exc
    if not stored.created:
        response.status_code = status.HTTP_200_OK
    return _storyboard_approval_event_output(stored.record)


@router.get(
    "/api/v1/storyboards/{storyboard_id}/approval",
    response_model=StoryboardApprovalOutput,
)
async def get_storyboard_approval(
    storyboard_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoryboardApprovalOutput:
    try:
        state = await StoryboardReviewService(session).approval_state(storyboard_id)
    except StoryboardNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="STORYBOARD_NOT_FOUND",
            title="Storyboard not found",
            detail="The requested storyboard does not exist.",
        ) from exc
    return StoryboardApprovalOutput(
        status=state.status,
        latest_event=(
            _storyboard_approval_event_output(state.latest_event)
            if state.latest_event is not None
            else None
        ),
    )


@router.post(
    "/api/v1/scripts/{script_id}/versions/{version_id}/derive",
    response_model=ScriptVersionOutput,
    status_code=status.HTTP_201_CREATED,
)
async def derive_script_version(
    script_id: UUID,
    version_id: UUID,
    payload: DeriveVersionInput,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScriptVersionOutput:
    async with session.begin():
        scripts = ScriptRepository(session)
        generation = await scripts.get_generation(script_id)
        parent = await scripts.get_version(version_id)
        if generation is None or parent is None or parent.generation_id != script_id:
            raise ApiProblem(
                status=404,
                code="SCRIPT_VERSION_NOT_FOUND",
                title="Script version not found",
                detail="The requested script version does not exist.",
            )
        draft = ScriptDraft.model_validate(parent.draft).model_copy(update={"titles": [payload.title]})
        products = ProductRepository(session)
        facts = {}
        for raw_id in generation.selected_fact_ids:
            fact = await products.get_fact(UUID(raw_id), for_update=True)
            if fact is not None:
                facts[fact.id] = fact
        excluded_facts = {}
        for raw_id in generation.excluded_fact_ids:
            fact = await products.get_fact(UUID(raw_id), for_update=True)
            if fact is None or fact.snapshot_id != generation.snapshot_id:
                raise ApiProblem(
                    status=409,
                    code="FACTS_NOT_READY",
                    title="Facts are not ready",
                    detail="The generation fact contract is no longer available.",
                )
            excluded_facts[fact.id] = fact
        report = validate_script(
            draft,
            facts,
            excluded_facts=excluded_facts,
            creative_pattern_key=generation.pattern_key,
            phase_sequence=tuple(
                str(item)
                for item in generation.configuration["pattern_definition"][
                    "phase_sequence"
                ]
            ),
        )
        version = ScriptVersionRecord(
            id=uuid4(),
            generation_id=script_id,
            parent_version_id=parent.id,
            draft=draft.model_dump(mode="json"),
            validation_report=report.model_dump(mode="json"),
        )
        await scripts.add_version(version)
    return _version_output(version)


@router.get(
    "/api/v1/scripts/{script_id}/compare",
    response_model=VersionDiffOutput,
)
async def compare_script_versions(
    script_id: UUID,
    left: Annotated[UUID, Query()],
    right: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VersionDiffOutput:
    repository = ScriptRepository(session)
    left_version = await repository.get_version(left)
    right_version = await repository.get_version(right)
    if (
        left_version is None
        or right_version is None
        or left_version.generation_id != script_id
        or right_version.generation_id != script_id
    ):
        raise ApiProblem(
            status=404,
            code="SCRIPT_VERSION_NOT_FOUND",
            title="Script version not found",
            detail="Both versions must belong to the requested script.",
        )
    return VersionDiffOutput(**diff_versions(left_version.draft, right_version.draft))


@router.get("/api/v1/scripts/{script_id}/versions/{version_id}/export")
async def export_script_version(
    script_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    format: Annotated[Literal["json", "markdown"], Query()] = "json",
) -> PlainTextResponse:
    repository = ScriptRepository(session)
    generation = await repository.get_generation(script_id)
    version = await repository.get_version(version_id)
    if generation is None or version is None or version.generation_id != script_id:
        raise ApiProblem(
            status=404,
            code="SCRIPT_VERSION_NOT_FOUND",
            title="Script version not found",
            detail="The requested script version does not exist.",
        )
    if format == "markdown":
        return PlainTextResponse(
            export_markdown(generation, version),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="script-{version.id}.md"'},
        )
    return PlainTextResponse(
        export_json(generation, version),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="script-{version.id}.json"'},
    )


@router.get("/api/v1/creative-patterns")
async def list_creative_patterns() -> list[dict[str, object]]:
    return [
        {
            "key": item.key,
            "version": item.version,
            "name": item.name,
            "hook_type": item.hook_type,
            "phase_sequence": item.phase_sequence,
            "shot_roles": item.shot_roles,
            "supported_durations": item.supported_durations,
        }
        for item in CREATIVE_PATTERNS
    ]
