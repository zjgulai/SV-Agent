from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.scripts.models import (
    FindingSeverity,
    ScriptDraft,
    ValidationFinding,
    ValidationReport,
)
from app.domain.scripts.storyboard import StoryboardPreflight, compile_storyboard_preflight
from app.domain.scripts.validation import validate_script


class StoryboardPreflightNotFoundError(Exception):
    pass


@dataclass(slots=True)
class StoryboardPreflightService:
    session: AsyncSession

    async def load(
        self, *, script_id: UUID, version_id: UUID, lock_facts: bool = False
    ) -> StoryboardPreflight:
        scripts = ScriptRepository(self.session)
        generation = await scripts.get_generation(script_id)
        version = await scripts.get_version(version_id)
        if generation is None or version is None or version.generation_id != script_id:
            raise StoryboardPreflightNotFoundError(str(version_id))

        product_facts = {
            item.id: item
            for item in await ProductRepository(self.session).list_facts(
                generation.snapshot_id, for_update=lock_facts
            )
        }
        selected, excluded, selection_findings = self._load_fact_contract(
            generation.selected_fact_ids,
            generation.excluded_fact_ids,
            product_facts,
        )
        draft = ScriptDraft.model_validate(version.draft)
        runtime_report = validate_script(
            draft,
            {item.id: item for item in selected},
            excluded_facts={item.id: item for item in excluded},
            creative_pattern_key=generation.pattern_key,
            phase_sequence=tuple(
                str(item)
                for item in generation.configuration["pattern_definition"]["phase_sequence"]
            ),
        )
        stored_report = ValidationReport.model_validate(version.validation_report)
        report = ValidationReport(
            findings=self._merge_findings(
                [*stored_report.findings, *runtime_report.findings, *selection_findings]
            )
        )
        return compile_storyboard_preflight(
            script_id=script_id,
            version_id=version_id,
            input_digest=generation.input_digest,
            pattern_key=generation.pattern_key,
            snapshot_id=generation.snapshot_id,
            selected_facts=selected,
            excluded_facts=excluded,
            draft=draft,
            validation_report=report,
        )

    @staticmethod
    def _load_fact_contract(
        selected_ids: list[str],
        excluded_ids: list[str],
        facts_by_id: dict[UUID, ProductFact],
    ) -> tuple[list[ProductFact], list[ProductFact], list[ValidationFinding]]:
        selected: list[ProductFact] = []
        excluded: list[ProductFact] = []
        findings: list[ValidationFinding] = []
        for index, raw_id in enumerate(selected_ids):
            fact = facts_by_id.get(UUID(raw_id))
            if fact is None:
                findings.append(
                    ValidationFinding(
                        rule_id="FACT_SELECTION_STALE",
                        path=f"selected_fact_ids[{index}]",
                        message="selected fact is no longer available on the frozen snapshot",
                        severity=FindingSeverity.BLOCKING,
                    )
                )
            elif fact.status not in {FactStatus.CONFIRMED, FactStatus.LOCKED}:
                findings.append(
                    ValidationFinding(
                        rule_id="FACTS_NOT_READY",
                        path=f"selected_fact_ids[{index}]",
                        message="selected fact is no longer confirmed or locked",
                        severity=FindingSeverity.BLOCKING,
                        evidence=fact.claim,
                    )
                )
            else:
                selected.append(fact)
        for index, raw_id in enumerate(excluded_ids):
            fact = facts_by_id.get(UUID(raw_id))
            if fact is None:
                findings.append(
                    ValidationFinding(
                        rule_id="FACT_SELECTION_STALE",
                        path=f"excluded_fact_ids[{index}]",
                        message="excluded fact is no longer available on the frozen snapshot",
                        severity=FindingSeverity.BLOCKING,
                    )
                )
            else:
                excluded.append(fact)
        return selected, excluded, findings

    @staticmethod
    def _merge_findings(
        findings: list[ValidationFinding],
    ) -> list[ValidationFinding]:
        unique = {
            (item.path, item.rule_id, item.message, item.evidence): item
            for item in findings
        }
        return [
            unique[key]
            for key in sorted(
                unique,
                key=lambda item: (
                    item[0],
                    item[1],
                    item[2],
                    item[3] or "",
                ),
            )
        ]
