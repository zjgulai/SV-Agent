from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import ProductRepository, ScriptRepository
from app.domain.common.canonical import canonical_digest
from app.domain.products.entities import FactStatus, ProductFact
from app.domain.products.promotion import PromotionRender, promotion_is_active, render_promotion
from app.domain.scripts.models import (
    FindingSeverity,
    ScriptDraft,
    ValidationFinding,
    ValidationReport,
)
from app.domain.scripts.patterns import load_persisted_pattern_definition
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
        pattern_definition = load_persisted_pattern_definition(
            generation.configuration["pattern_definition"],
            pattern_key=generation.pattern_key,
            pattern_version=generation.pattern_version,
            duration_seconds=int(generation.configuration["target_duration_seconds"]),
            language=str(generation.configuration["language"]),
        )
        promotion, promotion_findings = await self._load_promotion(
            generation.configuration,
            generation.snapshot_id,
            product_facts,
            language=str(generation.configuration["language"]),
        )
        runtime_report = validate_script(
            draft,
            {item.id: item for item in selected},
            excluded_facts={item.id: item for item in excluded},
            pattern_definition=pattern_definition,
            promotion=promotion,
        )
        stored_report = ValidationReport.model_validate(version.validation_report)
        report = ValidationReport(
            findings=self._merge_findings(
                [
                    *stored_report.findings,
                    *runtime_report.findings,
                    *selection_findings,
                    *promotion_findings,
                ]
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

    async def _load_promotion(
        self,
        configuration: Mapping[str, object],
        snapshot_id: UUID,
        facts_by_id: dict[UUID, ProductFact],
        *,
        language: str,
    ) -> tuple[PromotionRender | None, list[ValidationFinding]]:
        raw = configuration.get("promotion")
        if raw is None:
            return None, []
        if not isinstance(raw, dict):
            return None, [self._promotion_not_active_finding()]
        try:
            fact_id = UUID(str(raw["fact_id"]))
            digest = str(raw["value_digest"])
            text = str(raw["rendered_text"])
        except (KeyError, TypeError):
            return None, [self._promotion_not_active_finding()]
        except ValueError:
            return None, [self._promotion_not_active_finding()]
        fact = facts_by_id.get(fact_id)
        observed_at = await self.session.scalar(select(func.statement_timestamp()))
        if (
            fact is None
            or fact.snapshot_id != snapshot_id
            or fact.claim_type != "promotion"
            or canonical_digest(fact.value) != digest
            or not promotion_is_active(fact, now=observed_at)
        ):
            return None, [self._promotion_not_active_finding()]
        rendered = render_promotion(fact, language=language)
        if rendered.text != text:
            return None, [self._promotion_not_active_finding()]
        return rendered, []

    @staticmethod
    def _promotion_not_active_finding() -> ValidationFinding:
        return ValidationFinding(
            rule_id="PROMOTION_NOT_ACTIVE",
            path="promotion_fact_id",
            message="the frozen promotion is no longer active or valid",
            severity=FindingSeverity.BLOCKING,
        )

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
