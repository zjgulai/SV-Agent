from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ProductFactRecord, ProductSnapshotRecord
from app.adapters.db.sv_agent_models import (
    SvArtifactRecord,
    SvRunRecord,
    SvRuntimeLineageLinkRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
)
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.artifact_contracts import (
    ArtifactValidationError,
    validate_artifact,
    validate_artifact_chain,
)
from app.domain.sv_agent.entities import RunState
from app.domain.sv_agent.errors import JournalIntegrityError, TaskNotFound
from app.domain.sv_agent.runtime_records import (
    ArtifactStatus,
    ArtifactType,
    EvidenceLevel,
    ProofLevel,
)

_EXPLICIT_NON_EFFECTS = (
    "does_not_write_postgresql",
    "does_not_read_filesystem_or_private_assets",
    "does_not_bind_external_evidence_packages",
    "does_not_infer_control_or_variant_versions",
    "does_not_render_or_publish",
)
_MAX_ARTIFACTS = 50
_MAX_EDGES = 200
_MAX_LINEAGE_LINKS = 100
_MAX_INPUT_REFS = 32
_MAX_SOURCE_REFS = 20
_MAX_LIMITATIONS = 50
_MAX_TEXT_LENGTH = 2_000
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9])(?:/[A-Za-z0-9._-]+){2,}")
_WINDOWS_PATH = re.compile(r"(?:\b[A-Za-z]:\\|\\\\)[^\s]+")
_URL = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
_SECRET_TEXT = re.compile(
    r"(?:\bbearer\s+[A-Za-z0-9._~+/=-]+|"
    r"\b(?:authorization|api[_-]?key|token|secret|password|credential)\b\s*[:=])",
    re.IGNORECASE,
)
_LOCALE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_TIMEZONE = re.compile(r"^[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*$")
_SUBJECT_STATES = frozenset(
    {
        "exact_snapshot",
        "reviewed_snapshot_selection",
        "reviewed_family_context",
        "unresolved",
        "conflict",
        "not_applicable",
    }
)
_SOURCE_KINDS = frozenset(
    {
        "public_url",
        "local_media",
        "reviewed_package",
        "product_truth",
        "experiment",
        "asset_bundle",
        "human_observation",
        "other",
    }
)
_ARTIFACT_REF_KEYS = frozenset(
    {
        "artifact_id",
        "artifact_type",
        "task_ref",
        "run_ref",
        "version",
        "content_digest",
    }
)
_SUBJECT_KEYS = frozenset(
    {
        "state",
        "product_snapshot_id",
        "product_snapshot_digest",
        "market",
        "locale",
        "limitations",
    }
)
_SOURCE_KEYS = frozenset({"source_ref", "source_kind", "source_digest"})
_COMMON_ENVELOPE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "artifact_type",
        "task_ref",
        "run_ref",
        "version",
        "status",
        "input_refs",
        "source_refs",
        "subject_binding",
        "content_digest",
        "evidence_level",
        "proof_level",
        "limitations",
        "created_at",
        "supersedes_artifact_id",
    }
)
_ARTIFACT_SCHEMA_VERSIONS = {
    "reference_bundle": "sv.reference-bundle.v1",
    "decomposition_map": "sv.decomposition-map.v1",
    "pattern_hypothesis": "sv.pattern-hypothesis.v1",
    "replication_plan": "sv.replication-plan.v1",
    "fact_map": "sv.fact-map.v1",
    "replication_contract": "sv.replication-contract.v1",
    "adaptation_package": "sv.adaptation-package.v1",
    "media_integrity_record": "sv.media-integrity-record.v1",
    "replication_finding": "sv.replication-finding.v1",
}
_ARTIFACT_TYPE_FIELDS = {
    "reference_bundle": frozenset(
        {
            "candidate_state",
            "captured_at",
            "observations",
            "performance_window",
            "platform",
            "playability_state",
            "reference_id",
            "rights_state",
            "source_digest",
            "source_locator",
        }
    ),
    "decomposition_map": frozenset(
        {
            "mechanism_observations",
            "primary_mechanism",
            "reference_bundle_ref",
            "secondary_mechanisms",
            "timeline",
            "unknowns",
            "unsupported_claims",
        }
    ),
    "pattern_hypothesis": frozenset(
        {
            "adaptation_constraints",
            "decomposition_map_ref",
            "evidence_scope",
            "hypothesis",
            "invariant_elements",
            "primary_mechanism",
            "prohibited_elements",
            "replaceable_elements",
            "unknowns",
        }
    ),
    "replication_plan": frozenset(
        {
            "acceptance_gates",
            "changed_dimension",
            "control_id",
            "control_reference_ref",
            "execution_budget",
            "frozen_components",
            "pattern_hypothesis_ref",
            "primary_mechanism",
            "requires_human_approval",
            "rights_state",
            "selected_component",
            "stop_conditions",
            "target_duration_seconds",
            "target_platform",
            "variant_id",
        }
    ),
    "fact_map": frozenset(
        {
            "claim_mappings",
            "claim_scope",
            "excluded_fact_ids",
            "product_snapshot_digest",
            "product_snapshot_id",
            "replication_plan_ref",
            "selected_fact_ids",
            "unsupported_claims",
        }
    ),
    "replication_contract": frozenset(
        {
            "acceptance_gates",
            "approval_ref",
            "changed_dimension",
            "claim_scope",
            "control_id",
            "decomposition_map_ref",
            "excluded_fact_ids",
            "fact_map_ref",
            "frozen_components",
            "frozen_configuration",
            "immutable",
            "primary_mechanism",
            "replication_plan_ref",
            "rights_state",
            "selected_component",
            "selected_fact_ids",
            "stop_conditions",
            "variant_id",
        }
    ),
    "adaptation_package": frozenset(
        {
            "mechanism_payload",
            "primary_mechanism",
            "replication_contract_ref",
            "selected_component",
        }
    ),
    "media_integrity_record": frozenset(
        {
            "adaptation_package_ref",
            "blockers",
            "controlled_artifact_ref",
            "disposition",
            "evidence_limits",
            "fallback_strategy",
            "gate_checks",
            "mode",
            "replication_contract_ref",
            "script_version_ref",
            "storyboard_lineage",
            "storyboard_version_ref",
            "unknowns",
        }
    ),
    "replication_finding": frozenset(
        {
            "adaptation_package_ref",
            "anomalies",
            "bounded_inferences",
            "causal_claim",
            "conclusion_scope",
            "media_integrity_record_ref",
            "next_actions",
            "observations",
            "production_acceptance",
            "replication_contract_ref",
            "unknowns",
        }
    ),
}
_REQUIRED_DIRECT_REFS = {
    "reference_bundle": (),
    "decomposition_map": (("reference_bundle_ref", "reference_bundle"),),
    "pattern_hypothesis": (("decomposition_map_ref", "decomposition_map"),),
    "replication_plan": (
        ("pattern_hypothesis_ref", "pattern_hypothesis"),
        ("control_reference_ref", "reference_bundle"),
    ),
    "fact_map": (("replication_plan_ref", "replication_plan"),),
    "replication_contract": (
        ("replication_plan_ref", "replication_plan"),
        ("fact_map_ref", "fact_map"),
        ("decomposition_map_ref", "decomposition_map"),
    ),
    "adaptation_package": (("replication_contract_ref", "replication_contract"),),
    "media_integrity_record": (
        ("replication_contract_ref", "replication_contract"),
        ("adaptation_package_ref", "adaptation_package"),
    ),
    "replication_finding": (
        ("replication_contract_ref", "replication_contract"),
        ("adaptation_package_ref", "adaptation_package"),
        ("media_integrity_record_ref", "media_integrity_record"),
    ),
}
_OPTIONAL_DIRECT_REFS = {
    "media_integrity_record": (
        ("script_version_ref", "script_version"),
        ("storyboard_version_ref", "storyboard_version"),
        ("controlled_artifact_ref", "controlled_media"),
    )
}


class WorkspaceAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    OUT_OF_SCOPE = "out_of_scope"
    QUARANTINED = "quarantined"


class EvidencePlaneKind(StrEnum):
    PRODUCT_TRUTH = "product_truth"
    PERFORMANCE = "performance"
    EXPERIMENT = "experiment"
    ASSET = "asset"


@dataclass(frozen=True, slots=True)
class EvidenceWindow:
    start: date
    end: date
    timezone: str
    basis: Literal["artifact_observation", "task_scope"]


@dataclass(frozen=True, slots=True)
class EvidenceSubject:
    state: str
    market: str | None
    locale: str | None
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    kind: str


@dataclass(frozen=True, slots=True)
class EvidenceArtifactNode:
    ref: str
    artifact_type: ArtifactType
    version: int
    status: ArtifactStatus
    evidence_level: EvidenceLevel
    proof_level: ProofLevel
    created_at: datetime
    is_conclusion: bool
    sources: tuple[EvidenceSource, ...]
    subject: EvidenceSubject
    window: EvidenceWindow | None
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceArtifactEdge:
    source_ref: str
    target_ref: str
    kind: Literal["declared_input", "runtime_verified"]
    verification_state: Literal["declared_only", "verified"]


@dataclass(frozen=True, slots=True)
class EvidenceArtifactGraph:
    state: Literal["available", "unavailable"]
    public_code: str
    nodes: tuple[EvidenceArtifactNode, ...]
    edges: tuple[EvidenceArtifactEdge, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidencePlane:
    kind: EvidencePlaneKind
    state: WorkspaceAvailability
    public_code: str
    source: str
    subject: EvidenceSubject | None
    window: EvidenceWindow | None
    proof_level: ProofLevel | None
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceComparison:
    state: Literal["unavailable"]
    public_code: Literal["COMPARISON_VERSION_REFS_UNAVAILABLE"]
    script_ref: None
    control_version_ref: None
    variant_version_ref: None
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceWorkspaceTask:
    task_id: UUID
    task_revision: int
    subject: str
    performance_start: date
    performance_end: date
    performance_timezone: str


@dataclass(frozen=True, slots=True)
class EvidenceWorkspaceRun:
    run_id: UUID
    run_revision: int
    state: RunState


@dataclass(frozen=True, slots=True)
class EvidenceArtifactWorkspaceProjection:
    schema_version: Literal["sv-evidence-artifacts/v1"]
    authority: Literal["postgresql"]
    task: EvidenceWorkspaceTask
    run: EvidenceWorkspaceRun | None
    graph: EvidenceArtifactGraph
    evidence_planes: tuple[EvidencePlane, ...]
    comparison: EvidenceComparison
    explicit_non_effects: tuple[str, ...]


class EvidenceArtifactWorkspace:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect(self, task_id: UUID) -> EvidenceArtifactWorkspaceProjection:
        task, revision = await self._load_task(task_id)
        brief = {
            "goal_track": revision.goal_track,
            "decision_question": revision.decision_question,
            "subject": revision.subject,
            "platform": revision.platform,
            "market": revision.market,
            "language": revision.language,
            "performance_window": {
                "start": revision.performance_start,
                "end": revision.performance_end,
                "timezone": revision.performance_timezone,
            },
            "stop_condition": revision.stop_condition,
            "initial_rights_state": revision.initial_rights_state,
        }
        if canonical_digest(brief) != revision.brief_digest:
            raise JournalIntegrityError("evidence_workspace_brief_digest_mismatch")
        task_projection = EvidenceWorkspaceTask(
            task_id=task.id,
            task_revision=task.current_revision,
            subject=revision.subject,
            performance_start=revision.performance_start,
            performance_end=revision.performance_end,
            performance_timezone=revision.performance_timezone,
        )
        _validate_timezone(
            revision.performance_timezone,
            code="evidence_workspace_task_window_invalid",
        )
        task_window = EvidenceWindow(
            start=revision.performance_start,
            end=revision.performance_end,
            timezone=revision.performance_timezone,
            basis="task_scope",
        )
        if task.active_run_id is None:
            return EvidenceArtifactWorkspaceProjection(
                schema_version="sv-evidence-artifacts/v1",
                authority="postgresql",
                task=task_projection,
                run=None,
                graph=EvidenceArtifactGraph(
                    state="unavailable",
                    public_code="RUN_NOT_STARTED",
                    nodes=(),
                    edges=(),
                    limitations=(
                        "No authoritative Run exists, so no artifact graph can be projected.",
                    ),
                ),
                evidence_planes=_unavailable_planes(task_window),
                comparison=_unavailable_comparison(),
                explicit_non_effects=_EXPLICIT_NON_EFFECTS,
            )
        run = await self._session.get(SvRunRecord, task.active_run_id)
        if run is None or run.task_id != task.id or run.task_revision != task.current_revision:
            raise JournalIntegrityError("evidence_workspace_active_run_scope_invalid")
        try:
            run_state = RunState(run.state)
        except ValueError as exc:
            raise JournalIntegrityError("evidence_workspace_run_state_invalid") from exc
        expected_task_revision = task.current_revision
        expected_run_revision = run.revision
        expected_active_run_id = run.id

        records = (
            await self._session.scalars(
                select(SvArtifactRecord)
                .where(
                    SvArtifactRecord.task_id == task.id,
                    SvArtifactRecord.task_revision == task.current_revision,
                    SvArtifactRecord.run_id == run.id,
                    SvArtifactRecord.run_revision <= run.revision,
                )
                .order_by(
                    SvArtifactRecord.run_revision,
                    SvArtifactRecord.created_at,
                    SvArtifactRecord.artifact_id,
                    SvArtifactRecord.version,
                )
                .limit(_MAX_ARTIFACTS + 1)
            )
        ).all()
        if len(records) > _MAX_ARTIFACTS:
            raise JournalIntegrityError("evidence_workspace_artifact_set_unbounded")

        nodes: list[EvidenceArtifactNode] = []
        internal_refs: dict[tuple[str, str, int], tuple[str, str, int]] = {}
        declared_refs: list[tuple[str, int, dict[str, Any]]] = []
        for record in records:
            node, refs, content_digest = _parse_artifact(record, task=task, run=run)
            key = (record.artifact_type, str(record.artifact_id), record.version)
            if key in internal_refs:
                raise JournalIntegrityError("evidence_workspace_artifact_duplicate")
            internal_refs[key] = (node.ref, content_digest, record.run_revision)
            nodes.append(node)
            declared_refs.extend((node.ref, record.run_revision, item) for item in refs)

        declared_edges = _resolve_declared_edges(declared_refs, internal_refs)
        _assert_acyclic(tuple(node.ref for node in nodes), declared_edges)
        if records:
            canonical_types = {item.value for item in ArtifactType}
            external_refs = tuple(
                ref
                for record in records
                for ref in record.payload.get("input_refs", ())
                if isinstance(ref, dict) and ref.get("artifact_type") not in canonical_types
            )
            try:
                validate_artifact_chain(
                    (record.payload for record in records),
                    external_refs=external_refs,
                )
            except ArtifactValidationError as exc:
                raise JournalIntegrityError("evidence_workspace_artifact_chain_invalid") from exc
        runtime_edges = await self._load_runtime_edges(task, run, records, internal_refs)
        if len(declared_edges) + len(runtime_edges) > _MAX_EDGES:
            raise JournalIntegrityError("evidence_workspace_edge_set_unbounded")
        edges = tuple(
            sorted(
                (*declared_edges, *runtime_edges),
                key=lambda item: (item.kind, item.source_ref, item.target_ref),
            )
        )
        _assert_acyclic(tuple(node.ref for node in nodes), edges)
        nodes = list(_inherit_conclusion_evidence(tuple(nodes), declared_edges))

        graph = (
            EvidenceArtifactGraph(
                state="available",
                public_code="ARTIFACT_GRAPH_AVAILABLE",
                nodes=tuple(nodes),
                edges=edges,
                limitations=(
                    "Declared artifact lineage is separate from runtime verification.",
                    "External Script, Storyboard, and media refs are not promoted into canonical graph nodes.",
                ),
            )
            if nodes
            else EvidenceArtifactGraph(
                state="unavailable",
                public_code="ARTIFACT_GRAPH_EMPTY",
                nodes=(),
                edges=(),
                limitations=("No canonical artifact is recorded for the active Run.",),
            )
        )
        evidence_planes = await self._project_evidence_planes(records, task_window)
        await self._assert_snapshot_unchanged(
            task_id=task.id,
            run_id=run.id,
            expected_task_revision=expected_task_revision,
            expected_run_revision=expected_run_revision,
            expected_active_run_id=expected_active_run_id,
        )
        return EvidenceArtifactWorkspaceProjection(
            schema_version="sv-evidence-artifacts/v1",
            authority="postgresql",
            task=task_projection,
            run=EvidenceWorkspaceRun(
                run_id=run.id,
                run_revision=run.revision,
                state=run_state,
            ),
            graph=graph,
            evidence_planes=evidence_planes,
            comparison=_unavailable_comparison(),
            explicit_non_effects=_EXPLICIT_NON_EFFECTS,
        )

    async def _project_evidence_planes(
        self,
        records: Sequence[SvArtifactRecord],
        task_window: EvidenceWindow,
    ) -> tuple[EvidencePlane, ...]:
        defaults = _unavailable_planes(task_window)
        product_truth = await self._project_product_truth(records)
        return (product_truth, *defaults[1:])

    async def _project_product_truth(self, records: Sequence[SvArtifactRecord]) -> EvidencePlane:
        all_claim_records = [
            record
            for record in records
            if record.artifact_type
            in {ArtifactType.FACT_MAP.value, ArtifactType.REPLICATION_CONTRACT.value}
        ]
        superseded_ids = {
            str(record.payload["supersedes_artifact_id"])
            for record in all_claim_records
            if _text(record.payload.get("supersedes_artifact_id"))
        }
        claim_records = [
            record
            for record in all_claim_records
            if record.status not in {ArtifactStatus.STALE.value, ArtifactStatus.SUPERSEDED.value}
            and str(record.artifact_id) not in superseded_ids
        ]
        if not claim_records:
            return _unavailable_product_truth()
        by_type: dict[str, list[SvArtifactRecord]] = {}
        for record in claim_records:
            by_type.setdefault(record.artifact_type, []).append(record)
        if any(len(candidates) != 1 for candidates in by_type.values()):
            return _quarantined_product_truth(
                "More than one current Product Truth artifact exists for the same role."
            )
        fact_map = next(
            (
                record
                for record in claim_records
                if record.artifact_type == ArtifactType.FACT_MAP.value
            ),
            None,
        )
        contract = next(
            (
                record
                for record in claim_records
                if record.artifact_type == ArtifactType.REPLICATION_CONTRACT.value
            ),
            None,
        )
        if contract is not None and (
            fact_map is None or contract.payload.get("fact_map_ref") != _record_ref(fact_map)
        ):
            return _quarantined_product_truth(
                "The current ReplicationContract does not bind the current FactMap."
            )
        scopes = {record.payload.get("claim_scope") for record in claim_records}
        if not scopes <= {"product_claims", "no_product_claims"} or len(scopes) != 1:
            return _quarantined_product_truth(
                "Product claim scope is missing or conflicts across canonical artifacts."
            )
        scope = next(iter(scopes))
        if scope == "no_product_claims":
            if any(
                record.payload.get("selected_fact_ids")
                or record.payload.get("excluded_fact_ids")
                or record.payload.get("subject_binding", {}).get("state") != "not_applicable"
                or (
                    record.artifact_type == ArtifactType.FACT_MAP.value
                    and (
                        record.payload.get("product_snapshot_id") is not None
                        or record.payload.get("product_snapshot_digest") is not None
                        or record.payload.get("claim_mappings")
                        or record.payload.get("unsupported_claims")
                    )
                )
                for record in claim_records
            ):
                return _quarantined_product_truth(
                    "A no-product-claims artifact contains Product Truth bindings."
                )
            if contract is None:
                return _unavailable_product_truth()
            return EvidencePlane(
                kind=EvidencePlaneKind.PRODUCT_TRUTH,
                state=WorkspaceAvailability.OUT_OF_SCOPE,
                public_code="PRODUCT_TRUTH_OUT_OF_SCOPE",
                source="no_product_claims",
                subject=EvidenceSubject(
                    state="not_applicable",
                    market=None,
                    locale=None,
                    limitations=("This Run declares no product claims.",),
                ),
                window=None,
                proof_level=None,
                limitations=(
                    "Product Truth is out of scope only while visible product claims remain absent.",
                ),
            )

        bindings: set[tuple[str, str]] = set()
        fact_sets: set[tuple[str, ...]] = set()
        proof_levels: list[ProofLevel] = []
        subject: EvidenceSubject | None = None
        for record in claim_records:
            raw_subject = record.payload.get("subject_binding")
            if not isinstance(raw_subject, dict) or raw_subject.get("state") != "exact_snapshot":
                return _quarantined_product_truth(
                    "Product claims are not bound to one exact Product Snapshot."
                )
            snapshot_id = raw_subject.get("product_snapshot_id")
            snapshot_digest = raw_subject.get("product_snapshot_digest")
            selected = record.payload.get("selected_fact_ids")
            if (
                not _text(snapshot_id)
                or not _digest(snapshot_digest)
                or not isinstance(selected, list)
                or not selected
                or len(selected) > 200
                or len(selected) != len(set(selected))
                or not all(_text(item) for item in selected)
            ):
                return _quarantined_product_truth(
                    "Product Snapshot or selected Fact binding is incomplete."
                )
            if record.artifact_type == ArtifactType.FACT_MAP.value and (
                record.payload.get("product_snapshot_id") != snapshot_id
                or record.payload.get("product_snapshot_digest") != snapshot_digest
            ):
                return _quarantined_product_truth(
                    "FactMap Product Snapshot fields do not match its subject binding."
                )
            bindings.add((str(snapshot_id), str(snapshot_digest)))
            fact_sets.add(tuple(selected))
            proof_levels.append(ProofLevel(record.proof_level))
            subject = _parse_subject(raw_subject)
        if contract is None:
            return _unavailable_product_truth()
        if len(bindings) != 1 or len(fact_sets) != 1 or subject is None:
            return _quarantined_product_truth(
                "Canonical claim artifacts do not share one exact Product Truth binding."
            )
        snapshot_id_text, snapshot_digest = next(iter(bindings))
        try:
            snapshot_id = UUID(snapshot_id_text)
            fact_ids = tuple(UUID(item) for item in next(iter(fact_sets)))
        except ValueError:
            return _quarantined_product_truth(
                "Product Truth refs are not authoritative PostgreSQL identities."
            )
        snapshot = await self._session.get(ProductSnapshotRecord, snapshot_id)
        if snapshot is None or snapshot.canonical_digest != snapshot_digest:
            return _quarantined_product_truth(
                "The exact Product Snapshot digest cannot be verified."
            )
        facts = (
            await self._session.scalars(
                select(ProductFactRecord)
                .where(ProductFactRecord.id.in_(fact_ids))
                .order_by(ProductFactRecord.id)
            )
        ).all()
        if (
            len(facts) != len(fact_ids)
            or {fact.id for fact in facts} != set(fact_ids)
            or any(
                fact.snapshot_id != snapshot_id or fact.status not in {"confirmed", "locked"}
                for fact in facts
            )
        ):
            return _quarantined_product_truth(
                "Selected Facts are missing, stale, or not confirmed/locked for the exact Snapshot."
            )
        proof_level = min(proof_levels, key=_proof_level_rank)
        return EvidencePlane(
            kind=EvidencePlaneKind.PRODUCT_TRUTH,
            state=WorkspaceAvailability.AVAILABLE,
            public_code="PRODUCT_TRUTH_EVIDENCE_AVAILABLE",
            source="postgresql_product_truth",
            subject=subject,
            window=None,
            proof_level=proof_level,
            limitations=("Only the exact selected confirmed/locked Facts support product claims.",),
        )

    async def _load_task(self, task_id: UUID) -> tuple[SvTaskRecord, SvTaskRevisionRecord]:
        row = (
            await self._session.execute(
                select(SvTaskRecord, SvTaskRevisionRecord)
                .join(
                    SvTaskRevisionRecord,
                    (SvTaskRevisionRecord.task_id == SvTaskRecord.id)
                    & (SvTaskRevisionRecord.revision == SvTaskRecord.current_revision),
                )
                .where(SvTaskRecord.id == task_id)
            )
        ).one_or_none()
        if row is not None:
            return row[0], row[1]
        if await self._session.get(SvTaskRecord, task_id) is None:
            raise TaskNotFound("task_not_found")
        raise JournalIntegrityError("evidence_workspace_task_revision_missing")

    async def _load_runtime_edges(
        self,
        task: SvTaskRecord,
        run: SvRunRecord,
        records: Sequence[SvArtifactRecord],
        internal_refs: dict[tuple[str, str, int], tuple[str, str, int]],
    ) -> tuple[EvidenceArtifactEdge, ...]:
        links = (
            await self._session.scalars(
                select(SvRuntimeLineageLinkRecord)
                .where(
                    SvRuntimeLineageLinkRecord.task_id == task.id,
                    SvRuntimeLineageLinkRecord.task_revision == task.current_revision,
                    SvRuntimeLineageLinkRecord.run_id == run.id,
                    SvRuntimeLineageLinkRecord.run_revision <= run.revision,
                )
                .order_by(
                    SvRuntimeLineageLinkRecord.created_at,
                    SvRuntimeLineageLinkRecord.id,
                )
                .limit(_MAX_LINEAGE_LINKS + 1)
            )
        ).all()
        if len(links) > _MAX_LINEAGE_LINKS:
            raise JournalIntegrityError("evidence_workspace_lineage_set_unbounded")
        record_digests = {
            (record.artifact_type, str(record.artifact_id), record.version): (
                canonical_digest(record.payload)
            )
            for record in records
        }
        edges: list[EvidenceArtifactEdge] = []
        seen: set[tuple[str, str]] = set()
        canonical_types = {item.value for item in ArtifactType}
        for link in links:
            if canonical_digest(link.verification_payload) != link.verification_digest:
                raise JournalIntegrityError(
                    "evidence_workspace_lineage_verification_digest_mismatch"
                )
            source_key = (
                link.source_ref_type,
                link.source_ref_id,
                link.source_version,
            )
            target_key = (
                link.target_ref_type,
                link.target_ref_id,
                link.target_version,
            )
            source = internal_refs.get(source_key)
            target = internal_refs.get(target_key)
            if link.source_ref_type in canonical_types and (
                source is None or record_digests[source_key] != link.source_digest
            ):
                raise JournalIntegrityError("evidence_workspace_runtime_lineage_source_invalid")
            if link.target_ref_type in canonical_types and (
                target is None or record_digests[target_key] != link.target_digest
            ):
                raise JournalIntegrityError("evidence_workspace_runtime_lineage_target_invalid")
            if source is None or target is None:
                continue
            if source[2] > target[2] or link.run_revision < max(source[2], target[2]):
                raise JournalIntegrityError("evidence_workspace_runtime_lineage_revision_invalid")
            pair = (source[0], target[0])
            if pair in seen:
                raise JournalIntegrityError("evidence_workspace_runtime_lineage_conflict")
            seen.add(pair)
            edges.append(
                EvidenceArtifactEdge(
                    source_ref=source[0],
                    target_ref=target[0],
                    kind="runtime_verified",
                    verification_state="verified",
                )
            )
        return tuple(edges)

    async def _assert_snapshot_unchanged(
        self,
        *,
        task_id: UUID,
        run_id: UUID,
        expected_task_revision: int,
        expected_run_revision: int,
        expected_active_run_id: UUID,
    ) -> None:
        current_task = await self._session.get(SvTaskRecord, task_id, populate_existing=True)
        current_run = await self._session.get(SvRunRecord, run_id, populate_existing=True)
        if (
            current_task is None
            or current_run is None
            or current_task.current_revision != expected_task_revision
            or current_task.active_run_id != expected_active_run_id
            or current_run.revision != expected_run_revision
            or current_run.task_revision != expected_task_revision
        ):
            raise JournalIntegrityError("evidence_workspace_snapshot_changed")


def _parse_artifact(
    record: SvArtifactRecord,
    *,
    task: SvTaskRecord,
    run: SvRunRecord,
) -> tuple[EvidenceArtifactNode, tuple[dict[str, Any], ...], str]:
    payload = record.payload
    if not isinstance(payload, dict):
        raise JournalIntegrityError("evidence_workspace_artifact_payload_invalid")
    if canonical_digest(payload) != record.payload_digest:
        raise JournalIntegrityError("evidence_workspace_artifact_digest_mismatch")
    try:
        validated_payload = validate_artifact(payload, expected_type=record.artifact_type)
    except ArtifactValidationError as exc:
        raise JournalIntegrityError("evidence_workspace_artifact_schema_invalid") from exc
    allowed_keys = _COMMON_ENVELOPE_KEYS | _ARTIFACT_TYPE_FIELDS.get(
        record.artifact_type, frozenset()
    )
    expected_schema = _ARTIFACT_SCHEMA_VERSIONS.get(record.artifact_type)
    if (
        expected_schema is None
        or payload.get("schema_version") != expected_schema
        or frozenset(payload) != allowed_keys
    ):
        raise JournalIntegrityError("evidence_workspace_artifact_envelope_invalid")
    if (
        payload.get("schema_version") != record.schema_version
        or payload.get("artifact_id") != str(record.artifact_id)
        or payload.get("artifact_type") != record.artifact_type
        or payload.get("task_ref") != str(task.id)
        or payload.get("run_ref") != str(run.id)
        or payload.get("version") != record.version
        or payload.get("status") != record.status
        or payload.get("evidence_level") != record.evidence_level
        or payload.get("proof_level") != record.proof_level
    ):
        raise JournalIntegrityError("evidence_workspace_artifact_envelope_drift")
    created_at = payload.get("created_at")
    supersedes = payload.get("supersedes_artifact_id")
    if not isinstance(created_at, str):
        raise JournalIntegrityError("evidence_workspace_artifact_envelope_invalid")
    try:
        payload_created_at = datetime.fromisoformat(created_at)
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("evidence_workspace_artifact_envelope_invalid") from exc
    if (
        payload_created_at != record.created_at
        or (
            supersedes is not None
            and (not isinstance(supersedes, str) or _IDENTIFIER.fullmatch(supersedes) is None)
        )
        or supersedes == str(record.artifact_id)
    ):
        raise JournalIntegrityError("evidence_workspace_artifact_envelope_drift")
    content_digest = str(validated_payload["content_digest"])

    raw_refs = payload.get("input_refs")
    if (
        not isinstance(raw_refs, list)
        or len(raw_refs) > _MAX_INPUT_REFS
        or raw_refs != record.input_refs
    ):
        raise JournalIntegrityError("evidence_workspace_artifact_input_refs_invalid")
    refs: list[dict[str, Any]] = []
    seen_refs: set[tuple[str, str, int]] = set()
    for raw_ref in raw_refs:
        if not isinstance(raw_ref, dict) or frozenset(raw_ref) != _ARTIFACT_REF_KEYS:
            raise JournalIntegrityError("evidence_workspace_artifact_input_ref_invalid")
        ref_type = raw_ref.get("artifact_type")
        ref_id = raw_ref.get("artifact_id")
        ref_version = raw_ref.get("version")
        if (
            not _text(ref_type)
            or not _text(ref_id)
            or not _positive_int(ref_version)
            or raw_ref.get("task_ref") != str(task.id)
            or raw_ref.get("run_ref") != str(run.id)
            or not _digest(raw_ref.get("content_digest"))
        ):
            raise JournalIntegrityError("evidence_workspace_artifact_input_ref_invalid")
        assert isinstance(ref_version, int)
        key = (str(ref_type), str(ref_id), ref_version)
        if key in seen_refs:
            raise JournalIntegrityError("evidence_workspace_artifact_input_ref_duplicate")
        seen_refs.add(key)
        refs.append(raw_ref)
    ref_values = {
        (
            str(item["task_ref"]),
            str(item["run_ref"]),
            str(item["artifact_type"]),
            str(item["artifact_id"]),
            int(item["version"]),
            str(item["content_digest"]),
        )
        for item in refs
    }
    for field, expected_type in _REQUIRED_DIRECT_REFS[record.artifact_type]:
        _validate_direct_ref(
            payload.get(field),
            expected_type=expected_type,
            input_ref_values=ref_values,
        )
    for field, expected_type in _OPTIONAL_DIRECT_REFS.get(record.artifact_type, ()):
        direct_ref = payload.get(field)
        if direct_ref is not None:
            _validate_direct_ref(
                direct_ref,
                expected_type=expected_type,
                input_ref_values=ref_values,
            )

    raw_sources = payload.get("source_refs")
    if not isinstance(raw_sources, list) or len(raw_sources) > _MAX_SOURCE_REFS:
        raise JournalIntegrityError("evidence_workspace_artifact_sources_invalid")
    sources: list[EvidenceSource] = []
    for source in raw_sources:
        if not isinstance(source, dict) or frozenset(source) != _SOURCE_KEYS:
            raise JournalIntegrityError("evidence_workspace_artifact_source_invalid")
        kind = source.get("source_kind")
        if (
            kind not in _SOURCE_KINDS
            or not _text(source.get("source_ref"))
            or (
                source.get("source_digest") is not None and not _digest(source.get("source_digest"))
            )
        ):
            raise JournalIntegrityError("evidence_workspace_artifact_source_invalid")
        sources.append(EvidenceSource(kind=kind))

    subject = _parse_subject(payload.get("subject_binding"))
    limitations = _strings(
        payload.get("limitations"),
        code="evidence_workspace_artifact_limitations_invalid",
    )
    observation_window = _parse_observation_window(payload.get("performance_window"))
    try:
        artifact_type = ArtifactType(record.artifact_type)
        status = ArtifactStatus(record.status)
        evidence_level = EvidenceLevel(record.evidence_level)
        proof_level = ProofLevel(record.proof_level)
    except ValueError as exc:
        raise JournalIntegrityError("evidence_workspace_artifact_enum_invalid") from exc
    node = EvidenceArtifactNode(
        ref=_artifact_ref(record),
        artifact_type=artifact_type,
        version=record.version,
        status=status,
        evidence_level=evidence_level,
        proof_level=proof_level,
        created_at=record.created_at,
        is_conclusion=artifact_type is ArtifactType.REPLICATION_FINDING,
        sources=tuple(sources),
        subject=subject,
        window=observation_window,
        limitations=limitations,
    )
    return node, tuple(refs), content_digest


def _resolve_declared_edges(
    declared_refs: list[tuple[str, int, dict[str, Any]]],
    internal_refs: dict[tuple[str, str, int], tuple[str, str, int]],
) -> tuple[EvidenceArtifactEdge, ...]:
    canonical_types = {item.value for item in ArtifactType}
    edges: list[EvidenceArtifactEdge] = []
    seen: set[tuple[str, str]] = set()
    for target_ref, target_revision, raw_ref in declared_refs:
        ref_type = str(raw_ref["artifact_type"])
        if ref_type not in canonical_types:
            continue
        key = (ref_type, str(raw_ref["artifact_id"]), int(raw_ref["version"]))
        resolved = internal_refs.get(key)
        if resolved is None:
            raise JournalIntegrityError("evidence_workspace_artifact_ref_missing")
        source_ref, source_digest, source_revision = resolved
        if source_digest != raw_ref["content_digest"]:
            raise JournalIntegrityError("evidence_workspace_artifact_ref_digest_mismatch")
        if source_revision > target_revision:
            raise JournalIntegrityError("evidence_workspace_artifact_ref_from_future_revision")
        pair = (source_ref, target_ref)
        if pair in seen:
            raise JournalIntegrityError("evidence_workspace_artifact_edge_duplicate")
        seen.add(pair)
        edges.append(
            EvidenceArtifactEdge(
                source_ref=source_ref,
                target_ref=target_ref,
                kind="declared_input",
                verification_state="declared_only",
            )
        )
    return tuple(edges)


def _validate_direct_ref(
    value: object,
    *,
    expected_type: str,
    input_ref_values: set[tuple[str, str, str, str, int, str]],
) -> None:
    if not isinstance(value, dict) or frozenset(value) != _ARTIFACT_REF_KEYS:
        raise JournalIntegrityError("evidence_workspace_artifact_direct_ref_invalid")
    if value.get("artifact_type") != expected_type:
        raise JournalIntegrityError("evidence_workspace_artifact_direct_ref_invalid")
    try:
        key = (
            str(value["task_ref"]),
            str(value["run_ref"]),
            str(value["artifact_type"]),
            str(value["artifact_id"]),
            int(value["version"]),
            str(value["content_digest"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise JournalIntegrityError("evidence_workspace_artifact_direct_ref_invalid") from exc
    if key not in input_ref_values:
        raise JournalIntegrityError("evidence_workspace_artifact_direct_ref_invalid")


def _assert_acyclic(nodes: tuple[str, ...], edges: tuple[EvidenceArtifactEdge, ...]) -> None:
    successors: dict[str, set[str]] = {node: set() for node in nodes}
    incoming: dict[str, int] = {node: 0 for node in nodes}
    for edge in edges:
        if edge.target_ref in successors[edge.source_ref]:
            continue
        successors[edge.source_ref].add(edge.target_ref)
        incoming[edge.target_ref] += 1
    frontier = sorted(node for node, count in incoming.items() if count == 0)
    visited = 0
    while frontier:
        node = frontier.pop(0)
        visited += 1
        for successor in sorted(successors[node]):
            incoming[successor] -= 1
            if incoming[successor] == 0:
                frontier.append(successor)
                frontier.sort()
    if visited != len(nodes):
        raise JournalIntegrityError("evidence_workspace_artifact_cycle")


def _parse_subject(value: object) -> EvidenceSubject:
    if not isinstance(value, dict) or frozenset(value) != _SUBJECT_KEYS:
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    state = value.get("state")
    snapshot_id = value.get("product_snapshot_id")
    snapshot_digest = value.get("product_snapshot_digest")
    if state not in _SUBJECT_STATES or (snapshot_id is None) != (snapshot_digest is None):
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    if snapshot_id is not None and (not _text(snapshot_id) or not _digest(snapshot_digest)):
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    if state in {"exact_snapshot", "reviewed_snapshot_selection"} and snapshot_id is None:
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    if state in {"unresolved", "conflict", "not_applicable"} and snapshot_id is not None:
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    market = value.get("market")
    locale = value.get("locale")
    if market is not None and (
        not isinstance(market, str) or re.fullmatch(r"[A-Z]{2}", market) is None
    ):
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    if locale is not None and (not isinstance(locale, str) or _LOCALE.fullmatch(locale) is None):
        raise JournalIntegrityError("evidence_workspace_artifact_subject_invalid")
    return EvidenceSubject(
        state=state,
        market=market,
        locale=locale,
        limitations=_strings(
            value.get("limitations"),
            code="evidence_workspace_artifact_subject_invalid",
        ),
    )


def _parse_observation_window(value: object) -> EvidenceWindow | None:
    if value is None:
        return None
    if not isinstance(value, dict) or frozenset(value) != {"start", "end", "timezone"}:
        raise JournalIntegrityError("evidence_workspace_artifact_window_invalid")
    try:
        start = date.fromisoformat(value["start"])
        end = date.fromisoformat(value["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise JournalIntegrityError("evidence_workspace_artifact_window_invalid") from exc
    timezone = value.get("timezone")
    if end < start or not _text(timezone):
        raise JournalIntegrityError("evidence_workspace_artifact_window_invalid")
    assert isinstance(timezone, str)
    _validate_timezone(timezone, code="evidence_workspace_artifact_window_invalid")
    return EvidenceWindow(
        start=start,
        end=end,
        timezone=str(timezone),
        basis="artifact_observation",
    )


def _artifact_ref(record: SvArtifactRecord) -> str:
    return f"artifact:{record.artifact_id}:v{record.version}"


def _record_ref(record: SvArtifactRecord) -> dict[str, object]:
    return {
        "artifact_id": str(record.artifact_id),
        "artifact_type": record.artifact_type,
        "task_ref": str(record.task_id),
        "run_ref": str(record.run_id),
        "version": record.version,
        "content_digest": record.payload.get("content_digest"),
    }


def _inherit_conclusion_evidence(
    nodes: tuple[EvidenceArtifactNode, ...],
    declared_edges: tuple[EvidenceArtifactEdge, ...],
) -> tuple[EvidenceArtifactNode, ...]:
    by_ref = {node.ref: node for node in nodes}
    predecessors: dict[str, set[str]] = {node.ref: set() for node in nodes}
    for edge in declared_edges:
        predecessors[edge.target_ref].add(edge.source_ref)

    enriched: list[EvidenceArtifactNode] = []
    for node in nodes:
        if not node.is_conclusion:
            enriched.append(node)
            continue
        frontier = list(predecessors[node.ref])
        visited: set[str] = set()
        reference_nodes: list[EvidenceArtifactNode] = []
        while frontier:
            current_ref = frontier.pop()
            if current_ref in visited:
                continue
            visited.add(current_ref)
            current = by_ref[current_ref]
            if current.artifact_type is ArtifactType.REFERENCE_BUNDLE:
                reference_nodes.append(current)
            frontier.extend(predecessors[current_ref] - visited)

        source_kinds = {source.kind for source in node.sources}
        for reference in reference_nodes:
            source_kinds.update(source.kind for source in reference.sources)
        windows = {
            (window.start, window.end, window.timezone, window.basis): window
            for window in (reference.window for reference in reference_nodes)
            if window is not None
        }
        inherited_window = next(iter(windows.values())) if len(windows) == 1 else node.window
        enriched.append(
            replace(
                node,
                sources=tuple(EvidenceSource(kind=kind) for kind in sorted(source_kinds)),
                window=inherited_window,
            )
        )
    return tuple(enriched)


def _strings(value: object, *, code: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > _MAX_LIMITATIONS:
        raise JournalIntegrityError(code)
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise JournalIntegrityError(code)
        normalized = item.strip()
        if not normalized or len(normalized) > _MAX_TEXT_LENGTH:
            raise JournalIntegrityError(code)
        _assert_safe_text(normalized, code=code)
        result.append(normalized)
    return tuple(result)


def _assert_safe_text(value: str, *, code: str) -> None:
    lowered = value.casefold()
    if (
        _ABSOLUTE_PATH.search(value)
        or _WINDOWS_PATH.search(value)
        or _URL.search(value)
        or _SECRET_TEXT.search(value)
        or "cookie:" in lowered
        or "set-cookie:" in lowered
    ):
        raise JournalIntegrityError(code)


def _validate_timezone(value: str, *, code: str) -> None:
    if len(value) > 64 or _TIMEZONE.fullmatch(value) is None:
        raise JournalIntegrityError(code)
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise JournalIntegrityError(code) from exc


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _unavailable_product_truth() -> EvidencePlane:
    return EvidencePlane(
        kind=EvidencePlaneKind.PRODUCT_TRUTH,
        state=WorkspaceAvailability.UNAVAILABLE,
        public_code="PRODUCT_TRUTH_EVIDENCE_UNAVAILABLE",
        source="not_connected",
        subject=None,
        window=None,
        proof_level=None,
        limitations=("No exact Product Truth binding is available for this Task.",),
    )


def _quarantined_product_truth(limitation: str) -> EvidencePlane:
    return EvidencePlane(
        kind=EvidencePlaneKind.PRODUCT_TRUTH,
        state=WorkspaceAvailability.QUARANTINED,
        public_code="PRODUCT_TRUTH_EVIDENCE_QUARANTINED",
        source="postgresql_product_truth",
        subject=None,
        window=None,
        proof_level=None,
        limitations=(limitation,),
    )


def _proof_level_rank(value: ProofLevel) -> int:
    return (
        ProofLevel.LOCAL,
        ProofLevel.CI,
        ProofLevel.PRIVATE,
        ProofLevel.DEPLOYMENT,
        ProofLevel.LIVE,
        ProofLevel.PRODUCTION,
    ).index(value)


def _unavailable_planes(task_window: EvidenceWindow) -> tuple[EvidencePlane, ...]:
    return (
        _unavailable_product_truth(),
        EvidencePlane(
            kind=EvidencePlaneKind.PERFORMANCE,
            state=WorkspaceAvailability.UNAVAILABLE,
            public_code="PERFORMANCE_EVIDENCE_UNAVAILABLE",
            source="not_connected",
            subject=None,
            window=task_window,
            proof_level=None,
            limitations=(
                "The Task window is declared scope, not an observed Performance package.",
            ),
        ),
        EvidencePlane(
            kind=EvidencePlaneKind.EXPERIMENT,
            state=WorkspaceAvailability.UNAVAILABLE,
            public_code="EXPERIMENT_EVIDENCE_UNAVAILABLE",
            source="not_connected",
            subject=None,
            window=None,
            proof_level=None,
            limitations=("No reviewed Experiment package is connected.",),
        ),
        EvidencePlane(
            kind=EvidencePlaneKind.ASSET,
            state=WorkspaceAvailability.UNAVAILABLE,
            public_code="ASSET_EVIDENCE_UNAVAILABLE",
            source="not_connected",
            subject=None,
            window=None,
            proof_level=None,
            limitations=("No approved Asset evidence is connected.",),
        ),
    )


def _unavailable_comparison() -> EvidenceComparison:
    return EvidenceComparison(
        state="unavailable",
        public_code="COMPARISON_VERSION_REFS_UNAVAILABLE",
        script_ref=None,
        control_version_ref=None,
        variant_version_ref=None,
        limitations=(
            "No canonical artifact declares typed immutable Control and Variant ScriptVersion roles.",
        ),
    )
