from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    JobRecord,
    ProductFactRecord,
    ProductSnapshotRecord,
    ProductSourceRecord,
    ScriptGenerationRecord,
    ScriptVersionRecord,
    StoryboardApprovalEventRecord,
    StoryboardVersionRecord,
)
from app.domain.jobs.entities import Job, JobState, JobType
from app.domain.products.entities import (
    FactStatus,
    ParseStatus,
    ProductFact,
    ProductSnapshot,
    ProductSource,
    SourceType,
)


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_source(self, source: ProductSource) -> ProductSource:
        self.session.add(
            ProductSourceRecord(
                id=source.id,
                source_type=source.source_type.value,
                source_url=source.source_url,
                retrieved_at=source.retrieved_at,
                content_digest=source.content_digest,
                raw_payload=source.raw_payload,
                parse_status=source.parse_status.value,
                error_code=source.error_code,
            )
        )
        await self.session.flush()
        return source

    async def get_source(self, source_id: UUID) -> ProductSource | None:
        record = await self.session.get(ProductSourceRecord, source_id)
        return _source_from_record(record) if record is not None else None

    async def get_source_by_url(self, source_url: str) -> ProductSource | None:
        record = await self.session.scalar(
            select(ProductSourceRecord)
            .where(
                ProductSourceRecord.source_type == SourceType.SCHEMA_ORG_URL.value,
                ProductSourceRecord.source_url == source_url,
            )
            .order_by(ProductSourceRecord.retrieved_at, ProductSourceRecord.id)
            .limit(1)
        )
        return _source_from_record(record) if record is not None else None

    async def get_or_create_url_source(self, source_url: str) -> ProductSource:
        candidate = ProductSource.create(
            source_type=SourceType.SCHEMA_ORG_URL,
            source_url=source_url,
            raw_payload={},
            parse_status=ParseStatus.PENDING,
        )
        inserted_id = await self.session.scalar(
            insert(ProductSourceRecord)
            .values(
                id=candidate.id,
                source_type=candidate.source_type.value,
                source_url=candidate.source_url,
                retrieved_at=candidate.retrieved_at,
                content_digest=candidate.content_digest,
                raw_payload=candidate.raw_payload,
                parse_status=candidate.parse_status.value,
                error_code=candidate.error_code,
            )
            .on_conflict_do_nothing(
                index_elements=[ProductSourceRecord.source_url],
                index_where=text(
                    "source_type = 'schema_org_url' AND source_url IS NOT NULL"
                ),
            )
            .returning(ProductSourceRecord.id)
        )
        if inserted_id is not None:
            return candidate
        existing = await self.get_source_by_url(source_url)
        if existing is None:
            raise RuntimeError("URL source conflict returned no source")
        return existing

    async def list_sources(self) -> Sequence[ProductSource]:
        records = (
            await self.session.scalars(
                select(ProductSourceRecord).order_by(ProductSourceRecord.retrieved_at.desc())
            )
        ).all()
        return [_source_from_record(item) for item in records]

    async def add_snapshot(self, snapshot: ProductSnapshot) -> ProductSnapshot:
        self.session.add(
            ProductSnapshotRecord(
                id=snapshot.id,
                source_id=snapshot.source_id,
                title=snapshot.title,
                description=snapshot.description,
                category_path=list(snapshot.category_path),
                images=list(snapshot.images),
                price_amount=snapshot.price_amount,
                price_currency=snapshot.price_currency,
                canonical_digest=snapshot.canonical_digest,
                created_at=snapshot.created_at,
            )
        )
        await self.session.flush()
        return snapshot

    async def get_snapshot(self, snapshot_id: UUID) -> ProductSnapshot | None:
        record = await self.session.get(ProductSnapshotRecord, snapshot_id)
        return _snapshot_from_record(record) if record is not None else None

    async def get_latest_snapshot(self, source_id: UUID) -> ProductSnapshot | None:
        record = await self.session.scalar(
            select(ProductSnapshotRecord)
            .where(ProductSnapshotRecord.source_id == source_id)
            .order_by(ProductSnapshotRecord.created_at.desc(), ProductSnapshotRecord.id.desc())
            .limit(1)
        )
        return _snapshot_from_record(record) if record is not None else None

    async def list_snapshots(self, source_id: UUID) -> Sequence[ProductSnapshot]:
        records = (
            await self.session.scalars(
                select(ProductSnapshotRecord)
                .where(ProductSnapshotRecord.source_id == source_id)
                .order_by(ProductSnapshotRecord.created_at, ProductSnapshotRecord.id)
            )
        ).all()
        return [_snapshot_from_record(item) for item in records]

    async def add_fact(self, fact: ProductFact) -> ProductFact:
        self.session.add(
            ProductFactRecord(
                id=fact.id,
                snapshot_id=fact.snapshot_id,
                claim_type=fact.claim_type,
                claim=fact.claim,
                value=fact.value,
                evidence_kind=fact.evidence_kind,
                evidence_locator=fact.evidence_locator,
                evidence_excerpt=fact.evidence_excerpt,
                confidence=fact.confidence,
                status=fact.status.value,
                updated_at=fact.updated_at,
            )
        )
        await self.session.flush()
        return fact

    async def get_fact(self, fact_id: UUID, *, for_update: bool = False) -> ProductFact | None:
        statement = select(ProductFactRecord).where(ProductFactRecord.id == fact_id)
        if for_update:
            statement = statement.with_for_update()
        record = await self.session.scalar(statement)
        return _fact_from_record(record) if record is not None else None

    async def list_facts(
        self, snapshot_id: UUID, *, for_update: bool = False
    ) -> Sequence[ProductFact]:
        statement = (
            select(ProductFactRecord)
            .where(ProductFactRecord.snapshot_id == snapshot_id)
            .order_by(ProductFactRecord.updated_at, ProductFactRecord.id)
        )
        if for_update:
            statement = statement.with_for_update()
        records = (await self.session.scalars(statement)).all()
        return [_fact_from_record(item) for item in records]

    async def save_fact(self, fact: ProductFact) -> ProductFact:
        record = await self.session.get(ProductFactRecord, fact.id)
        if record is None:
            raise LookupError(f"fact {fact.id} does not exist")
        record.status = fact.status.value
        record.updated_at = fact.updated_at
        await self.session.flush()
        return fact


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: UUID, *, for_update: bool = False) -> Job | None:
        statement = select(JobRecord).where(JobRecord.id == job_id)
        if for_update:
            statement = statement.with_for_update()
        record = await self.session.scalar(statement)
        return _job_from_record(record) if record is not None else None

    async def get_by_idempotency(self, job_type: JobType, key: str) -> Job | None:
        record = await self.session.scalar(
            select(JobRecord).where(
                JobRecord.job_type == job_type.value,
                JobRecord.idempotency_key == key,
            )
        )
        return _job_from_record(record) if record is not None else None

    async def save(self, job: Job) -> Job:
        record = await self.session.get(JobRecord, job.id)
        if record is None:
            raise LookupError(f"job {job.id} does not exist")
        record.state = job.state.value
        record.attempt_count = job.attempt_count
        record.error_code = job.error_code
        record.error_detail = job.error_detail
        record.result_id = job.result_id
        record.started_at = job.started_at
        record.finished_at = job.finished_at
        await self.session.flush()
        return job


class ScriptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_generation(self, generation_id: UUID) -> ScriptGenerationRecord | None:
        return await self.session.get(ScriptGenerationRecord, generation_id)

    async def add_version(self, version: ScriptVersionRecord) -> ScriptVersionRecord:
        self.session.add(version)
        await self.session.flush()
        return version

    async def list_versions(self, generation_id: UUID) -> Sequence[ScriptVersionRecord]:
        return (
            await self.session.scalars(
                select(ScriptVersionRecord)
                .where(ScriptVersionRecord.generation_id == generation_id)
                .order_by(ScriptVersionRecord.created_at, ScriptVersionRecord.id)
            )
        ).all()

    async def get_version(self, version_id: UUID) -> ScriptVersionRecord | None:
        return await self.session.get(ScriptVersionRecord, version_id)

    async def get_storyboard(
        self, storyboard_id: UUID, *, for_update: bool = False
    ) -> StoryboardVersionRecord | None:
        statement = select(StoryboardVersionRecord).where(
            StoryboardVersionRecord.id == storyboard_id
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def get_storyboard_by_operation(
        self, *, script_version_id: UUID, operation_key: str
    ) -> StoryboardVersionRecord | None:
        return await self.session.scalar(
            select(StoryboardVersionRecord).where(
                StoryboardVersionRecord.script_version_id == script_version_id,
                StoryboardVersionRecord.operation_key == operation_key,
            )
        )

    async def insert_storyboard(
        self, storyboard: StoryboardVersionRecord
    ) -> tuple[StoryboardVersionRecord, bool]:
        inserted_id = await self.session.scalar(
            insert(StoryboardVersionRecord)
            .values(
                id=storyboard.id,
                script_version_id=storyboard.script_version_id,
                snapshot_id=storyboard.snapshot_id,
                selected_fact_ids=storyboard.selected_fact_ids,
                excluded_fact_ids=storyboard.excluded_fact_ids,
                pattern_key=storyboard.pattern_key,
                pattern_version=storyboard.pattern_version,
                phase_sequence=storyboard.phase_sequence,
                draft=storyboard.draft,
                validation_report=storyboard.validation_report,
                preflight_digest=storyboard.preflight_digest,
                storyboard_digest=storyboard.storyboard_digest,
                preview_contract_version=storyboard.preview_contract_version,
                operation_key=storyboard.operation_key,
            )
            .on_conflict_do_nothing(constraint="uq_storyboard_version_operation")
            .returning(StoryboardVersionRecord.id)
        )
        if inserted_id is None:
            existing = await self.get_storyboard_by_operation(
                script_version_id=storyboard.script_version_id,
                operation_key=storyboard.operation_key,
            )
            if existing is None:
                raise RuntimeError("storyboard idempotency conflict returned no record")
            return existing, False
        created = await self.get_storyboard(inserted_id)
        if created is None:
            raise RuntimeError("created storyboard cannot be loaded")
        return created, True

    async def get_approval_event_by_operation(
        self, *, storyboard_id: UUID, operation_key: str
    ) -> StoryboardApprovalEventRecord | None:
        return await self.session.scalar(
            select(StoryboardApprovalEventRecord).where(
                StoryboardApprovalEventRecord.storyboard_id == storyboard_id,
                StoryboardApprovalEventRecord.operation_key == operation_key,
            )
        )

    async def get_latest_approval_event(
        self, storyboard_id: UUID
    ) -> StoryboardApprovalEventRecord | None:
        return await self.session.scalar(
            select(StoryboardApprovalEventRecord)
            .where(StoryboardApprovalEventRecord.storyboard_id == storyboard_id)
            .order_by(
                StoryboardApprovalEventRecord.event_sequence.desc(),
            )
            .limit(1)
        )

    async def insert_approval_event(
        self, event: StoryboardApprovalEventRecord
    ) -> tuple[StoryboardApprovalEventRecord, bool]:
        inserted_id = await self.session.scalar(
            insert(StoryboardApprovalEventRecord)
            .values(
                id=event.id,
                storyboard_id=event.storyboard_id,
                decision=event.decision,
                reason=event.reason,
                storyboard_digest=event.storyboard_digest,
                preflight_digest=event.preflight_digest,
                approval_digest=event.approval_digest,
                validation_report=event.validation_report,
                operation_key=event.operation_key,
            )
            .on_conflict_do_nothing(constraint="uq_storyboard_approval_event_operation")
            .returning(StoryboardApprovalEventRecord.id)
        )
        if inserted_id is None:
            existing = await self.get_approval_event_by_operation(
                storyboard_id=event.storyboard_id,
                operation_key=event.operation_key,
            )
            if existing is None:
                raise RuntimeError("approval idempotency conflict returned no record")
            return existing, False
        created = await self.session.get(StoryboardApprovalEventRecord, inserted_id)
        if created is None:
            raise RuntimeError("created approval event cannot be loaded")
        return created, True

def _source_from_record(record: ProductSourceRecord) -> ProductSource:
    return ProductSource(
        id=record.id,
        source_type=SourceType(record.source_type),
        source_url=record.source_url,
        retrieved_at=record.retrieved_at,
        content_digest=record.content_digest,
        raw_payload=record.raw_payload,
        parse_status=ParseStatus(record.parse_status),
        error_code=record.error_code,
    )


def _snapshot_from_record(record: ProductSnapshotRecord) -> ProductSnapshot:
    return ProductSnapshot(
        id=record.id,
        source_id=record.source_id,
        title=record.title,
        description=record.description,
        category_path=tuple(record.category_path),
        images=tuple(record.images),
        price_amount=record.price_amount,
        price_currency=record.price_currency,
        canonical_digest=record.canonical_digest,
        created_at=record.created_at,
    )


def _fact_from_record(record: ProductFactRecord) -> ProductFact:
    return ProductFact(
        id=record.id,
        snapshot_id=record.snapshot_id,
        claim_type=record.claim_type,
        claim=record.claim,
        value=record.value,
        evidence_kind=record.evidence_kind,
        evidence_locator=record.evidence_locator,
        evidence_excerpt=record.evidence_excerpt,
        confidence=record.confidence,
        status=FactStatus(record.status),
        updated_at=record.updated_at,
    )


def _job_from_record(record: JobRecord) -> Job:
    return Job(
        id=record.id,
        job_type=JobType(record.job_type),
        idempotency_key=record.idempotency_key,
        state=JobState(record.state),
        input_digest=record.input_digest,
        attempt_count=record.attempt_count,
        error_code=record.error_code,
        error_detail=record.error_detail,
        result_id=record.result_id,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )
