from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ScriptGenerationRecord, ScriptVersionRecord
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


@dataclass(frozen=True, slots=True)
class StoryboardPreflightEvaluation:
    preflight: StoryboardPreflight
    fact_contract_findings: tuple[ValidationFinding, ...]
    promotion_findings: tuple[ValidationFinding, ...]
    stored_validation_report: ValidationReport
    live_validation_report: ValidationReport


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

        product_facts, observed_at = await ProductRepository(
            self.session
        ).list_facts_at_observation(generation.snapshot_id, for_update=lock_facts)
        return self.evaluate_loaded(
            generation=generation,
            version=version,
            product_facts=product_facts,
            observed_at=observed_at,
        ).preflight

    def evaluate_loaded(
        self,
        *,
        generation: ScriptGenerationRecord,
        version: ScriptVersionRecord,
        product_facts: Mapping[UUID, ProductFact] | Sequence[ProductFact],
        observed_at: datetime,
        strict_draft: bool = False,
    ) -> StoryboardPreflightEvaluation:
        facts_by_id = (
            dict(product_facts)
            if isinstance(product_facts, Mapping)
            else {item.id: item for item in product_facts}
        )
        selected, excluded, selection_findings = self._load_fact_contract(
            generation.selected_fact_ids,
            generation.excluded_fact_ids,
            facts_by_id,
        )
        draft = ScriptDraft.model_validate(
            version.draft, extra="forbid" if strict_draft else None
        )
        pattern_definition = load_persisted_pattern_definition(
            generation.configuration["pattern_definition"],
            pattern_key=generation.pattern_key,
            pattern_version=generation.pattern_version,
            duration_seconds=int(generation.configuration["target_duration_seconds"]),
            language=str(generation.configuration["language"]),
        )
        promotion, promotion_findings = self._load_promotion(
            generation.configuration,
            generation.snapshot_id,
            facts_by_id,
            language=str(generation.configuration["language"]),
            observed_at=observed_at,
        )
        runtime_report = validate_script(
            draft,
            {item.id: item for item in selected},
            excluded_facts={item.id: item for item in excluded},
            pattern_definition=pattern_definition,
            promotion=promotion,
        )
        stored_report = self._load_stored_report(
            version.validation_report, strict=strict_draft
        )
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
        preflight = compile_storyboard_preflight(
            script_id=generation.id,
            version_id=version.id,
            input_digest=generation.input_digest,
            pattern_key=generation.pattern_key,
            snapshot_id=generation.snapshot_id,
            selected_facts=selected,
            excluded_facts=excluded,
            draft=draft,
            validation_report=report,
        )
        return StoryboardPreflightEvaluation(
            preflight=preflight,
            fact_contract_findings=tuple(selection_findings),
            promotion_findings=tuple(promotion_findings),
            stored_validation_report=stored_report,
            live_validation_report=runtime_report,
        )

    @staticmethod
    def _load_stored_report(
        raw: Mapping[str, object], *, strict: bool
    ) -> ValidationReport:
        if not strict:
            return ValidationReport.model_validate(raw)
        allowed = {"findings", "blocking", "acceptable"}
        if set(raw) - allowed:
            raise ValueError("stored validation report contains unknown fields")
        report = ValidationReport.model_validate(
            {"findings": raw.get("findings")}, extra="forbid"
        )
        serialized = report.model_dump(mode="json")
        if raw.get("blocking") != serialized["blocking"]:
            raise ValueError("stored validation blocking projection is inconsistent")
        if raw.get("acceptable") != serialized["acceptable"]:
            raise ValueError("stored validation acceptable projection is inconsistent")
        return report

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

    def _load_promotion(
        self,
        configuration: Mapping[str, object],
        snapshot_id: UUID,
        facts_by_id: dict[UUID, ProductFact],
        *,
        language: str,
        observed_at: datetime,
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
