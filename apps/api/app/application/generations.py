from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import JobRecord, ScriptGenerationRecord, ScriptVersionRecord
from app.adapters.db.repositories import (
    JobRepository,
    OutboxRepository,
    ProductRepository,
    ScriptRepository,
)
from app.application.outbox import task_name_for
from app.domain.common.canonical import canonical_digest
from app.domain.jobs.entities import TERMINAL_STATES, Job, JobState, JobType
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.products.promotion import PromotionRender, promotion_is_active, render_promotion
from app.domain.scripts.audience import audience_context
from app.domain.scripts.creative_contract import enforce_creative_contract
from app.domain.scripts.models import ScriptDraft
from app.domain.scripts.patterns import (
    CREATIVE_PATTERNS,
    PatternCompileError,
    compile_pattern,
    load_persisted_pattern_definition,
)
from app.domain.scripts.validation import validate_script
from app.ports.script_provider import (
    ProviderError,
    ScriptGenerationRequest,
    ScriptProvider,
    SupportedFact,
)


class GenerationProductNotFoundError(Exception):
    pass


class FactsNotReadyError(Exception):
    pass


class FactSelectionInvalidError(Exception):
    pass


class CreativePatternNotFoundError(Exception):
    pass


class DurationNotSupportedError(Exception):
    pass


class LanguageNotSupportedError(Exception):
    pass


class GenerationIdempotencyConflictError(Exception):
    pass


class PromotionSelectionInvalidError(Exception):
    pass


class PromotionNotActiveError(Exception):
    pass


class AudienceProfileUnsupportedError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class GenerationCommand:
    target_duration_seconds: int
    language: str
    audience: str
    creative_pattern_key: str
    selected_fact_ids: tuple[UUID, ...] = ()
    excluded_fact_ids: tuple[UUID, ...] = ()
    promotion_fact_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class QueuedGeneration:
    job: Job
    created: bool


@dataclass(frozen=True, slots=True)
class WorkerStart:
    should_execute: bool
    terminal_version_id: UUID | None
    attempt_token: int | None


class GenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)

    async def queue(
        self,
        *,
        product_id: UUID,
        idempotency_key: str,
        command: GenerationCommand,
        provider: str = "deterministic",
        model: str = "deterministic-v1",
    ) -> QueuedGeneration:
        snapshot = await self.products.get_latest_snapshot(product_id)
        if snapshot is None:
            raise GenerationProductNotFoundError(str(product_id))
        pattern = next(
            (item for item in CREATIVE_PATTERNS if item.key == command.creative_pattern_key), None
        )
        if pattern is None:
            raise CreativePatternNotFoundError(command.creative_pattern_key)
        if command.target_duration_seconds not in pattern.supported_durations:
            raise DurationNotSupportedError(str(command.target_duration_seconds))
        try:
            audience = audience_context(command.audience)
            compiled_pattern = compile_pattern(
                pattern.key,
                duration_seconds=command.target_duration_seconds,
                language=command.language,
                audience_profile_key=audience.profile_key,
            )
        except PatternCompileError as exc:
            raise LanguageNotSupportedError(command.language) from exc
        except ValueError as exc:
            raise AudienceProfileUnsupportedError(command.audience) from exc

        selected_fact_ids = list(command.selected_fact_ids)
        excluded_fact_ids = list(command.excluded_fact_ids)
        if not selected_fact_ids:
            raise FactsNotReadyError(str(product_id))
        if (
            len(set(selected_fact_ids)) != len(selected_fact_ids)
            or len(set(excluded_fact_ids)) != len(excluded_fact_ids)
            or set(selected_fact_ids) & set(excluded_fact_ids)
        ):
            raise FactSelectionInvalidError("fact IDs must be unique and disjoint")

        facts_by_id = {
            item.id: item for item in await self.products.list_facts(snapshot.id)
        }
        for fact_id in [*selected_fact_ids, *excluded_fact_ids]:
            if fact_id not in facts_by_id:
                raise FactSelectionInvalidError("fact must belong to the current snapshot")
        if any(
            facts_by_id[fact_id].status not in {FactStatus.CONFIRMED, FactStatus.LOCKED}
            for fact_id in selected_fact_ids
        ):
            raise FactsNotReadyError(str(product_id))
        if any(
            facts_by_id[fact_id].claim_type == "promotion"
            for fact_id in [*selected_fact_ids, *excluded_fact_ids]
        ):
            raise FactSelectionInvalidError(
                "promotion facts must use the separate promotion_fact_id field"
            )

        promotion: PromotionRender | None = None
        promotion_configuration: dict[str, str] | None = None
        if command.promotion_fact_id is not None:
            if compiled_pattern.cta_policy.mode != "server_promotion_final_cta":
                raise PromotionSelectionInvalidError(
                    "the selected pattern does not have a promotion CTA slot"
                )
            if command.promotion_fact_id in {*selected_fact_ids, *excluded_fact_ids}:
                raise PromotionSelectionInvalidError("promotion fact must not be selected or excluded")
            promotion_fact = facts_by_id.get(command.promotion_fact_id)
            if promotion_fact is None or promotion_fact.claim_type != "promotion":
                raise PromotionSelectionInvalidError("promotion fact must belong to the current snapshot")
            observed_at = await self.session.scalar(select(func.statement_timestamp()))
            if not promotion_is_active(promotion_fact, now=observed_at):
                raise PromotionNotActiveError(str(command.promotion_fact_id))
            promotion = render_promotion(promotion_fact, language=command.language)
            promotion_configuration = {
                "fact_id": str(promotion.fact_id),
                "value_digest": canonical_digest(promotion_fact.value),
                "rendered_text": promotion.text,
            }

        serialized_selected_fact_ids = [str(item) for item in selected_fact_ids]
        serialized_excluded_fact_ids = [str(item) for item in excluded_fact_ids]
        configuration: dict[str, Any] = {
            "target_duration_seconds": command.target_duration_seconds,
            "language": command.language,
            "audience": audience.label,
            "audience_profile": audience.model_dump(mode="json"),
            "promotion": promotion_configuration,
            "pattern_definition": compiled_pattern.model_dump(mode="json"),
        }
        input_digest = canonical_digest(
            {
                "snapshot_digest": snapshot.canonical_digest,
                "selected_fact_ids": serialized_selected_fact_ids,
                "excluded_fact_ids": serialized_excluded_fact_ids,
                "configuration": configuration,
                "pattern_key": pattern.key,
                "pattern_version": pattern.version,
                "provider": provider,
                "model": model,
                "prompt_contract_version": "1.3",
            }
        )
        generation_id = uuid4()
        job_id = uuid4()
        inserted_id = await self.session.scalar(
            insert(JobRecord)
            .values(
                id=job_id,
                job_type=JobType.SCRIPT_GENERATION.value,
                idempotency_key=idempotency_key,
                state=JobState.QUEUED.value,
                input_digest=input_digest,
                attempt_count=0,
                result_id=generation_id,
            )
            .on_conflict_do_nothing(constraint="uq_job_idempotency")
            .returning(JobRecord.id)
        )
        if inserted_id is not None:
            self.session.add(
                ScriptGenerationRecord(
                    id=generation_id,
                    snapshot_id=snapshot.id,
                    selected_fact_ids=serialized_selected_fact_ids,
                    excluded_fact_ids=serialized_excluded_fact_ids,
                    configuration=configuration,
                    pattern_key=pattern.key,
                    pattern_version=pattern.version,
                    provider=provider,
                    model=model,
                    prompt_contract_version="1.3",
                    input_digest=input_digest,
                )
            )
            await self.session.flush()
            jobs = JobRepository(self.session)
            created = await jobs.get(inserted_id)
            if created is None:
                raise RuntimeError("created generation job cannot be loaded")
            await jobs.append_event(created, event_type="job_created")
            await OutboxRepository(self.session).add_dispatch(
                created, task_name=task_name_for(JobType.SCRIPT_GENERATION)
            )
            return QueuedGeneration(job=created, created=True)

        existing = await JobRepository(self.session).get_by_idempotency(
            JobType.SCRIPT_GENERATION, idempotency_key
        )
        if existing is None:
            raise RuntimeError("idempotency insert returned no generation job")
        if existing.input_digest != input_digest:
            raise GenerationIdempotencyConflictError(idempotency_key)
        return QueuedGeneration(job=existing, created=False)


class GenerationWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        provider: ScriptProvider,
    ) -> None:
        self.session_factory = session_factory
        self.provider = provider

    async def run(self, job_id: UUID, *, allow_retry: bool = False) -> UUID | None:
        start = await self._start_or_replay(job_id, allow_retry=allow_retry)
        if not start.should_execute:
            return start.terminal_version_id
        assert start.attempt_token is not None
        attempt_token = start.attempt_token

        try:
            request = await self._load_request(job_id)
            draft = await self.provider.generate(request)
            draft = draft.model_copy(
                update={
                    "target_duration_seconds": request.target_duration_seconds,
                    "language": request.language,
                    "audience": request.audience,
                    "snapshot_id": request.snapshot_id,
                }
            )
            draft = enforce_creative_contract(
                draft,
                pattern=request.pattern_definition,
                promotion=request.promotion,
            )
            additional_attempts = max(
                0, int(getattr(self.provider, "last_attempt_count", 1)) - 1
            )
            validating_token = await self._mark_validating(
                job_id,
                attempt_token=attempt_token,
                additional_attempts=additional_attempts,
            )
            if validating_token is None:
                return None
            attempt_token = validating_token
            return await self._save_result(job_id, draft, attempt_token=attempt_token)
        except (SQLAlchemyError, OSError):
            raise
        except FactsNotReadyError:
            await self._mark_failed(
                job_id,
                "FACTS_NOT_READY",
                "Selected product facts are no longer confirmed or locked.",
                attempt_token=attempt_token,
            )
            return None
        except PromotionNotActiveError:
            await self._mark_failed(
                job_id,
                "PROMOTION_NOT_ACTIVE",
                "The selected promotion is no longer active.",
                attempt_token=attempt_token,
            )
            return None
        except ProviderError as exc:
            await self._mark_failed(
                job_id,
                exc.code,
                str(exc),
                attempt_token=attempt_token,
                additional_attempts=max(0, exc.attempt_count - 1),
            )
            return None
        except Exception:
            await self._mark_failed(
                job_id,
                "GENERATION_FAILED",
                "Script generation failed.",
                attempt_token=attempt_token,
            )
            raise

    async def fail_before_provider(
        self,
        job_id: UUID,
        *,
        code: str,
        detail: str,
        allow_retry: bool = False,
    ) -> None:
        start = await self._start_or_replay(job_id, allow_retry=allow_retry)
        if start.should_execute:
            assert start.attempt_token is not None
            await self._mark_failed(
                job_id, code, detail, attempt_token=start.attempt_token
            )

    async def _start_or_replay(self, job_id: UUID, *, allow_retry: bool) -> WorkerStart:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if job is None or job.job_type is not JobType.SCRIPT_GENERATION:
                raise LookupError(f"script generation job {job_id} does not exist")
            if job.state in TERMINAL_STATES:
                return WorkerStart(
                    False, await self._latest_version_id(session, job), None
                )
            if job.state is JobState.QUEUED:
                job = job.transition_to(JobState.GENERATING)
            elif allow_retry:
                job = job.register_retry()
            else:
                return WorkerStart(False, None, None)
            await jobs.save(job)
            return WorkerStart(True, None, job.attempt_count)

    async def _load_request(self, job_id: UUID) -> ScriptGenerationRequest:
        async with self.session_factory() as session, session.begin():
            job = await JobRepository(session).get(job_id)
            if job is None or job.result_id is None:
                raise LookupError(f"generation job {job_id} has no generation")
            generation = await ScriptRepository(session).get_generation(job.result_id)
            if generation is None:
                raise LookupError(f"generation {job.result_id} does not exist")
            products = ProductRepository(session)
            snapshot = await products.get_snapshot(generation.snapshot_id)
            if snapshot is None:
                raise LookupError(f"snapshot {generation.snapshot_id} does not exist")
            facts: list[ProductFact] = []
            for raw_id in generation.selected_fact_ids:
                fact = await products.get_fact(UUID(raw_id))
                if fact is None or fact.status not in {
                    FactStatus.CONFIRMED,
                    FactStatus.LOCKED,
                } or fact.snapshot_id != snapshot.id:
                    raise FactsNotReadyError(str(raw_id))
                facts.append(fact)
            excluded_facts: list[ProductFact] = []
            for raw_id in generation.excluded_fact_ids:
                fact = await products.get_fact(UUID(raw_id))
                if fact is None or fact.snapshot_id != snapshot.id:
                    raise FactsNotReadyError(str(raw_id))
                excluded_facts.append(fact)
            pattern_definition = load_persisted_pattern_definition(
                generation.configuration["pattern_definition"],
                pattern_key=generation.pattern_key,
                pattern_version=generation.pattern_version,
                duration_seconds=int(generation.configuration["target_duration_seconds"]),
                language=str(generation.configuration["language"]),
            )
            request = ScriptGenerationRequest(
                snapshot_id=snapshot.id,
                title=snapshot.title,
                facts=[
                    SupportedFact(id=item.id, claim=item.claim, claim_type=item.claim_type)
                    for item in facts
                ],
                excluded_facts=[
                    SupportedFact(id=item.id, claim=item.claim, claim_type=item.claim_type)
                    for item in excluded_facts
                ],
                target_duration_seconds=int(
                    generation.configuration["target_duration_seconds"]
                ),
                language=str(generation.configuration["language"]),
                audience=str(generation.configuration["audience"]),
                pattern_definition=pattern_definition,
                promotion=await _load_generation_promotion(
                    session, products, generation, language=str(generation.configuration["language"])
                ),
            )
            return request

    async def _mark_validating(
        self,
        job_id: UUID,
        *,
        attempt_token: int,
        additional_attempts: int = 0,
    ) -> int | None:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if job is None:
                raise LookupError(str(job_id))
            if job.attempt_count != attempt_token or job.state not in {
                JobState.GENERATING,
                JobState.VALIDATING,
            }:
                return None
            for _ in range(additional_attempts):
                job = job.register_retry()
            if job.state is JobState.GENERATING:
                job = job.transition_to(JobState.VALIDATING)
            await jobs.save(job)
            return job.attempt_count

    async def _save_result(
        self,
        job_id: UUID,
        draft: ScriptDraft,
        *,
        attempt_token: int,
    ) -> UUID | None:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if job is None or job.result_id is None:
                raise LookupError(str(job_id))
            if job.attempt_count != attempt_token:
                return await self._latest_version_id(session, job)
            if job.state is not JobState.VALIDATING:
                return await self._latest_version_id(session, job)
            generation = await ScriptRepository(session).get_generation(job.result_id)
            if generation is None:
                raise LookupError(str(job.result_id))
            products = ProductRepository(session)
            facts: dict[UUID, ProductFact] = {}
            for raw_id in generation.selected_fact_ids:
                fact = await products.get_fact(UUID(raw_id), for_update=True)
                if fact is None or fact.snapshot_id != generation.snapshot_id:
                    raise FactsNotReadyError(str(raw_id))
                facts[fact.id] = fact
            excluded_facts: dict[UUID, ProductFact] = {}
            for raw_id in generation.excluded_fact_ids:
                fact = await products.get_fact(UUID(raw_id), for_update=True)
                if fact is None or fact.snapshot_id != generation.snapshot_id:
                    raise FactsNotReadyError(str(raw_id))
                excluded_facts[fact.id] = fact
            pattern_definition = load_persisted_pattern_definition(
                generation.configuration["pattern_definition"],
                pattern_key=generation.pattern_key,
                pattern_version=generation.pattern_version,
                duration_seconds=int(generation.configuration["target_duration_seconds"]),
                language=str(generation.configuration["language"]),
            )
            report = validate_script(
                draft,
                facts,
                excluded_facts=excluded_facts,
                pattern_definition=pattern_definition,
                promotion=await _load_generation_promotion(
                    session,
                    products,
                    generation,
                    language=str(generation.configuration["language"]),
                ),
            )
            version = ScriptVersionRecord(
                id=uuid4(),
                generation_id=job.result_id,
                parent_version_id=None,
                draft=draft.model_dump(mode="json"),
                validation_report=report.model_dump(mode="json"),
            )
            await ScriptRepository(session).add_version(version)
            terminal = JobState.SUCCEEDED if report.acceptable else JobState.VALIDATION_FAILED
            await jobs.save(job.transition_to(terminal))
            return version.id

    async def _mark_failed(
        self,
        job_id: UUID,
        code: str,
        detail: str,
        *,
        attempt_token: int,
        additional_attempts: int = 0,
    ) -> None:
        async with self.session_factory() as session, session.begin():
            jobs = JobRepository(session)
            job = await jobs.get(job_id, for_update=True)
            if (
                job is None
                or job.state in TERMINAL_STATES
                or job.attempt_count != attempt_token
            ):
                return
            for _ in range(additional_attempts):
                job = job.register_retry()
            await jobs.save(
                job.transition_to(
                    JobState.FAILED,
                    error_code=code,
                    error_detail=detail[:500] or "Provider failed.",
                )
            )

    @staticmethod
    async def _latest_version_id(session: AsyncSession, job: Job) -> UUID | None:
        if job.result_id is None:
            return None
        return await session.scalar(
            select(ScriptVersionRecord.id)
            .where(ScriptVersionRecord.generation_id == job.result_id)
            .order_by(ScriptVersionRecord.created_at.desc(), ScriptVersionRecord.id.desc())
            .limit(1)
        )


async def _load_generation_promotion(
    session: AsyncSession,
    products: ProductRepository,
    generation: ScriptGenerationRecord,
    *,
    language: str,
) -> PromotionRender | None:
    raw = generation.configuration.get("promotion")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise PromotionNotActiveError("frozen promotion configuration is invalid")
    try:
        fact_id = UUID(str(raw["fact_id"]))
        frozen_digest = str(raw["value_digest"])
        frozen_text = str(raw["rendered_text"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PromotionNotActiveError("frozen promotion configuration is invalid") from exc
    fact = await products.get_fact(fact_id, for_update=True)
    observed_at = await session.scalar(select(func.statement_timestamp()))
    if (
        fact is None
        or fact.snapshot_id != generation.snapshot_id
        or fact.claim_type != "promotion"
        or canonical_digest(fact.value) != frozen_digest
        or not promotion_is_active(fact, now=observed_at)
    ):
        raise PromotionNotActiveError(str(fact_id))
    rendered = render_promotion(fact, language=language)
    if rendered.text != frozen_text:
        raise PromotionNotActiveError(str(fact_id))
    return rendered
