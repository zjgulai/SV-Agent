from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.creative_comparison_lab import (
    CreativeComparisonIntegrityError,
    CreativeComparisonLab,
    CreativeComparisonReferenceInvalidError,
    CreativeComparisonRequest,
    CreativeComparisonSubjectNotFoundError,
)
from app.application.job_reads import JobReadService
from app.application.products import ProductNotFoundError, ProductService
from app.application.script_reads import ScriptReadService
from app.application.storyboard_reads import StoryboardReadService
from app.application.sv_agent_tool_contracts import (
    CreativeComparisonReadInput,
    CreativeComparisonReadOutput,
    JobReadInput,
    PatternContractReadInput,
    PatternContractReadOutput,
    ProductFactProjection,
    ProductSnapshotProjection,
    ProductTruthProjection,
    ProductTruthReadInput,
    ProductTruthReadOutput,
    ReadResult,
    ReadToolInput,
    ReadToolName,
    ReadToolOutput,
    ScriptReadInput,
    StoryboardReadInput,
)
from app.application.sv_agent_tool_errors import ReadToolSourceFailure
from app.domain.scripts.patterns import PatternCompileError, compile_pattern


class ApplicationReadToolRuntime:
    """Adapter-free tool facade over existing application query services."""

    def __init__(self, session: AsyncSession) -> None:
        self._products = ProductService(session)
        self._jobs = JobReadService(session)
        self._scripts = ScriptReadService(session)
        self._storyboards = StoryboardReadService(session)
        self._comparisons = CreativeComparisonLab(session)

    def supports(self, name: ReadToolName) -> bool:
        return name in ReadToolName

    async def execute(self, command: ReadToolInput) -> ReadToolOutput:
        if isinstance(command, ProductTruthReadInput):
            return await self._inspect_product_truth(command)
        if isinstance(command, PatternContractReadInput):
            return self._inspect_pattern(command)
        if isinstance(command, JobReadInput):
            return await self._jobs.inspect(command)
        if isinstance(command, ScriptReadInput):
            return await self._scripts.inspect(command)
        if isinstance(command, StoryboardReadInput):
            return await self._storyboards.inspect(command)
        return await self._inspect_comparison(command)

    async def _inspect_product_truth(
        self,
        command: ProductTruthReadInput,
    ) -> ProductTruthReadOutput:
        try:
            product = await self._products.get_product(command.product_id)
        except ProductNotFoundError:
            return ProductTruthReadOutput.not_found(
                product_id=command.product_id,
                code="PRODUCT_NOT_FOUND",
            )
        snapshot = product.snapshot
        projection = ProductTruthProjection(
            product_id=product.product_id,
            snapshot=ProductSnapshotProjection(
                id=snapshot.id,
                source_id=snapshot.source_id,
                title=snapshot.title,
                description=snapshot.description,
                category_path=snapshot.category_path,
                images=snapshot.images,
                price_amount=snapshot.price_amount,
                price_currency=snapshot.price_currency,
                canonical_digest=snapshot.canonical_digest,
                created_at=snapshot.created_at,
            ),
            facts=tuple(
                ProductFactProjection(
                    id=fact.id,
                    snapshot_id=fact.snapshot_id,
                    claim_type=fact.claim_type,
                    claim=fact.claim,
                    evidence_kind=fact.evidence_kind,
                    evidence_locator=fact.evidence_locator,
                    evidence_excerpt=fact.evidence_excerpt,
                    confidence=fact.confidence,
                    status=fact.status,
                    updated_at=fact.updated_at,
                )
                for fact in product.facts
            ),
        )
        return ProductTruthReadOutput(result=ReadResult[ProductTruthProjection].found(projection))

    @staticmethod
    def _inspect_pattern(
        command: PatternContractReadInput,
    ) -> PatternContractReadOutput:
        try:
            contract = compile_pattern(
                command.pattern_key,
                duration_seconds=command.duration_seconds,
                language=command.language,
                audience_profile_key=command.audience_profile_key,
            )
            if contract.version != command.pattern_version:
                raise PatternCompileError("requested pattern version is unavailable")
        except (PatternCompileError, ValueError):
            return PatternContractReadOutput(
                result=ReadResult.not_found(
                    "PATTERN_CONTRACT_NOT_FOUND",
                    subject_ref=(
                        f"{command.pattern_key}@{command.pattern_version}:"
                        f"{command.duration_seconds}:{command.language}:"
                        f"{command.audience_profile_key}"
                    ),
                )
            )
        return PatternContractReadOutput(result=ReadResult.found(contract))

    async def _inspect_comparison(
        self,
        command: CreativeComparisonReadInput,
    ) -> CreativeComparisonReadOutput:
        try:
            projection = await self._comparisons.inspect(
                CreativeComparisonRequest(
                    script_id=command.script_id,
                    control_version_id=command.control_version_id,
                    variant_version_id=command.variant_version_id,
                )
            )
        except CreativeComparisonSubjectNotFoundError:
            return CreativeComparisonReadOutput(
                result=ReadResult.not_found(
                    "COMPARISON_SUBJECT_NOT_FOUND",
                    subject_ref=(
                        f"{command.script_id}:{command.control_version_id}:"
                        f"{command.variant_version_id}"
                    ),
                )
            )
        except CreativeComparisonReferenceInvalidError as exc:
            raise ReadToolSourceFailure(
                "COMPARISON_REFERENCE_INVALID",
                "Select two different ScriptVersions from the same Script and retry.",
            ) from exc
        except CreativeComparisonIntegrityError as exc:
            raise ReadToolSourceFailure(
                "PRODUCT_TRUTH_INTEGRITY_ERROR",
                "Repair the stored Product Truth or ScriptVersion data before retrying.",
            ) from exc
        return CreativeComparisonReadOutput(result=ReadResult.found(projection))
