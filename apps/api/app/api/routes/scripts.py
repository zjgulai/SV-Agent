import logging
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError
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
    ScriptFactContractItem,
    ScriptFactContractOutput,
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
from app.application.exports import export_json, export_markdown
from app.application.generations import (
    AudienceProfileUnsupportedError,
    CreativePatternNotFoundError,
    DurationNotSupportedError,
    FactSelectionInvalidError,
    FactsNotReadyError,
    GenerationCommand,
    GenerationIdempotencyConflictError,
    GenerationProductNotFoundError,
    GenerationService,
    LanguageNotSupportedError,
    PromotionNotActiveError,
    PromotionSelectionInvalidError,
)
from app.application.outbox import publish_job_outbox
from app.application.script_revisions import (
    FactBinding,
    FactRebindCommand,
    ScriptParentNotAcceptableError,
    ScriptRevisionFactsNotReadyError,
    ScriptRevisionIdempotencyConflictError,
    ScriptRevisionInvalidError,
    ScriptRevisionNotFoundError,
    ScriptRevisionService,
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
from app.domain.scripts.models import ScriptDraft, ValidationReport
from app.domain.scripts.patterns import (
    CREATIVE_PATTERNS,
    SUPPORTED_PATTERN_LANGUAGES,
    compile_pattern,
)
from app.domain.scripts.storyboard import StoryboardPreflight, StoryboardPreview
from app.settings import provider_api_key_is_configured, settings
from app.worker.tasks import dispatch_job

router = APIRouter(tags=["scripts"])
LOGGER = logging.getLogger(__name__)


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
        revision_kind=cast(Literal["fact_rebind"] | None, record.revision_kind),
        actor_kind=cast(Literal["local_operator"] | None, record.actor_kind),
        reason_code=cast(Literal["fact_rebind"] | None, record.reason_code),
        operation_input_digest=record.operation_input_digest,
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
    products = ProductRepository(session)

    async def fact_contract(raw_ids: list[str]) -> list[ScriptFactContractItem]:
        contract: list[ScriptFactContractItem] = []
        for raw_id in raw_ids:
            fact = await products.get_fact(UUID(raw_id))
            if fact is None or fact.snapshot_id != generation.snapshot_id:
                raise RuntimeError("generation fact contract is unavailable")
            contract.append(
                ScriptFactContractItem(
                    id=fact.id,
                    claim=fact.claim,
                    status=fact.status,
                    snapshot_id=fact.snapshot_id,
                )
            )
        return contract

    return ScriptOutput(
        generation=_generation_output(generation),
        versions=[_version_output(item) for item in versions],
        fact_contract=ScriptFactContractOutput(
            selected=await fact_contract(generation.selected_fact_ids),
            excluded=await fact_contract(generation.excluded_fact_ids),
        ),
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
                    promotion_fact_id=payload.promotion_fact_id,
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
    except PromotionSelectionInvalidError as exc:
        raise ApiProblem(
            status=422,
            code="PROMOTION_SELECTION_INVALID",
            title="Promotion selection invalid",
            detail="The promotion must be a separate fact on the current snapshot.",
        ) from exc
    except PromotionNotActiveError as exc:
        raise ApiProblem(
            status=409,
            code="PROMOTION_NOT_ACTIVE",
            title="Promotion is not active",
            detail="Confirm or lock a currently active promotion before generation.",
        ) from exc
    except AudienceProfileUnsupportedError as exc:
        raise ApiProblem(
            status=422,
            code="AUDIENCE_PROFILE_UNSUPPORTED",
            title="Audience profile unavailable",
            detail="The selected audience profile is unavailable.",
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
    except LanguageNotSupportedError as exc:
        raise ApiProblem(
            status=422,
            code="LANGUAGE_NOT_SUPPORTED",
            title="Language not supported",
            detail="The selected creative pattern does not support this language.",
        ) from exc
    except GenerationIdempotencyConflictError as exc:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Idempotency conflict",
            detail="This Idempotency-Key was already used with different input.",
        ) from exc
    job = queued.job
    try:
        await publish_job_outbox(session, dispatch_job, job_id=job.id)
    except (OSError, SQLAlchemyError):
        # The durable event has already committed. The reconciler owns recovery.
        LOGGER.warning("immediate script outbox dispatch deferred", exc_info=True)
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
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> ScriptVersionOutput:
    try:
        async with session.begin():
            stored = await ScriptRevisionService(session).fact_rebind(
                script_id=script_id,
                parent_version_id=version_id,
                operation_key=idempotency_key,
                command=FactRebindCommand(
                    fact_bindings=tuple(
                        FactBinding(shot_index=item.shot_index, fact_id=item.fact_id)
                        for item in payload.fact_bindings
                    )
                ),
            )
    except ScriptRevisionNotFoundError as exc:
        raise ApiProblem(
            status=404,
            code="SCRIPT_VERSION_NOT_FOUND",
            title="Script version not found",
            detail="The requested script version does not exist.",
        ) from exc
    except ScriptParentNotAcceptableError as exc:
        raise ApiProblem(
            status=409,
            code="SCRIPT_PARENT_NOT_ACCEPTABLE",
            title="Script parent is not acceptable",
            detail="Only an acceptable script version can be fact-rebound.",
        ) from exc
    except ScriptRevisionFactsNotReadyError as exc:
        raise ApiProblem(
            status=409,
            code="FACTS_NOT_READY",
            title="Facts are not ready",
            detail="The frozen generation fact contract is no longer ready.",
        ) from exc
    except ScriptRevisionInvalidError as exc:
        raise ApiProblem(
            status=422,
            code="SCRIPT_EDIT_INVALID",
            title="Script edit invalid",
            detail="Each shot must bind exactly one selected fact.",
        ) from exc
    except ScriptRevisionIdempotencyConflictError as exc:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Idempotency conflict",
            detail="This Idempotency-Key was already used with different input.",
        ) from exc
    response.status_code = status.HTTP_201_CREATED if stored.created else status.HTTP_200_OK
    return _version_output(stored.version)


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
            "supported_durations": item.supported_durations,
            "supported_languages": SUPPORTED_PATTERN_LANGUAGES,
            "contracts": [
                compile_pattern(
                    item.key,
                    duration_seconds=duration_seconds,
                    language=language,
                ).model_dump(mode="json")
                for duration_seconds in item.supported_durations
                for language in SUPPORTED_PATTERN_LANGUAGES
            ],
        }
        for item in CREATIVE_PATTERNS
    ]
