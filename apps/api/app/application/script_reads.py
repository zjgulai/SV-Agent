from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ScriptGenerationRecord, ScriptVersionRecord
from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.application.exports import export_json, export_markdown
from app.application.sv_agent.read_tools.contracts import (
    ReadResult,
    ScriptDiffEntry,
    ScriptDiffProjection,
    ScriptDiffQuery,
    ScriptExportProjection,
    ScriptExportQuery,
    ScriptFactProjection,
    ScriptGenerationProjection,
    ScriptInspectQuery,
    ScriptProjection,
    ScriptReadInput,
    ScriptReadOutput,
    ScriptReadValue,
    ScriptVersionProjection,
    ScriptVersionQuery,
)
from app.application.sv_agent.read_tools.errors import ReadToolSourceFailure
from app.application.version_diff import diff_versions
from app.domain.scripts.models import ScriptDraft, ValidationReport


class ScriptReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._scripts = ScriptRepository(session)
        self._products = ProductRepository(session)

    async def inspect(self, command: ScriptReadInput) -> ScriptReadOutput:
        query = command.query
        if isinstance(query, ScriptInspectQuery):
            return await self._inspect_script(query)
        if isinstance(query, ScriptVersionQuery):
            return await self._inspect_version(query)
        if isinstance(query, ScriptDiffQuery):
            return await self._inspect_diff(query)
        return await self._inspect_export(query)

    async def _inspect_script(self, query: ScriptInspectQuery) -> ScriptReadOutput:
        generation = await self._scripts.get_generation(query.script_id)
        if generation is None:
            return self._not_found(
                "inspect",
                "SCRIPT_NOT_FOUND",
                subject_ref=str(query.script_id),
            )
        versions = await self._scripts.list_versions(query.script_id)
        selected = await self._facts(generation, generation.selected_fact_ids)
        excluded = await self._facts(generation, generation.excluded_fact_ids)
        projection = ScriptProjection(
            generation=self._generation(generation),
            versions=tuple(self._version(item) for item in versions[: query.version_limit]),
            selected_facts=selected,
            excluded_facts=excluded,
        )
        return ScriptReadOutput(
            action="inspect",
            result=ReadResult[ScriptReadValue].found(projection),
        )

    async def _inspect_version(self, query: ScriptVersionQuery) -> ScriptReadOutput:
        version = await self._scripts.get_version(query.version_id)
        if version is None or version.generation_id != query.script_id:
            return self._not_found(
                "version",
                "SCRIPT_VERSION_NOT_FOUND",
                subject_ref=f"{query.script_id}:{query.version_id}",
            )
        return ScriptReadOutput(
            action="version",
            result=ReadResult[ScriptReadValue].found(self._version(version)),
        )

    async def _inspect_diff(self, query: ScriptDiffQuery) -> ScriptReadOutput:
        left = await self._scripts.get_version(query.left_version_id)
        right = await self._scripts.get_version(query.right_version_id)
        if (
            left is None
            or right is None
            or left.generation_id != query.script_id
            or right.generation_id != query.script_id
        ):
            return self._not_found(
                "diff",
                "SCRIPT_VERSION_NOT_FOUND",
                subject_ref=(f"{query.script_id}:{query.left_version_id}:{query.right_version_id}"),
            )
        raw = diff_versions(left.draft, right.draft)
        projection = ScriptDiffProjection(
            script_id=query.script_id,
            left_version_id=query.left_version_id,
            right_version_id=query.right_version_id,
            added=tuple(ScriptDiffEntry.model_validate(item) for item in raw["added"]),
            removed=tuple(ScriptDiffEntry.model_validate(item) for item in raw["removed"]),
            changed=tuple(ScriptDiffEntry.model_validate(item) for item in raw["changed"]),
        )
        return ScriptReadOutput(
            action="diff",
            result=ReadResult[ScriptReadValue].found(projection),
        )

    async def _inspect_export(self, query: ScriptExportQuery) -> ScriptReadOutput:
        generation = await self._scripts.get_generation(query.script_id)
        version = await self._scripts.get_version(query.version_id)
        if generation is None or version is None or version.generation_id != query.script_id:
            return self._not_found(
                "export",
                "SCRIPT_VERSION_NOT_FOUND",
                subject_ref=f"{query.script_id}:{query.version_id}",
            )
        if query.format == "markdown":
            projection = ScriptExportProjection(
                script_id=query.script_id,
                version_id=query.version_id,
                format="markdown",
                media_type="text/markdown",
                content=export_markdown(generation, version),
            )
        else:
            projection = ScriptExportProjection(
                script_id=query.script_id,
                version_id=query.version_id,
                format="json",
                media_type="application/json",
                content=export_json(generation, version),
            )
        return ScriptReadOutput(
            action="export",
            result=ReadResult[ScriptReadValue].found(projection),
        )

    async def _facts(
        self,
        generation: ScriptGenerationRecord,
        raw_ids: list[str],
    ) -> tuple[ScriptFactProjection, ...]:
        projections: list[ScriptFactProjection] = []
        for raw_id in raw_ids:
            try:
                fact_id = UUID(raw_id)
            except ValueError as exc:
                raise ReadToolSourceFailure(
                    "SCRIPT_FACT_CONTRACT_INVALID",
                    "Repair the stored Script fact contract before retrying the read.",
                ) from exc
            fact = await self._products.get_fact(fact_id)
            if fact is None or fact.snapshot_id != generation.snapshot_id:
                raise ReadToolSourceFailure(
                    "SCRIPT_FACT_CONTRACT_UNAVAILABLE",
                    "Restore the referenced Product Fact before retrying the read.",
                )
            projections.append(
                ScriptFactProjection(
                    id=fact.id,
                    snapshot_id=fact.snapshot_id,
                    claim=fact.claim,
                    status=fact.status,
                )
            )
        return tuple(projections)

    @staticmethod
    def _generation(record: ScriptGenerationRecord) -> ScriptGenerationProjection:
        try:
            target_duration_seconds = int(record.configuration["target_duration_seconds"])
            language = str(record.configuration["language"])
            raw_audience_profile = record.configuration["audience_profile"]
            if not isinstance(raw_audience_profile, Mapping):
                raise TypeError("audience profile is not a mapping")
            audience_profile_key = str(raw_audience_profile["profile_key"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReadToolSourceFailure(
                "SCRIPT_CONFIGURATION_INVALID",
                "Repair the immutable generation configuration before retrying the read.",
            ) from exc
        return ScriptGenerationProjection(
            id=record.id,
            snapshot_id=record.snapshot_id,
            selected_fact_ids=tuple(UUID(item) for item in record.selected_fact_ids),
            excluded_fact_ids=tuple(UUID(item) for item in record.excluded_fact_ids),
            target_duration_seconds=target_duration_seconds,
            language=language,
            audience_profile_key=audience_profile_key,
            pattern_key=record.pattern_key,
            pattern_version=record.pattern_version,
            provider=record.provider,
            model=record.model,
            prompt_contract_version=record.prompt_contract_version,
            input_digest=record.input_digest,
            created_at=record.created_at,
        )

    @staticmethod
    def _version(record: ScriptVersionRecord) -> ScriptVersionProjection:
        try:
            draft = ScriptDraft.model_validate(record.draft, extra="forbid")
            report = ValidationReport.model_validate(record.validation_report)
        except (TypeError, ValueError) as exc:
            raise ReadToolSourceFailure(
                "SCRIPT_VERSION_INVALID",
                "Repair the immutable ScriptVersion payload before retrying the read.",
            ) from exc
        return ScriptVersionProjection(
            id=record.id,
            generation_id=record.generation_id,
            parent_version_id=record.parent_version_id,
            draft=draft,
            validation_report=report,
            revision_kind=record.revision_kind,
            actor_kind=record.actor_kind,
            reason_code=record.reason_code,
            operation_input_digest=record.operation_input_digest,
            created_at=record.created_at,
        )

    @staticmethod
    def _not_found(
        action: str,
        code: str,
        *,
        subject_ref: str,
    ) -> ScriptReadOutput:
        return ScriptReadOutput(
            action=action,  # type: ignore[arg-type]
            result=ReadResult[ScriptReadValue].not_found(
                code,
                subject_ref=subject_ref,
            ),
        )
