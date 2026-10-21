from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ProductFactRecord,
    ProductSnapshotRecord,
    ProductSourceRecord,
)
from app.adapters.db.sv_agent_models import (
    SvArtifactRecord,
    SvRunRecord,
    SvRuntimeLineageLinkRecord,
    SvTaskRecord,
    SvTaskRevisionRecord,
)
from app.application.sv_agent.evidence_workspace import EvidenceArtifactWorkspace
from app.domain.common.canonical import canonical_digest
from app.domain.sv_agent.artifact_contracts import bind_artifact_digest
from app.domain.sv_agent.entities import (
    GoalTrack,
    PerformanceWindow,
    RightsState,
    TargetPlatform,
    Task,
    TaskBrief,
)
from app.domain.sv_agent.errors import JournalIntegrityError

TASK_ID = UUID("41000000-0000-0000-0000-000000000001")


def _field_names(value: str) -> frozenset[str]:
    return frozenset(value.split())


_ARTIFACT_TYPE_FIELDS = {
    "reference_bundle": _field_names(
        "candidate_state captured_at observations performance_window platform "
        "playability_state reference_id rights_state source_digest source_locator"
    ),
    "decomposition_map": _field_names(
        "mechanism_observations primary_mechanism reference_bundle_ref "
        "secondary_mechanisms timeline unknowns unsupported_claims"
    ),
    "pattern_hypothesis": _field_names(
        "adaptation_constraints decomposition_map_ref evidence_scope hypothesis "
        "invariant_elements primary_mechanism prohibited_elements "
        "replaceable_elements unknowns"
    ),
    "replication_plan": _field_names(
        "acceptance_gates changed_dimension control_id control_reference_ref "
        "execution_budget frozen_components pattern_hypothesis_ref primary_mechanism "
        "requires_human_approval rights_state selected_component stop_conditions "
        "target_duration_seconds target_platform variant_id"
    ),
    "fact_map": _field_names(
        "claim_mappings claim_scope excluded_fact_ids product_snapshot_digest "
        "product_snapshot_id replication_plan_ref selected_fact_ids unsupported_claims"
    ),
    "replication_contract": _field_names(
        "acceptance_gates approval_ref changed_dimension claim_scope control_id "
        "decomposition_map_ref excluded_fact_ids fact_map_ref frozen_components "
        "frozen_configuration immutable primary_mechanism replication_plan_ref "
        "rights_state selected_component selected_fact_ids stop_conditions variant_id"
    ),
    "adaptation_package": _field_names(
        "mechanism_payload primary_mechanism replication_contract_ref selected_component"
    ),
    "media_integrity_record": _field_names(
        "adaptation_package_ref blockers controlled_artifact_ref disposition "
        "evidence_limits fallback_strategy gate_checks mode replication_contract_ref "
        "script_version_ref storyboard_lineage storyboard_version_ref unknowns"
    ),
    "replication_finding": _field_names(
        "adaptation_package_ref anomalies bounded_inferences causal_claim "
        "conclusion_scope media_integrity_record_ref next_actions observations "
        "production_acceptance replication_contract_ref unknowns"
    ),
}


def _task() -> Task:
    return Task.new(
        TaskBrief.create(
            goal_track=GoalTrack.BRAND_VOICE_SOCIAL_RESONANCE,
            decision_question="Which baby reaction mechanism should Momcozy test?",
            subject="Momcozy baby reaction story",
            platform=TargetPlatform.TIKTOK,
            market="US",
            language="en-US",
            performance_window=PerformanceWindow(
                start=date(2026, 10, 1),
                end=date(2026, 10, 20),
                timezone="America/Los_Angeles",
            ),
            stop_condition="Stop before provider execution or publication.",
            initial_rights_state=RightsState.ANALYSIS_ONLY,
        ),
        id=TASK_ID,
        created_at=datetime(2026, 10, 21, 8, 0, tzinfo=UTC),
    )


async def _persist_task(
    session: AsyncSession,
    task: Task,
    *,
    active_run: SvRunRecord | None = None,
) -> None:
    session.add(
        SvTaskRecord(
            id=task.id,
            current_revision=task.revision,
            active_run_id=active_run.id if active_run is not None else None,
            summary={"subject": task.brief.subject},
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )
    session.add(
        SvTaskRevisionRecord(
            task_id=task.id,
            revision=task.revision,
            goal_track=task.brief.goal_track.value,
            decision_question=task.brief.decision_question,
            subject=task.brief.subject,
            platform=task.brief.platform.value,
            market=task.brief.market,
            language=task.brief.language,
            performance_start=task.brief.performance_window.start,
            performance_end=task.brief.performance_window.end,
            performance_timezone=task.brief.performance_window.timezone,
            stop_condition=task.brief.stop_condition,
            initial_rights_state=task.brief.initial_rights_state.value,
            brief_digest=canonical_digest(task.brief),
            created_at=task.created_at,
        )
    )
    await session.flush()
    if active_run is not None:
        session.add(active_run)
        await session.flush()


def _placeholder_ref(
    *,
    task_id: UUID,
    run_id: UUID,
    artifact_type: str,
    index: int,
) -> dict[str, object]:
    return {
        "artifact_id": f"{artifact_type}-placeholder-{index}",
        "artifact_type": artifact_type,
        "task_ref": str(task_id),
        "run_ref": str(run_id),
        "version": 1,
        "content_digest": "d" * 64,
    }


def _artifact_defaults(
    *,
    task_id: UUID,
    run_id: UUID,
    artifact_type: str,
    input_refs: list[dict[str, object]],
    subject_state: str,
) -> dict[str, object]:
    def ref(index: int, expected_type: str) -> dict[str, object]:
        if index < len(input_refs):
            return input_refs[index]
        placeholder = _placeholder_ref(
            task_id=task_id,
            run_id=run_id,
            artifact_type=expected_type,
            index=index,
        )
        input_refs.append(placeholder)
        return placeholder

    if artifact_type == "reference_bundle":
        return {
            "reference_id": "reference-001",
            "source_locator": "https://example.test/video/001",
            "source_digest": "a" * 64,
            "platform": "tiktok",
            "performance_window": {
                "start": "2026-10-01",
                "end": "2026-10-20",
                "timezone": "America/Los_Angeles",
            },
            "captured_at": "2026-10-21T09:00:00Z",
            "rights_state": "analysis_only",
            "playability_state": "playable",
            "candidate_state": "candidate",
            "observations": [
                {
                    "observation_ref": "views-001",
                    "metric": "views",
                    "state": "observed",
                    "value": 100,
                    "unit": "count",
                    "source_refs": ["bounded-source-001"],
                }
            ],
        }
    if artifact_type == "decomposition_map":
        return {
            "reference_bundle_ref": ref(0, "reference_bundle"),
            "timeline": [
                {
                    "start_seconds": 0,
                    "end_seconds": 2.5,
                    "dimension": "hook",
                    "observation": "The opening withholds the outcome.",
                    "availability": "observed",
                    "source_refs": ["bounded-source-001"],
                }
            ],
            "primary_mechanism": "attention-grammar",
            "secondary_mechanisms": [],
            "mechanism_observations": {
                "mechanism": "attention-grammar",
                "pattern_identity": {
                    "pattern_key": "delayed-reveal",
                    "pattern_version": 1,
                },
                "observations": [
                    {
                        "component": "hook_trigger",
                        "start_seconds": 0,
                        "end_seconds": 2.5,
                        "carrier": "opening-shot",
                        "observable_function": "withhold outcome",
                        "surface_modality": "visual",
                        "surface_disposition": "replaceable",
                        "source_refs": ["bounded-source-001"],
                        "availability": "observed",
                        "shot_or_phase_anchor": "shot-01",
                    }
                ],
            },
            "unsupported_claims": [],
            "unknowns": ["Retention is not reported."],
        }
    if artifact_type == "pattern_hypothesis":
        return {
            "decomposition_map_ref": ref(0, "decomposition_map"),
            "primary_mechanism": "attention-grammar",
            "hypothesis": "A delayed reveal may improve opening attention.",
            "invariant_elements": ["withhold the opening outcome"],
            "replaceable_elements": ["setting", "performer"],
            "prohibited_elements": ["copying creator identity"],
            "adaptation_constraints": ["Preserve Product Truth boundaries."],
            "evidence_scope": ["One bounded local reference."],
            "unknowns": ["No retention curve is available."],
        }
    if artifact_type == "replication_plan":
        return {
            "pattern_hypothesis_ref": ref(0, "pattern_hypothesis"),
            "control_reference_ref": ref(1, "reference_bundle"),
            "primary_mechanism": "attention-grammar",
            "selected_component": "hook_trigger",
            "control_id": "control-001",
            "variant_id": "variant-001",
            "changed_dimension": "opening reveal timing",
            "frozen_components": [
                "reveal_cadence",
                "caption_cadence",
                "visual_contrast",
                "sonic_timing",
            ],
            "target_platform": "tiktok",
            "target_duration_seconds": 20,
            "execution_budget": {
                "max_variants": 1,
                "max_iterations": 2,
                "max_duration_seconds": 30,
                "stop_on_violation": True,
            },
            "stop_conditions": ["Stop on a contract violation."],
            "acceptance_gates": ["Human approval is required."],
            "rights_state": "analysis_only",
            "requires_human_approval": True,
        }
    if artifact_type == "fact_map":
        no_product_claims = subject_state == "not_applicable"
        return {
            "replication_plan_ref": ref(0, "replication_plan"),
            "claim_scope": "no_product_claims" if no_product_claims else "product_claims",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "claim_mappings": [],
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
            "unsupported_claims": [],
        }
    if artifact_type == "replication_contract":
        no_product_claims = subject_state == "not_applicable"
        return {
            "replication_plan_ref": ref(0, "replication_plan"),
            "fact_map_ref": ref(1, "fact_map"),
            "decomposition_map_ref": ref(2, "decomposition_map"),
            "primary_mechanism": "attention-grammar",
            "selected_component": "hook_trigger",
            "frozen_components": [
                "reveal_cadence",
                "caption_cadence",
                "visual_contrast",
                "sonic_timing",
            ],
            "claim_scope": "no_product_claims" if no_product_claims else "product_claims",
            "control_id": "control-001",
            "variant_id": "variant-001",
            "changed_dimension": "opening reveal timing",
            "frozen_configuration": {
                "language": "en-US",
                "market": "US",
                "platform": "tiktok",
                "duration_seconds": 20,
                "model": "document-only",
                "material_scope": ["target-assets-only"],
                "execution_budget": {
                    "max_variants": 1,
                    "max_iterations": 2,
                    "max_duration_seconds": 30,
                    "stop_on_violation": True,
                },
            },
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
            "stop_conditions": ["Stop on a contract violation."],
            "acceptance_gates": ["Human approval is required."],
            "rights_state": "analysis_only",
            "approval_ref": "approval-001",
            "immutable": True,
        }
    if artifact_type == "adaptation_package":
        return {
            "replication_contract_ref": ref(0, "replication_contract"),
            "primary_mechanism": "attention-grammar",
            "selected_component": "hook_trigger",
            "mechanism_payload": {
                "mechanism": "attention-grammar",
                "component": "hook_trigger",
                "hook_trigger": "Open on an unresolved caregiving moment.",
                "reveal_cadence": "Reveal after the first beat.",
                "caption_cadence": "One short caption per beat.",
                "visual_contrast": "Calm after visible friction.",
                "sonic_timing": "Use sound only as a beat marker.",
                "frozen_components": [
                    "reveal_cadence",
                    "caption_cadence",
                    "visual_contrast",
                    "sonic_timing",
                ],
                "anchors": [
                    {
                        "component": "hook_trigger",
                        "start_seconds": 0,
                        "end_seconds": 2.5,
                        "carrier": "opening-shot",
                        "observable_function": "withhold outcome",
                        "surface_class": "visual",
                        "source_ref": "bounded-source-001",
                        "availability": "observed",
                        "shot_or_phase_anchor": "shot-01",
                    }
                ],
                "pattern_identity": {
                    "pattern_key": "delayed-reveal",
                    "pattern_version": 1,
                },
                "target_surface_substitutions": ["Use target-owned surfaces."],
                "sound_policy": "functional_substitution",
            },
        }
    if artifact_type == "media_integrity_record":
        script_ref = _placeholder_ref(
            task_id=task_id,
            run_id=run_id,
            artifact_type="script_version",
            index=2,
        )
        if script_ref not in input_refs:
            input_refs.append(script_ref)
        unknown = "Rendered media is unavailable."
        return {
            "replication_contract_ref": ref(0, "replication_contract"),
            "adaptation_package_ref": ref(1, "adaptation_package"),
            "script_version_ref": script_ref,
            "storyboard_version_ref": None,
            "storyboard_lineage": None,
            "controlled_artifact_ref": None,
            "mode": "preflight",
            "gate_checks": [
                {
                    "gate": gate,
                    "state": "not_applicable_pending_artifact",
                    "findings": ["No controlled media artifact exists."],
                    "evidence_refs": [],
                    "blockers": [],
                    "unknowns": [unknown],
                    "fallback_strategy": ["Review a controlled media artifact."],
                }
                for gate in (
                    "artifact_traceability",
                    "technical_profile",
                    "communicative_surface",
                    "target_identity_continuity",
                    "source_use_scope",
                    "originality_delta",
                )
            ],
            "disposition": "proceed_with_limits",
            "fallback_strategy": ["Complete artifact review."],
            "blockers": [],
            "unknowns": [unknown],
            "evidence_limits": ["Preflight is not media acceptance."],
        }
    if artifact_type == "replication_finding":
        return {
            "replication_contract_ref": ref(0, "replication_contract"),
            "adaptation_package_ref": ref(1, "adaptation_package"),
            "media_integrity_record_ref": ref(2, "media_integrity_record"),
            "conclusion_scope": "local_fixture",
            "observations": [
                {
                    "observation_ref": "fixture-check-001",
                    "metric": "contract_conformance",
                    "state": "observed",
                    "value": True,
                    "unit": None,
                    "source_refs": ["bounded-source-001"],
                }
            ],
            "bounded_inferences": ["The package is structurally conformant."],
            "unknowns": ["No live outcome was inspected."],
            "anomalies": [],
            "next_actions": ["Complete artifact review."],
            "causal_claim": False,
            "production_acceptance": False,
        }
    raise AssertionError(f"unsupported artifact type: {artifact_type}")


def _artifact_payload(
    *,
    task_id: UUID,
    run_id: UUID,
    artifact_id: UUID,
    artifact_type: str,
    version: int,
    input_refs: list[dict[str, object]],
    subject_state: str = "not_applicable",
    source_kind: str = "human_observation",
    limitations: list[str] | None = None,
    performance_window: dict[str, str] | None = None,
    product_snapshot_id: UUID | None = None,
    product_snapshot_digest: str | None = None,
    created_at: datetime | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": f"sv.{artifact_type.replace('_', '-')}.v1",
        "artifact_id": str(artifact_id),
        "artifact_type": artifact_type,
        "task_ref": str(task_id),
        "run_ref": str(run_id),
        "version": version,
        "status": "validated",
        "input_refs": input_refs,
        "source_refs": [
            {
                "source_ref": "bounded-source-001",
                "source_kind": source_kind,
                "source_digest": "a" * 64,
            }
        ],
        "subject_binding": {
            "state": subject_state,
            "product_snapshot_id": (
                str(product_snapshot_id) if product_snapshot_id is not None else None
            ),
            "product_snapshot_digest": product_snapshot_digest,
            "market": "US" if subject_state != "not_applicable" else None,
            "locale": "en-US" if subject_state != "not_applicable" else None,
            "limitations": ["Subject scope remains bounded."],
        },
        "content_digest": "0" * 64,
        "evidence_level": "inference",
        "proof_level": "local",
        "limitations": limitations or ["Local evidence only."],
        "created_at": (created_at or datetime(2026, 10, 21, 9, 0, tzinfo=UTC))
        .isoformat()
        .replace("+00:00", "Z"),
        "supersedes_artifact_id": None,
    }
    payload.update(
        _artifact_defaults(
            task_id=task_id,
            run_id=run_id,
            artifact_type=artifact_type,
            input_refs=input_refs,
            subject_state=subject_state,
        )
    )
    if performance_window is not None:
        payload["performance_window"] = performance_window
    if extra is not None:
        payload.update(extra)
    if artifact_type == "fact_map" and payload["claim_scope"] == "product_claims":
        if not (extra is not None and "claim_mappings" in extra):
            selected = list(payload["selected_fact_ids"])
            excluded = list(payload["excluded_fact_ids"])
            payload["claim_mappings"] = [
                *[
                    {
                        "claim_id": f"bound-claim-{index}",
                        "claim_text": "Bounded confirmed claim.",
                        "disposition": "bind",
                        "fact_id": fact_id,
                        "fact_status": "confirmed",
                        "evidence_refs": [f"fact-evidence-{index}"],
                        "reason": None,
                    }
                    for index, fact_id in enumerate(selected, start=1)
                ],
                *[
                    {
                        "claim_id": f"excluded-claim-{index}",
                        "claim_text": "Excluded claim.",
                        "disposition": "exclude",
                        "fact_id": fact_id,
                        "fact_status": "unconfirmed",
                        "evidence_refs": [],
                        "reason": "The fact is not confirmed or locked.",
                    }
                    for index, fact_id in enumerate(excluded, start=1)
                ],
            ]
        payload["product_snapshot_id"] = str(product_snapshot_id)
        payload["product_snapshot_digest"] = product_snapshot_digest
    payload["content_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "content_digest"}
    )
    return payload


def _artifact_ref(payload: dict[str, object]) -> dict[str, object]:
    return {
        "artifact_id": payload["artifact_id"],
        "artifact_type": payload["artifact_type"],
        "task_ref": payload["task_ref"],
        "run_ref": payload["run_ref"],
        "version": payload["version"],
        "content_digest": payload["content_digest"],
    }


def _artifact_record(
    *,
    task_id: UUID,
    run_id: UUID,
    run_revision: int,
    payload: dict[str, object],
    created_at: datetime,
) -> SvArtifactRecord:
    return SvArtifactRecord(
        artifact_id=UUID(str(payload["artifact_id"])),
        version=int(payload["version"]),
        task_id=task_id,
        task_revision=1,
        run_id=run_id,
        run_revision=run_revision,
        artifact_type=str(payload["artifact_type"]),
        schema_version=str(payload["schema_version"]),
        status=str(payload["status"]),
        evidence_level=str(payload["evidence_level"]),
        proof_level=str(payload["proof_level"]),
        payload=payload,
        payload_digest=canonical_digest(payload),
        input_refs=list(payload["input_refs"]),
        created_at=created_at,
    )


def _fact_map_only_chain(
    *,
    task_id: UUID,
    run_id: UUID,
    created_at: datetime,
    artifact_id_seed: int,
    subject_state: str,
    product_snapshot_id: UUID | None = None,
    product_snapshot_digest: str | None = None,
    selected_fact_ids: tuple[UUID, ...] = (),
) -> tuple[dict[str, object], ...]:
    def artifact_id(offset: int) -> UUID:
        return UUID(int=artifact_id_seed + offset)

    reference = _artifact_payload(
        task_id=task_id,
        run_id=run_id,
        artifact_id=artifact_id(1),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state=subject_state,
        product_snapshot_id=product_snapshot_id,
        product_snapshot_digest=product_snapshot_digest,
        created_at=created_at,
    )
    decomposition = _artifact_payload(
        task_id=task_id,
        run_id=run_id,
        artifact_id=artifact_id(2),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(reference)],
        subject_state=subject_state,
        product_snapshot_id=product_snapshot_id,
        product_snapshot_digest=product_snapshot_digest,
        created_at=created_at,
        extra={"reference_bundle_ref": _artifact_ref(reference)},
    )
    hypothesis = _artifact_payload(
        task_id=task_id,
        run_id=run_id,
        artifact_id=artifact_id(3),
        artifact_type="pattern_hypothesis",
        version=1,
        input_refs=[_artifact_ref(decomposition)],
        subject_state=subject_state,
        product_snapshot_id=product_snapshot_id,
        product_snapshot_digest=product_snapshot_digest,
        created_at=created_at,
        extra={"decomposition_map_ref": _artifact_ref(decomposition)},
    )
    plan = _artifact_payload(
        task_id=task_id,
        run_id=run_id,
        artifact_id=artifact_id(4),
        artifact_type="replication_plan",
        version=1,
        input_refs=[_artifact_ref(hypothesis), _artifact_ref(reference)],
        subject_state=subject_state,
        product_snapshot_id=product_snapshot_id,
        product_snapshot_digest=product_snapshot_digest,
        created_at=created_at,
        extra={
            "pattern_hypothesis_ref": _artifact_ref(hypothesis),
            "control_reference_ref": _artifact_ref(reference),
        },
    )
    fact_map = _artifact_payload(
        task_id=task_id,
        run_id=run_id,
        artifact_id=artifact_id(5),
        artifact_type="fact_map",
        version=1,
        input_refs=[_artifact_ref(plan)],
        subject_state=subject_state,
        product_snapshot_id=product_snapshot_id,
        product_snapshot_digest=product_snapshot_digest,
        created_at=created_at,
        extra={
            "replication_plan_ref": _artifact_ref(plan),
            "claim_scope": (
                "no_product_claims" if subject_state == "not_applicable" else "product_claims"
            ),
            "selected_fact_ids": [str(item) for item in selected_fact_ids],
            "excluded_fact_ids": [],
        },
    )
    return reference, decomposition, hypothesis, plan, fact_map


async def test_workspace_preserves_unavailable_evidence_without_inventing_a_run(
    db_session: AsyncSession,
) -> None:
    task = _task()
    await _persist_task(db_session, task)

    projection = await EvidenceArtifactWorkspace(db_session).inspect(task.id)

    assert projection.schema_version == "sv-evidence-artifacts/v1"
    assert projection.authority == "postgresql"
    assert projection.task.task_id == task.id
    assert projection.run is None
    assert projection.graph.state == "unavailable"
    assert projection.graph.public_code == "RUN_NOT_STARTED"
    assert projection.graph.nodes == ()
    assert projection.graph.edges == ()
    assert [plane.kind for plane in projection.evidence_planes] == [
        "product_truth",
        "performance",
        "experiment",
        "asset",
    ]
    assert [plane.state for plane in projection.evidence_planes] == [
        "unavailable",
        "unavailable",
        "unavailable",
        "unavailable",
    ]
    performance = projection.evidence_planes[1]
    assert performance.window is not None
    assert performance.window.basis == "task_scope"
    assert projection.comparison.state == "unavailable"


async def test_product_claims_fact_map_without_contract_keeps_product_truth_unavailable(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000031")
    now = datetime(2026, 10, 21, 9, 31, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=5,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)

    source_id = UUID("45000000-0000-0000-0000-000000000031")
    snapshot_id = UUID("45000000-0000-0000-0000-000000000032")
    fact_id = UUID("45000000-0000-0000-0000-000000000033")
    snapshot_digest = "b" * 64
    db_session.add(
        ProductSourceRecord(
            id=source_id,
            source_type="manual",
            source_url=None,
            retrieved_at=now,
            content_digest="c" * 64,
            raw_payload={},
            parse_status="succeeded",
            error_code=None,
        )
    )
    await db_session.flush()
    db_session.add(
        ProductSnapshotRecord(
            id=snapshot_id,
            source_id=source_id,
            title="Momcozy test product",
            description=None,
            category_path=[],
            images=[],
            price_amount=None,
            price_currency=None,
            canonical_digest=snapshot_digest,
            created_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        ProductFactRecord(
            id=fact_id,
            snapshot_id=snapshot_id,
            claim_type="feature",
            claim="Bounded confirmed claim",
            value={"text": "Bounded confirmed claim"},
            evidence_kind="user_assertion",
            evidence_locator="manual-form",
            evidence_excerpt="Bounded confirmed claim",
            confidence=Decimal("1.0000"),
            status="confirmed",
            updated_at=now,
            operation_key=None,
            operation_input_digest=None,
        )
    )
    payloads = _fact_map_only_chain(
        task_id=task.id,
        run_id=run_id,
        created_at=now,
        artifact_id_seed=3100,
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        selected_fact_ids=(fact_id,),
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=revision,
                payload=payload,
                created_at=now,
            )
            for revision, payload in enumerate(payloads, start=1)
        ]
    )
    await db_session.flush()

    projection = await EvidenceArtifactWorkspace(db_session).inspect(task.id)

    product_truth = projection.evidence_planes[0]
    assert product_truth.state == "unavailable"
    assert product_truth.public_code == "PRODUCT_TRUTH_EVIDENCE_UNAVAILABLE"


async def test_no_product_claims_fact_map_without_contract_keeps_product_truth_unavailable(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000032")
    now = datetime(2026, 10, 21, 9, 32, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=5,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    payloads = _fact_map_only_chain(
        task_id=task.id,
        run_id=run_id,
        created_at=now,
        artifact_id_seed=3200,
        subject_state="not_applicable",
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=revision,
                payload=payload,
                created_at=now,
            )
            for revision, payload in enumerate(payloads, start=1)
        ]
    )
    await db_session.flush()

    projection = await EvidenceArtifactWorkspace(db_session).inspect(task.id)

    product_truth = projection.evidence_planes[0]
    assert product_truth.state == "unavailable"
    assert product_truth.public_code == "PRODUCT_TRUTH_EVIDENCE_UNAVAILABLE"


async def test_workspace_accepts_canonical_text_with_significant_boundary_whitespace(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000020")
    now = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    payload = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000020"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        limitations=["  Boundary whitespace is part of this reviewed limitation.  "],
        created_at=now,
    )
    payload = bind_artifact_digest(payload)
    db_session.add(
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=payload,
            created_at=now,
        )
    )
    await db_session.flush()

    projection = await EvidenceArtifactWorkspace(db_session).inspect(task.id)

    assert projection.graph.state == "available"
    assert projection.graph.public_code == "ARTIFACT_GRAPH_AVAILABLE"
    assert projection.graph.nodes[0].limitations == (
        "Boundary whitespace is part of this reviewed limitation.",
    )


async def test_workspace_exposes_product_truth_only_for_an_exact_eligible_binding(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000002")
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=6,
        state="running",
        primary_mechanism="proof-demonstration",
        creative_dimension="proof_device",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)

    source_id = UUID("45000000-0000-0000-0000-000000000001")
    snapshot_id = UUID("45000000-0000-0000-0000-000000000002")
    fact_id = UUID("45000000-0000-0000-0000-000000000003")
    snapshot_digest = "b" * 64
    db_session.add(
        ProductSourceRecord(
            id=source_id,
            source_type="manual",
            source_url=None,
            retrieved_at=now,
            content_digest="c" * 64,
            raw_payload={},
            parse_status="succeeded",
            error_code=None,
        )
    )
    await db_session.flush()
    db_session.add(
        ProductSnapshotRecord(
            id=snapshot_id,
            source_id=source_id,
            title="Momcozy test product",
            description=None,
            category_path=[],
            images=[],
            price_amount=None,
            price_currency=None,
            canonical_digest=snapshot_digest,
            created_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        ProductFactRecord(
            id=fact_id,
            snapshot_id=snapshot_id,
            claim_type="feature",
            claim="Bounded confirmed claim",
            value={"text": "Bounded confirmed claim"},
            evidence_kind="user_assertion",
            evidence_locator="manual-form",
            evidence_excerpt="Bounded confirmed claim",
            confidence=Decimal("1.0000"),
            status="confirmed",
            updated_at=now,
            operation_key=None,
            operation_input_digest=None,
        )
    )

    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000001"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
    )
    decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000002"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(reference)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={"reference_bundle_ref": _artifact_ref(reference)},
    )
    hypothesis = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000003"),
        artifact_type="pattern_hypothesis",
        version=1,
        input_refs=[_artifact_ref(decomposition)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={"decomposition_map_ref": _artifact_ref(decomposition)},
    )
    plan = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000004"),
        artifact_type="replication_plan",
        version=1,
        input_refs=[_artifact_ref(hypothesis), _artifact_ref(reference)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={
            "pattern_hypothesis_ref": _artifact_ref(hypothesis),
            "control_reference_ref": _artifact_ref(reference),
        },
    )
    fact_map = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000005"),
        artifact_type="fact_map",
        version=1,
        input_refs=[_artifact_ref(plan)],
        subject_state="exact_snapshot",
        source_kind="product_truth",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={
            "claim_scope": "product_claims",
            "product_snapshot_id": str(snapshot_id),
            "product_snapshot_digest": snapshot_digest,
            "selected_fact_ids": [str(fact_id)],
            "excluded_fact_ids": [],
            "replication_plan_ref": _artifact_ref(plan),
        },
    )
    contract = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000006"),
        artifact_type="replication_contract",
        version=1,
        input_refs=[
            _artifact_ref(plan),
            _artifact_ref(fact_map),
            _artifact_ref(decomposition),
        ],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={
            "replication_plan_ref": _artifact_ref(plan),
            "fact_map_ref": _artifact_ref(fact_map),
            "decomposition_map_ref": _artifact_ref(decomposition),
            "claim_scope": "product_claims",
            "selected_fact_ids": [str(fact_id)],
            "excluded_fact_ids": [],
        },
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=reference,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=decomposition,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=3,
                payload=hypothesis,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=4,
                payload=plan,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=5,
                payload=fact_map,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=6,
                payload=contract,
                created_at=now,
            ),
        ]
    )
    await db_session.flush()

    projection = await EvidenceArtifactWorkspace(db_session).inspect(task.id)

    product_truth = projection.evidence_planes[0]
    assert product_truth.kind == "product_truth"
    assert product_truth.state == "available"
    assert product_truth.public_code == "PRODUCT_TRUTH_EVIDENCE_AVAILABLE"
    assert product_truth.source == "postgresql_product_truth"
    assert product_truth.subject is not None
    assert product_truth.subject.state == "exact_snapshot"
    assert product_truth.proof_level == "local"
    assert projection.evidence_planes[1].state == "unavailable"
    assert projection.evidence_planes[2].state == "unavailable"
    assert projection.evidence_planes[3].state == "unavailable"
    assert projection.comparison.control_version_ref is None
    assert projection.comparison.variant_version_ref is None
    assert projection.explicit_non_effects == (
        "does_not_write_postgresql",
        "does_not_read_filesystem_or_private_assets",
        "does_not_bind_external_evidence_packages",
        "does_not_infer_control_or_variant_versions",
        "does_not_render_or_publish",
    )


async def test_workspace_rejects_fact_map_contract_excluded_fact_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000021")
    now = datetime(2026, 10, 21, 10, 30, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=6,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)

    snapshot_id = UUID("45000000-0000-0000-0000-000000000021")
    selected_fact_id = UUID("45000000-0000-0000-0000-000000000022")
    excluded_fact_id = UUID("45000000-0000-0000-0000-000000000023")
    snapshot_digest = "b" * 64
    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000021"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
    )
    decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000022"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(reference)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={"reference_bundle_ref": _artifact_ref(reference)},
    )
    hypothesis = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000023"),
        artifact_type="pattern_hypothesis",
        version=1,
        input_refs=[_artifact_ref(decomposition)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={"decomposition_map_ref": _artifact_ref(decomposition)},
    )
    plan = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000024"),
        artifact_type="replication_plan",
        version=1,
        input_refs=[_artifact_ref(hypothesis), _artifact_ref(reference)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={
            "pattern_hypothesis_ref": _artifact_ref(hypothesis),
            "control_reference_ref": _artifact_ref(reference),
        },
    )
    fact_map = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000025"),
        artifact_type="fact_map",
        version=1,
        input_refs=[_artifact_ref(plan)],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={
            "replication_plan_ref": _artifact_ref(plan),
            "claim_scope": "product_claims",
            "selected_fact_ids": [str(selected_fact_id)],
            "excluded_fact_ids": [str(excluded_fact_id)],
        },
    )
    contract = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("46000000-0000-0000-0000-000000000026"),
        artifact_type="replication_contract",
        version=1,
        input_refs=[
            _artifact_ref(plan),
            _artifact_ref(fact_map),
            _artifact_ref(decomposition),
        ],
        subject_state="exact_snapshot",
        product_snapshot_id=snapshot_id,
        product_snapshot_digest=snapshot_digest,
        created_at=now,
        extra={
            "replication_plan_ref": _artifact_ref(plan),
            "fact_map_ref": _artifact_ref(fact_map),
            "decomposition_map_ref": _artifact_ref(decomposition),
            "claim_scope": "product_claims",
            "selected_fact_ids": [str(selected_fact_id)],
            "excluded_fact_ids": [],
        },
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=revision,
                payload=payload,
                created_at=now,
            )
            for revision, payload in enumerate(
                (reference, decomposition, hypothesis, plan, fact_map, contract),
                start=1,
            )
        ]
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_chain_invalid",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_projects_a_bounded_cross_revision_canonical_graph(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000001")
    now = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=9,
        state="running",
        primary_mechanism="experience-pov",
        creative_dimension="experience_pov",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)

    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000001"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        source_kind="public_url",
        performance_window={
            "start": "2026-10-01",
            "end": "2026-10-20",
            "timezone": "America/Los_Angeles",
        },
    )
    decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000002"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(reference)],
        subject_state="unresolved",
        extra={"reference_bundle_ref": _artifact_ref(reference)},
    )
    hypothesis = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000003"),
        artifact_type="pattern_hypothesis",
        version=1,
        input_refs=[_artifact_ref(decomposition)],
        subject_state="unresolved",
        extra={"decomposition_map_ref": _artifact_ref(decomposition)},
    )
    plan = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000004"),
        artifact_type="replication_plan",
        version=1,
        input_refs=[_artifact_ref(hypothesis), _artifact_ref(reference)],
        subject_state="not_applicable",
        extra={
            "pattern_hypothesis_ref": _artifact_ref(hypothesis),
            "control_reference_ref": _artifact_ref(reference),
        },
    )
    fact_map = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000005"),
        artifact_type="fact_map",
        version=1,
        input_refs=[_artifact_ref(plan)],
        subject_state="not_applicable",
        extra={
            "replication_plan_ref": _artifact_ref(plan),
            "claim_scope": "no_product_claims",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
        },
    )
    contract = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000006"),
        artifact_type="replication_contract",
        version=1,
        input_refs=[
            _artifact_ref(plan),
            _artifact_ref(fact_map),
            _artifact_ref(decomposition),
        ],
        subject_state="not_applicable",
        extra={
            "replication_plan_ref": _artifact_ref(plan),
            "fact_map_ref": _artifact_ref(fact_map),
            "decomposition_map_ref": _artifact_ref(decomposition),
            "claim_scope": "no_product_claims",
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
        },
    )
    adaptation = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000007"),
        artifact_type="adaptation_package",
        version=1,
        input_refs=[_artifact_ref(contract)],
        subject_state="not_applicable",
        extra={"replication_contract_ref": _artifact_ref(contract)},
    )
    media = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000008"),
        artifact_type="media_integrity_record",
        version=1,
        input_refs=[_artifact_ref(contract), _artifact_ref(adaptation)],
        subject_state="not_applicable",
        extra={
            "replication_contract_ref": _artifact_ref(contract),
            "adaptation_package_ref": _artifact_ref(adaptation),
        },
    )
    script_ref = media["script_version_ref"]
    assert isinstance(script_ref, dict)
    storyboard_ref = _placeholder_ref(
        task_id=task.id,
        run_id=run_id,
        artifact_type="storyboard_version",
        index=3,
    )
    controlled_ref = _placeholder_ref(
        task_id=task.id,
        run_id=run_id,
        artifact_type="controlled_media",
        index=4,
    )
    media_input_refs = media["input_refs"]
    assert isinstance(media_input_refs, list)
    media_input_refs.extend((storyboard_ref, controlled_ref))
    media.update(
        {
            "storyboard_version_ref": storyboard_ref,
            "storyboard_lineage": {
                "storyboard_version_ref": storyboard_ref,
                "source_script_version_ref": script_ref,
                "evidence_scope": "declared_artifact_lineage",
            },
            "controlled_artifact_ref": controlled_ref,
            "mode": "artifact_review",
            "disposition": "ready_for_next_gate",
            "blockers": [],
            "unknowns": [],
        }
    )
    gate_checks = media["gate_checks"]
    assert isinstance(gate_checks, list)
    for check in gate_checks:
        assert isinstance(check, dict)
        check.update(
            {
                "state": "passed",
                "findings": ["The controlled artifact passed this bounded gate."],
                "evidence_refs": [f"{check['gate']}-evidence-001"],
                "blockers": [],
                "unknowns": [],
                "fallback_strategy": [],
            }
        )
    media = bind_artifact_digest(media)
    finding = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("43000000-0000-0000-0000-000000000009"),
        artifact_type="replication_finding",
        version=1,
        input_refs=[
            _artifact_ref(contract),
            _artifact_ref(adaptation),
            _artifact_ref(media),
        ],
        subject_state="not_applicable",
        limitations=["No causal or production conclusion."],
        extra={
            "replication_contract_ref": _artifact_ref(contract),
            "adaptation_package_ref": _artifact_ref(adaptation),
            "media_integrity_record_ref": _artifact_ref(media),
        },
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=reference,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=decomposition,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=3,
                payload=hypothesis,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=4,
                payload=plan,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=5,
                payload=fact_map,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=6,
                payload=contract,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=7,
                payload=adaptation,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=8,
                payload=media,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=9,
                payload=finding,
                created_at=now,
            ),
        ]
    )
    verification = {"verification": "exact-runtime-binding"}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("44000000-0000-0000-0000-000000000001"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=9,
            source_ref_type="media_integrity_record",
            source_ref_id=str(media["artifact_id"]),
            source_version=1,
            source_digest=canonical_digest(media),
            target_ref_type="replication_finding",
            target_ref_id=str(finding["artifact_id"]),
            target_version=1,
            target_digest=canonical_digest(finding),
            relation_type="derived_from",
            verifier_name="evidence-workspace-test",
            verifier_version="1.0.0",
            verification_payload=verification,
            verification_digest=canonical_digest(verification),
            created_at=now,
        )
    )
    await db_session.flush()

    projection = await EvidenceArtifactWorkspace(db_session).inspect(task.id)

    assert projection.run is not None
    assert projection.run.run_revision == 9
    assert projection.graph.state == "available"
    assert [node.artifact_type for node in projection.graph.nodes] == [
        "reference_bundle",
        "decomposition_map",
        "pattern_hypothesis",
        "replication_plan",
        "fact_map",
        "replication_contract",
        "adaptation_package",
        "media_integrity_record",
        "replication_finding",
    ]
    assert projection.graph.nodes[0].sources[0].kind == "public_url"
    assert projection.graph.nodes[0].window is not None
    assert projection.graph.nodes[0].window.basis == "artifact_observation"
    assert [node.is_conclusion for node in projection.graph.nodes] == [
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
    ]
    assert len(projection.graph.edges) == 15
    assert projection.graph.edges[-1].kind == "runtime_verified"
    assert projection.graph.edges[-1].verification_state == "verified"
    assert projection.graph.nodes[-1].limitations == ("No causal or production conclusion.",)
    assert {source.kind for source in projection.graph.nodes[-1].sources} == {
        "human_observation",
        "public_url",
    }
    assert projection.graph.nodes[-1].window == projection.graph.nodes[0].window
    assert projection.evidence_planes[0].state == "out_of_scope"
    assert projection.comparison.state == "unavailable"


async def test_workspace_rejects_unknown_fields_in_a_canonical_artifact_envelope(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000003")
    now = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    payload = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("47000000-0000-0000-0000-000000000001"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        extra={"private_reasoning": "must never be projected"},
    )
    db_session.add(
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=payload,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_schema_invalid",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_missing_type_specific_fields(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000013")
    now = datetime(2026, 10, 21, 11, 30, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    payload = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("47000000-0000-0000-0000-000000000013"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    del payload["reference_id"]
    payload["content_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "content_digest"}
    )
    db_session.add(
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=payload,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_schema_invalid",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    (
        ("dangling", "evidence_workspace_artifact_ref_missing"),
        ("digest_drift", "evidence_workspace_artifact_ref_digest_mismatch"),
    ),
)
async def test_workspace_rejects_unresolved_canonical_refs(
    db_session: AsyncSession,
    mutation: str,
    error_code: str,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000014")
    now = datetime(2026, 10, 21, 11, 45, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=2,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("47000000-0000-0000-0000-000000000014"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    unresolved_ref = _artifact_ref(reference)
    if mutation == "dangling":
        unresolved_ref["artifact_id"] = "47000000-0000-0000-0000-000000000099"
    else:
        unresolved_ref["content_digest"] = "f" * 64
    decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("47000000-0000-0000-0000-000000000015"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[unresolved_ref],
        subject_state="unresolved",
        created_at=now,
        extra={"reference_bundle_ref": unresolved_ref},
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=reference,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=decomposition,
                created_at=now,
            ),
        ]
    )
    await db_session.flush()

    with pytest.raises(JournalIntegrityError, match=error_code):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_runtime_verification_digest_drift(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000015")
    now = datetime(2026, 10, 21, 11, 50, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    verification = {"review": "bounded"}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("49000000-0000-0000-0000-000000000015"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            source_ref_type="script_version",
            source_ref_id="script-version-001",
            source_version=1,
            source_digest="a" * 64,
            target_ref_type="storyboard_version",
            target_ref_id="storyboard-version-001",
            target_version=1,
            target_digest="b" * 64,
            relation_type="derived_from",
            verifier_name="evidence-workspace-test",
            verifier_version="1.0.0",
            verification_payload=verification,
            verification_digest="c" * 64,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_lineage_verification_digest_mismatch",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_a_runtime_verified_cycle(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000019")
    now = datetime(2026, 10, 21, 11, 52, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("47000000-0000-0000-0000-000000000019"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    db_session.add(
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=reference,
            created_at=now,
        )
    )
    verification = {"review": "bounded"}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("49000000-0000-0000-0000-000000000019"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            source_ref_type="reference_bundle",
            source_ref_id=str(reference["artifact_id"]),
            source_version=1,
            source_digest=canonical_digest(reference),
            target_ref_type="reference_bundle",
            target_ref_id=str(reference["artifact_id"]),
            target_version=1,
            target_digest=canonical_digest(reference),
            relation_type="derived_from",
            verifier_name="evidence-workspace-test",
            verifier_version="1.0.0",
            verification_payload=verification,
            verification_digest=canonical_digest(verification),
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_cycle",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_fails_closed_above_the_artifact_bound(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000016")
    now = datetime(2026, 10, 21, 11, 55, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=51,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    for offset in range(1, 52):
        payload = _artifact_payload(
            task_id=task.id,
            run_id=run_id,
            artifact_id=UUID(f"50000000-0000-0000-0000-{offset:012d}"),
            artifact_type="reference_bundle",
            version=1,
            input_refs=[],
            subject_state="unresolved",
            created_at=now,
        )
        db_session.add(
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=offset,
                payload=payload,
                created_at=now,
            )
        )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_set_unbounded",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_fails_closed_above_the_runtime_lineage_bound(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000017")
    now = datetime(2026, 10, 21, 11, 57, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    verification = {"review": "bounded"}
    for offset in range(1, 102):
        db_session.add(
            SvRuntimeLineageLinkRecord(
                id=UUID(f"51000000-0000-0000-0000-{offset:012d}"),
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=1,
                source_ref_type="script_version",
                source_ref_id=f"script-version-{offset:03d}",
                source_version=1,
                source_digest="a" * 64,
                target_ref_type="storyboard_version",
                target_ref_id=f"storyboard-version-{offset:03d}",
                target_version=1,
                target_digest="b" * 64,
                relation_type="derived_from",
                verifier_name="evidence-workspace-test",
                verifier_version="1.0.0",
                verification_payload=verification,
                verification_digest=canonical_digest(verification),
                created_at=now,
            )
        )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_lineage_set_unbounded",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_fails_closed_above_the_total_edge_bound(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000018")
    now = datetime(2026, 10, 21, 11, 59, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=38,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    references: list[dict[str, object]] = []
    for offset in range(1, 32):
        payload = _artifact_payload(
            task_id=task.id,
            run_id=run_id,
            artifact_id=UUID(f"52000000-0000-0000-0000-{offset:012d}"),
            artifact_type="reference_bundle",
            version=1,
            input_refs=[],
            subject_state="unresolved",
            created_at=now,
        )
        references.append(payload)
        db_session.add(
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=offset,
                payload=payload,
                created_at=now,
            )
        )
    reference_refs = [_artifact_ref(payload) for payload in references]
    for offset in range(32, 39):
        payload = _artifact_payload(
            task_id=task.id,
            run_id=run_id,
            artifact_id=UUID(f"53000000-0000-0000-0000-{offset:012d}"),
            artifact_type="decomposition_map",
            version=1,
            input_refs=reference_refs,
            subject_state="unresolved",
            created_at=now,
            extra={"reference_bundle_ref": reference_refs[0]},
        )
        db_session.add(
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=offset,
                payload=payload,
                created_at=now,
            )
        )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_edge_set_unbounded",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_conflicting_runtime_lineage_for_one_edge(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("42000000-0000-0000-0000-000000000004")
    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=2,
        state="running",
        primary_mechanism="narrative-transformation",
        creative_dimension="narrative_arc",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("48000000-0000-0000-0000-000000000001"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("48000000-0000-0000-0000-000000000002"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(reference)],
        subject_state="unresolved",
        created_at=now,
        extra={"reference_bundle_ref": _artifact_ref(reference)},
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=reference,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=decomposition,
                created_at=now,
            ),
        ]
    )
    for offset in (1, 2):
        verification = {"review": offset}
        db_session.add(
            SvRuntimeLineageLinkRecord(
                id=UUID(f"49000000-0000-0000-0000-{offset:012d}"),
                task_id=task.id,
                task_revision=task.revision,
                run_id=run_id,
                run_revision=2,
                source_ref_type="reference_bundle",
                source_ref_id=str(reference["artifact_id"]),
                source_version=1,
                source_digest=canonical_digest(reference),
                target_ref_type="decomposition_map",
                target_ref_id=str(decomposition["artifact_id"]),
                target_version=1,
                target_digest=canonical_digest(decomposition),
                relation_type="derived_from",
                verifier_name="evidence-workspace-test",
                verifier_version="1.0.0",
                verification_payload=verification,
                verification_digest=canonical_digest(verification),
                created_at=now,
            )
        )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_runtime_lineage_conflict",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_a_semantically_invalid_canonical_artifact(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000001")
    now = datetime(2026, 10, 21, 12, 10, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    payload = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000002"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
        extra={"reference_id": "not a valid identifier"},
    )
    db_session.add(
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=payload,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_schema_invalid",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_a_direct_ref_from_another_task(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000003")
    now = datetime(2026, 10, 21, 12, 11, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=2,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000004"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    direct_ref = dict(_artifact_ref(reference))
    direct_ref["task_ref"] = "another-task"
    decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000005"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(reference)],
        subject_state="unresolved",
        created_at=now,
        extra={"reference_bundle_ref": direct_ref},
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=reference,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=decomposition,
                created_at=now,
            ),
        ]
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_(?:schema|direct_ref)_invalid",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_declared_lineage_from_a_future_revision(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000006")
    now = datetime(2026, 10, 21, 12, 12, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=2,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    future_reference = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000007"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    earlier_decomposition = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000008"),
        artifact_type="decomposition_map",
        version=1,
        input_refs=[_artifact_ref(future_reference)],
        subject_state="unresolved",
        created_at=now,
        extra={"reference_bundle_ref": _artifact_ref(future_reference)},
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=future_reference,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=earlier_decomposition,
                created_at=now,
            ),
        ]
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_artifact_ref_from_future_revision",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rejects_runtime_lineage_verified_before_its_endpoints(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000009")
    now = datetime(2026, 10, 21, 12, 13, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=2,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    source = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000010"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    target = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000011"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    db_session.add_all(
        [
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=2,
                payload=source,
                created_at=now,
            ),
            _artifact_record(
                task_id=task.id,
                run_id=run_id,
                run_revision=1,
                payload=target,
                created_at=now,
            ),
        ]
    )
    verification = {"verification": "too-early"}
    db_session.add(
        SvRuntimeLineageLinkRecord(
            id=UUID("54000000-0000-0000-0000-000000000012"),
            task_id=task.id,
            task_revision=task.revision,
            run_id=run_id,
            run_revision=1,
            source_ref_type="reference_bundle",
            source_ref_id=str(source["artifact_id"]),
            source_version=1,
            source_digest=canonical_digest(source),
            target_ref_type="reference_bundle",
            target_ref_id=str(target["artifact_id"]),
            target_version=1,
            target_digest=canonical_digest(target),
            relation_type="derived_from",
            verifier_name="evidence-workspace-test",
            verifier_version="1.0.0",
            verification_payload=verification,
            verification_digest=canonical_digest(verification),
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_runtime_lineage_revision_invalid",
    ):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_product_truth_uses_the_current_non_superseded_claim_frontier(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000013")
    now = datetime(2026, 10, 21, 12, 14, tzinfo=UTC)
    old = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000014"),
        artifact_type="fact_map",
        version=1,
        input_refs=[],
        subject_state="exact_snapshot",
        product_snapshot_id=UUID("54000000-0000-0000-0000-000000000015"),
        product_snapshot_digest="a" * 64,
        created_at=now,
        extra={
            "claim_scope": "product_claims",
            "selected_fact_ids": ["54000000-0000-0000-0000-000000000016"],
            "excluded_fact_ids": [],
        },
    )
    old["status"] = "stale"
    old["content_digest"] = canonical_digest(
        {key: value for key, value in old.items() if key != "content_digest"}
    )
    current = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000017"),
        artifact_type="fact_map",
        version=1,
        input_refs=[],
        subject_state="not_applicable",
        created_at=now,
        extra={
            "claim_scope": "no_product_claims",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
        },
    )
    contract = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000020"),
        artifact_type="replication_contract",
        version=1,
        input_refs=[_artifact_ref(current)],
        subject_state="not_applicable",
        created_at=now,
        extra={
            "fact_map_ref": _artifact_ref(current),
            "claim_scope": "no_product_claims",
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
        },
    )
    records = [
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=old,
            created_at=now,
        ),
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=2,
            payload=current,
            created_at=now,
        ),
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=3,
            payload=contract,
            created_at=now,
        ),
    ]

    plane = await EvidenceArtifactWorkspace(db_session)._project_product_truth(records)

    assert plane.state == "out_of_scope"
    assert plane.public_code == "PRODUCT_TRUTH_OUT_OF_SCOPE"


async def test_no_product_claims_cannot_hide_claim_mappings(
    db_session: AsyncSession,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000018")
    now = datetime(2026, 10, 21, 12, 15, tzinfo=UTC)
    payload = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000019"),
        artifact_type="fact_map",
        version=1,
        input_refs=[],
        subject_state="not_applicable",
        created_at=now,
        extra={
            "claim_scope": "no_product_claims",
            "product_snapshot_id": None,
            "product_snapshot_digest": None,
            "claim_mappings": [
                {
                    "claim_id": "hidden-claim",
                    "claim_text": "Hidden product claim",
                    "disposition": "unsupported",
                    "fact_id": None,
                    "fact_status": None,
                    "evidence_refs": [],
                    "reason": "Should not exist in this scope.",
                }
            ],
            "selected_fact_ids": [],
            "excluded_fact_ids": [],
            "unsupported_claims": [],
        },
    )
    record = _artifact_record(
        task_id=task.id,
        run_id=run_id,
        run_revision=1,
        payload=payload,
        created_at=now,
    )

    plane = await EvidenceArtifactWorkspace(db_session)._project_product_truth([record])

    assert plane.state == "quarantined"


@pytest.mark.parametrize(
    "mutation",
    ("unsafe_locale", "bearer_token"),
)
async def test_workspace_rejects_private_output_text(
    db_session: AsyncSession,
    mutation: str,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000020")
    now = datetime(2026, 10, 21, 12, 16, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    payload = _artifact_payload(
        task_id=task.id,
        run_id=run_id,
        artifact_id=UUID("54000000-0000-0000-0000-000000000021"),
        artifact_type="reference_bundle",
        version=1,
        input_refs=[],
        subject_state="unresolved",
        created_at=now,
    )
    if mutation == "unsafe_locale":
        subject = dict(payload["subject_binding"])
        subject["locale"] = "/Users/private/project"
        payload["subject_binding"] = subject
    else:
        payload["limitations"] = ["Authorization: Bearer private-token"]
    payload["content_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "content_digest"}
    )
    db_session.add(
        _artifact_record(
            task_id=task.id,
            run_id=run_id,
            run_revision=1,
            payload=payload,
            created_at=now,
        )
    )
    await db_session.flush()

    with pytest.raises(JournalIntegrityError, match="evidence_workspace_artifact_"):
        await EvidenceArtifactWorkspace(db_session).inspect(task.id)


async def test_workspace_rechecks_the_head_after_product_truth_queries(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _task()
    run_id = UUID("54000000-0000-0000-0000-000000000022")
    now = datetime(2026, 10, 21, 12, 17, tzinfo=UTC)
    run = SvRunRecord(
        id=run_id,
        task_id=task.id,
        task_revision=task.revision,
        revision=1,
        state="running",
        primary_mechanism="attention-grammar",
        creative_dimension="hook_trigger",
        created_at=now,
        updated_at=now,
    )
    await _persist_task(db_session, task, active_run=run)
    workspace = EvidenceArtifactWorkspace(db_session)
    original = workspace._project_evidence_planes

    async def advance_head(
        records: list[SvArtifactRecord],
        task_window: object,
    ) -> object:
        result = await original(records, task_window)  # type: ignore[arg-type]
        await db_session.execute(
            update(SvRunRecord)
            .where(SvRunRecord.id == run_id)
            .values(revision=2)
            .execution_options(synchronize_session=False)
        )
        return result

    monkeypatch.setattr(workspace, "_project_evidence_planes", advance_head)

    with pytest.raises(
        JournalIntegrityError,
        match="evidence_workspace_snapshot_changed",
    ):
        await workspace.inspect(task.id)
