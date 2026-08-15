from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ScriptVersionRecord
from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.application.generations import _load_generation_promotion
from app.domain.common.canonical import canonical_digest
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.scripts.models import ScriptDraft
from app.domain.scripts.patterns import load_persisted_pattern_definition
from app.domain.scripts.validation import validate_script


class ScriptRevisionNotFoundError(Exception):
    pass


class ScriptParentNotAcceptableError(Exception):
    pass


class ScriptRevisionFactsNotReadyError(Exception):
    pass


class ScriptRevisionInvalidError(Exception):
    pass


class ScriptRevisionIdempotencyConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FactBinding:
    shot_index: int
    fact_id: UUID


@dataclass(frozen=True, slots=True)
class FactRebindCommand:
    fact_bindings: tuple[FactBinding, ...]


@dataclass(frozen=True, slots=True)
class StoredScriptRevision:
    version: ScriptVersionRecord
    created: bool


class ScriptRevisionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scripts = ScriptRepository(session)
        self.products = ProductRepository(session)

    async def fact_rebind(
        self,
        *,
        script_id: UUID,
        parent_version_id: UUID,
        operation_key: str,
        command: FactRebindCommand,
    ) -> StoredScriptRevision:
        generation = await self.scripts.get_generation(script_id)
        parent = await self.scripts.get_version(parent_version_id)
        if generation is None or parent is None or parent.generation_id != script_id:
            raise ScriptRevisionNotFoundError(str(parent_version_id))

        input_digest = canonical_digest(
            {
                "contract_version": "p1.2a-fact-rebind-v1",
                "parent_version_id": str(parent_version_id),
                "fact_bindings": [
                    {"shot_index": item.shot_index, "fact_id": str(item.fact_id)}
                    for item in command.fact_bindings
                ],
            }
        )
        replay = await self.scripts.get_version_by_operation(
            parent_version_id=parent_version_id,
            operation_key=operation_key,
        )
        if replay is not None:
            if replay.operation_input_digest != input_digest:
                raise ScriptRevisionIdempotencyConflictError(operation_key)
            return StoredScriptRevision(version=replay, created=False)

        parent_draft = ScriptDraft.model_validate(parent.draft)
        if not bool(parent.validation_report.get("acceptable", False)):
            raise ScriptParentNotAcceptableError(str(parent_version_id))
        pattern_definition = load_persisted_pattern_definition(
            generation.configuration["pattern_definition"],
            pattern_key=generation.pattern_key,
            pattern_version=generation.pattern_version,
            duration_seconds=int(generation.configuration["target_duration_seconds"]),
            language=str(generation.configuration["language"]),
        )
        if (
            len(parent_draft.phases) != len(pattern_definition.phases)
            or len(parent_draft.shots) != len(pattern_definition.shots)
        ):
            raise ScriptParentNotAcceptableError(str(parent_version_id))

        facts = await self._load_selected_facts(generation.snapshot_id, generation.selected_fact_ids)
        excluded_facts = await self._load_excluded_facts(
            generation.snapshot_id, generation.excluded_fact_ids
        )
        bindings = self._bindings_by_index(command, shot_count=len(parent_draft.shots))
        if any(fact_id not in facts for fact_id in bindings.values()):
            raise ScriptRevisionInvalidError("bindings must reference selected facts")

        shots = [
            shot.model_copy(
                update={
                    "voiceover": facts[bindings[index]].claim,
                    "caption": facts[bindings[index]].claim,
                    "product_claims": [facts[bindings[index]].claim],
                    "supported_fact_ids": [facts[bindings[index]].id],
                }
            )
            for index, shot in enumerate(parent_draft.shots)
        ]
        draft = parent_draft.model_copy(
            update={
                "snapshot_id": generation.snapshot_id,
                "shots": shots,
            }
        )
        report = validate_script(
            draft,
            facts,
            excluded_facts=excluded_facts,
            pattern_definition=pattern_definition,
            promotion=await _load_generation_promotion(
                self.session,
                self.products,
                generation,
                language=str(generation.configuration["language"]),
            ),
        )
        if not report.acceptable:
            raise ScriptRevisionInvalidError("fact rebind did not satisfy the frozen contract")

        version = ScriptVersionRecord(
            id=uuid4(),
            generation_id=script_id,
            parent_version_id=parent_version_id,
            draft=draft.model_dump(mode="json"),
            validation_report=report.model_dump(mode="json"),
            revision_kind="fact_rebind",
            actor_kind="local_operator",
            reason_code="fact_rebind",
            operation_key=operation_key,
            operation_input_digest=input_digest,
        )
        stored, created = await self.scripts.insert_fact_rebind_version(version)
        if not created and stored.operation_input_digest != input_digest:
            raise ScriptRevisionIdempotencyConflictError(operation_key)
        return StoredScriptRevision(version=stored, created=created)

    async def _load_selected_facts(
        self, snapshot_id: UUID, raw_ids: list[str]
    ) -> dict[UUID, ProductFact]:
        facts: dict[UUID, ProductFact] = {}
        for raw_id in raw_ids:
            fact = await self.products.get_fact(UUID(raw_id), for_update=True)
            if (
                fact is None
                or fact.snapshot_id != snapshot_id
                or fact.status not in {FactStatus.CONFIRMED, FactStatus.LOCKED}
            ):
                raise ScriptRevisionFactsNotReadyError(raw_id)
            facts[fact.id] = fact
        return facts

    async def _load_excluded_facts(
        self, snapshot_id: UUID, raw_ids: list[str]
    ) -> dict[UUID, ProductFact]:
        facts: dict[UUID, ProductFact] = {}
        for raw_id in raw_ids:
            fact = await self.products.get_fact(UUID(raw_id), for_update=True)
            if fact is None or fact.snapshot_id != snapshot_id:
                raise ScriptRevisionFactsNotReadyError(raw_id)
            facts[fact.id] = fact
        return facts

    @staticmethod
    def _bindings_by_index(
        command: FactRebindCommand, *, shot_count: int
    ) -> dict[int, UUID]:
        bindings = {item.shot_index: item.fact_id for item in command.fact_bindings}
        if len(bindings) != len(command.fact_bindings) or set(bindings) != set(range(shot_count)):
            raise ScriptRevisionInvalidError("bindings must cover every shot exactly once")
        return bindings
