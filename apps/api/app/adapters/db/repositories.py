from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ImportAttemptRecord,
    JobEventRecord,
    JobRecord,
    OutboxEventRecord,
    ProductFactRecord,
    ProductSnapshotRecord,
    ProductSourceRecord,
    ScriptGenerationRecord,
    ScriptVersionRecord,
    StoryboardApprovalEventRecord,
    StoryboardVersionRecord,
)
from app.domain.common.canonical import canonical_digest
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
                operation_key=fact.operation_key,
                operation_input_digest=fact.operation_input_digest,
            )
        )
        await self.session.flush()
        return fact

    async def add_fact_idempotent(self, fact: ProductFact) -> tuple[ProductFact, bool]:
        if fact.operation_key is None or fact.operation_input_digest is None:
            raise ValueError("idempotent fact creation requires operation metadata")
        inserted_id = await self.session.scalar(
            insert(ProductFactRecord)
            .values(
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
                operation_key=fact.operation_key,
                operation_input_digest=fact.operation_input_digest,
            )
            .on_conflict_do_nothing(
                index_elements=[ProductFactRecord.snapshot_id, ProductFactRecord.operation_key],
                index_where=ProductFactRecord.operation_key.is_not(None),
            )
            .returning(ProductFactRecord.id)
        )
        if inserted_id is not None:
            return fact, True
        record = await self.session.scalar(
            select(ProductFactRecord).where(
                ProductFactRecord.snapshot_id == fact.snapshot_id,
                ProductFactRecord.operation_key == fact.operation_key,
            )
        )
        if record is None:
            raise RuntimeError("fact idempotency conflict returned no fact")
        return _fact_from_record(record), False

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

    async def list_facts_at_observation(
        self, snapshot_id: UUID, *, for_update: bool = False
    ) -> tuple[Sequence[ProductFact], datetime]:
        statement = (
            select(ProductFactRecord, func.statement_timestamp())
            .where(ProductFactRecord.snapshot_id == snapshot_id)
            .order_by(ProductFactRecord.updated_at, ProductFactRecord.id)
        )
        if for_update:
            statement = statement.with_for_update(of=ProductFactRecord)
        rows = (await self.session.execute(statement)).all()
        if not rows:
            observed_at = await self.session.scalar(select(func.statement_timestamp()))
            if observed_at is None:
                raise RuntimeError("PostgreSQL did not return statement_timestamp")
            return [], observed_at
        observed_at = rows[0][1]
        return [_fact_from_record(row[0]) for row in rows], observed_at

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
        from_state = JobState(record.state)
        state_changed = record.state != job.state.value
        attempt_changed = record.attempt_count != job.attempt_count
        error_changed = (
            record.error_code != job.error_code or record.error_detail != job.error_detail
        )
        if not (state_changed or attempt_changed or error_changed):
            return job
        record.state = job.state.value
        record.attempt_count = job.attempt_count
        record.error_code = job.error_code
        record.error_detail = job.error_detail
        record.result_id = job.result_id
        record.started_at = job.started_at
        record.finished_at = job.finished_at
        await self.append_event(
            job,
            event_type="state_transition" if state_changed else "execution_reclaimed",
            from_state=from_state,
        )
        await self.session.flush()
        return job

    async def append_event(
        self,
        job: Job,
        *,
        event_type: str,
        from_state: JobState | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> JobEventRecord:
        event = JobEventRecord(
            id=uuid4(),
            job_id=job.id,
            event_type=event_type,
            from_state=from_state.value if from_state is not None else None,
            to_state=job.state.value,
            attempt_count=job.attempt_count,
            error_code=error_code if error_code is not None else job.error_code,
            error_detail=(error_detail if error_detail is not None else job.error_detail),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(self, job_id: UUID) -> Sequence[JobEventRecord]:
        return (
            await self.session.scalars(
                select(JobEventRecord)
                .where(JobEventRecord.job_id == job_id)
                .order_by(JobEventRecord.event_sequence)
            )
        ).all()


class OutboxRepository:
    EVENT_TYPE = "job.dispatch.v1"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_dispatch(self, job: Job, *, task_name: str) -> OutboxEventRecord:
        now = await self._database_now()
        payload = {
            "contract_version": "1.0",
            "job_id": str(job.id),
            "job_type": job.job_type.value,
            "task_name": task_name,
        }
        record = OutboxEventRecord(
            id=uuid4(),
            event_type=self.EVENT_TYPE,
            job_id=job.id,
            task_name=task_name,
            payload=payload,
            payload_digest=canonical_digest(payload),
            delivery_state="pending",
            delivery_attempt_count=0,
            delivery_cycle_started_at=now,
            manual_retry_count=0,
            available_at=now,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_job_id(
        self, job_id: UUID, *, for_update: bool = False
    ) -> OutboxEventRecord | None:
        statement = select(OutboxEventRecord).where(OutboxEventRecord.job_id == job_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def _database_now(self) -> datetime:
        now = await self.session.scalar(select(func.statement_timestamp()))
        if now is None:
            raise RuntimeError("PostgreSQL did not return statement_timestamp")
        return now

    async def dead_letter_due(
        self,
        *,
        max_delivery_attempts: int,
        max_delivery_age_seconds: int,
        job_id: UUID | None = None,
    ) -> OutboxEventRecord | None:
        now = await self._database_now()
        expired_cycle = OutboxEventRecord.delivery_cycle_started_at <= now - timedelta(
            seconds=max_delivery_age_seconds
        )
        eligible_delivery = or_(
            OutboxEventRecord.delivery_state == "pending",
            and_(
                OutboxEventRecord.delivery_state == "leased",
                OutboxEventRecord.lease_expires_at <= now,
            ),
        )
        exhausted = or_(
            OutboxEventRecord.delivery_attempt_count >= max_delivery_attempts,
            expired_cycle,
        )
        conditions = [eligible_delivery, exhausted, JobRecord.state == JobState.QUEUED.value]
        if job_id is not None:
            conditions.append(OutboxEventRecord.job_id == job_id)
        record = await self.session.scalar(
            select(OutboxEventRecord)
            .join(JobRecord, JobRecord.id == OutboxEventRecord.job_id)
            .where(*conditions)
            .order_by(OutboxEventRecord.delivery_cycle_started_at, OutboxEventRecord.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if record is None:
            return None
        record.delivery_state = "dead"
        record.lease_token = None
        record.lease_expires_at = None
        record.available_at = now
        record.dead_letter_code = (
            "OUTBOX_MAX_DELIVERY_ATTEMPTS"
            if record.delivery_attempt_count >= max_delivery_attempts
            else "OUTBOX_MAX_DELIVERY_AGE"
        )
        record.dead_lettered_at = now
        record.last_error_code = record.dead_letter_code
        record.last_error_detail = "Task broker delivery requires operator recovery."
        await self.session.flush()
        return record

    async def claim_due(
        self, *, lease_seconds: int, job_id: UUID | None = None
    ) -> OutboxEventRecord | None:
        now = await self._database_now()
        conditions = [
            or_(
                and_(
                    OutboxEventRecord.delivery_state == "pending",
                    OutboxEventRecord.available_at <= now,
                ),
                and_(
                    OutboxEventRecord.delivery_state == "leased",
                    OutboxEventRecord.lease_expires_at <= now,
                ),
            )
        ]
        if job_id is not None:
            conditions.append(OutboxEventRecord.job_id == job_id)
        record = await self.session.scalar(
            select(OutboxEventRecord)
            .join(JobRecord, JobRecord.id == OutboxEventRecord.job_id)
            .where(*conditions)
            .where(JobRecord.state == JobState.QUEUED.value)
            .order_by(OutboxEventRecord.available_at, OutboxEventRecord.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if record is None:
            return None
        record.delivery_state = "leased"
        record.delivery_attempt_count += 1
        record.lease_token = uuid4()
        record.lease_expires_at = now + timedelta(seconds=lease_seconds)
        record.dead_letter_code = None
        record.dead_lettered_at = None
        record.last_error_code = None
        record.last_error_detail = None
        await self.session.flush()
        return record

    async def mark_published(self, *, event_id: UUID, lease_token: UUID) -> bool:
        now = await self._database_now()
        published_id = await self.session.scalar(
            update(OutboxEventRecord)
            .where(
                OutboxEventRecord.id == event_id,
                OutboxEventRecord.delivery_state == "leased",
                OutboxEventRecord.lease_token == lease_token,
                OutboxEventRecord.lease_expires_at > now,
            )
            .values(
                delivery_state="published",
                published_at=now,
                lease_token=None,
                lease_expires_at=None,
            )
            .returning(OutboxEventRecord.id)
        )
        return published_id is not None

    async def release(
        self,
        *,
        event_id: UUID,
        lease_token: UUID,
        error_code: str,
        error_detail: str,
        backoff_seconds: int,
    ) -> bool:
        now = await self._database_now()
        released_id = await self.session.scalar(
            update(OutboxEventRecord)
            .where(
                OutboxEventRecord.id == event_id,
                OutboxEventRecord.delivery_state == "leased",
                OutboxEventRecord.lease_token == lease_token,
            )
            .values(
                delivery_state="pending",
                available_at=now + timedelta(seconds=backoff_seconds),
                lease_token=None,
                lease_expires_at=None,
                last_error_code=error_code,
                last_error_detail=error_detail[:500],
            )
            .returning(OutboxEventRecord.id)
        )
        return released_id is not None

    async def retry_dead(self, *, job_id: UUID) -> OutboxEventRecord | None:
        now = await self._database_now()
        record = await self.session.scalar(
            select(OutboxEventRecord)
            .join(JobRecord, JobRecord.id == OutboxEventRecord.job_id)
            .where(
                OutboxEventRecord.job_id == job_id,
                OutboxEventRecord.delivery_state == "dead",
                JobRecord.state == JobState.QUEUED.value,
            )
            .with_for_update()
        )
        if record is None:
            return None
        record.delivery_state = "pending"
        record.delivery_attempt_count = 0
        record.delivery_cycle_started_at = now
        record.manual_retry_count += 1
        record.last_manual_retry_at = now
        record.available_at = now
        record.lease_token = None
        record.lease_expires_at = None
        record.dead_letter_code = None
        record.dead_lettered_at = None
        record.last_error_code = None
        record.last_error_detail = None
        await self.session.flush()
        return record


class ImportAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        job_id: UUID,
        source_id: UUID,
        attempt_token: int,
        stage: str,
        source_url_digest: str,
        resolution_digest: str | None = None,
        response_digest: str | None = None,
        snapshot_id: UUID | None = None,
        error_code: str | None = None,
    ) -> ImportAttemptRecord:
        record = ImportAttemptRecord(
            id=uuid4(),
            job_id=job_id,
            source_id=source_id,
            attempt_token=attempt_token,
            stage=stage,
            source_url_digest=source_url_digest,
            resolution_digest=resolution_digest,
            response_digest=response_digest,
            snapshot_id=snapshot_id,
            error_code=error_code,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_by_job_id(self, job_id: UUID) -> Sequence[ImportAttemptRecord]:
        return (
            await self.session.scalars(
                select(ImportAttemptRecord)
                .where(ImportAttemptRecord.job_id == job_id)
                .order_by(ImportAttemptRecord.attempt_sequence)
            )
        ).all()


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

    async def get_version_by_operation(
        self, *, parent_version_id: UUID, operation_key: str
    ) -> ScriptVersionRecord | None:
        return await self.session.scalar(
            select(ScriptVersionRecord).where(
                ScriptVersionRecord.parent_version_id == parent_version_id,
                ScriptVersionRecord.operation_key == operation_key,
            )
        )

    async def insert_fact_rebind_version(
        self, version: ScriptVersionRecord
    ) -> tuple[ScriptVersionRecord, bool]:
        inserted_id = await self.session.scalar(
            insert(ScriptVersionRecord)
            .values(
                id=version.id,
                generation_id=version.generation_id,
                parent_version_id=version.parent_version_id,
                draft=version.draft,
                validation_report=version.validation_report,
                revision_kind=version.revision_kind,
                actor_kind=version.actor_kind,
                reason_code=version.reason_code,
                operation_key=version.operation_key,
                operation_input_digest=version.operation_input_digest,
            )
            .on_conflict_do_nothing(constraint="uq_script_versions_parent_operation")
            .returning(ScriptVersionRecord.id)
        )
        if inserted_id is None:
            if version.parent_version_id is None or version.operation_key is None:
                raise RuntimeError("fact rebind requires parent and operation key")
            existing = await self.get_version_by_operation(
                parent_version_id=version.parent_version_id,
                operation_key=version.operation_key,
            )
            if existing is None:
                raise RuntimeError("script version conflict returned no record")
            return existing, False
        created = await self.get_version(inserted_id)
        if created is None:
            raise RuntimeError("created script version cannot be loaded")
        return created, True

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
        operation_key=record.operation_key,
        operation_input_digest=record.operation_input_digest,
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
