#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
for _ in range(12):
    if (SCRIPT_DIR / "tools").is_file() or (SCRIPT_DIR / "tools").is_dir():
        break
    if (SCRIPT_DIR.parent == SCRIPT_DIR):
        break
    SCRIPT_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SCRIPT_DIR if (SCRIPT_DIR / "tools").is_dir() else Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.oumomo_experiments.contracts import ExperimentRecord, validate_record


REQUIRED_MANIFEST_FIELDS = {
    "confidence",
    "experiment_id",
    "feature",
    "submit_count",
    "verdict",
}
REQUIRED_HASH_COLUMNS = {
    "experiment_id",
    "artifact_path",
    "sha256",
    "bytes",
    "mime",
}
REQUIRED_SCORECARD_COLUMNS = {
    "experiment_id",
}
FORBIDDEN_FIELDS = {
    "authorization",
    "cookie",
    "headers",
    "password",
    "phone",
    "raw_job_id",
    "signed_url",
    "token",
}
JOB_HASH = re.compile(r"[0-9a-f]{64}")
ISO8601 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _forbidden_fields(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.casefold()
            if normalized == "job_id" or normalized in FORBIDDEN_FIELDS:
                found.append(key)
            found.extend(_forbidden_fields(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_forbidden_fields(child))
    return found


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return records, [f"missing file: {path}"]
    for line_number, raw_line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError:
            errors.append(f"{path.name} line {line_number}: invalid JSON")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.name} line {line_number}: record must be an object")
            continue
        records.append(value)
    return records, errors


def _read_csv(path: Path, required_fields: set[str]) -> tuple[list[dict[str, str]], list[str]]:
    if not path.is_file():
        return [], [f"missing file: {path}"]
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        for row_number, row in enumerate(reader, start=2):
            for field in required_fields:
                if field not in row:
                    errors.append(f"{path.name} row {row_number}: missing column {field}")
            rows.append(row)
    return rows, errors


def _as_int(value: str | int | None, context: str, errors: list[str]) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        errors.append(f"{context}: invalid integer")
        return None


def _is_iso8601(value: object) -> bool:
    return isinstance(value, str) and ISO8601.fullmatch(value) is not None


def _validate_stage_timestamps(
    experiment_id: str,
    states: list[str] | None,
    timestamps: list[dict[str, Any]] | None,
    errors: list[str],
) -> None:
    if timestamps is None and (states or states is not None):
        errors.append(f"{experiment_id}: stage_timestamps missing while state_sequence exists")
        return
    if timestamps is None:
        return
    if states is None:
        errors.append(f"{experiment_id}: state_sequence missing while stage_timestamps exists")
        return
    if not isinstance(timestamps, list):
        errors.append(f"{experiment_id}: stage_timestamps must be a list")
        return
    if len(timestamps) != len(states):
        errors.append(
            f"{experiment_id}: stage_timestamps length must match state_sequence length"
        )
        return
    ordered = []
    for item_index, item in enumerate(timestamps):
        if not isinstance(item, dict):
            errors.append(
                f"{experiment_id}: stage_timestamps[{item_index}] must be an object"
            )
            continue
        state = item.get("state")
        observed_at = item.get("observed_at")
        if not isinstance(state, str) or state not in states:
            errors.append(
                f"{experiment_id}: stage_timestamps[{item_index}] state must match state_sequence"
            )
            continue
        if not _is_iso8601(observed_at):
            errors.append(
                f"{experiment_id}: stage_timestamps[{item_index}] observed_at must be ISO8601 UTC"
            )
        ordered.append(state)
    if ordered != states:
        errors.append(
            f"{experiment_id}: stage_timestamps order must align with state_sequence"
        )


def validate(
    root: Path,
    *,
    max_spend: int = 980,
    strict_protocol_requirements: bool = True,
) -> list[str]:
    experiments = root / "experiments"
    manifest_rows, errors = _read_jsonl(experiments / "experiment-manifest.jsonl")
    if not manifest_rows and not errors:
        errors.append("manifest empty")
    manifest_by_id: dict[str, ExperimentRecord] = {}
    protocol_v2_ids: set[str] = set()
    paid_manifest_ids: set[str] = set()
    seen_manifest: set[str] = set()

    for row in manifest_rows:
        experiment_id = str(row.get("experiment_id", "<missing>"))
        for field in sorted(REQUIRED_MANIFEST_FIELDS - set(row)):
            if row.get("submit_count", 0) == 0 and field == "quote_before_submit":
                continue
            errors.append(f"{experiment_id}: missing required field: {field}")

        try:
            record = ExperimentRecord.from_mapping(row)
        except TypeError as exc:
            errors.append(f"{experiment_id}: {exc}")
            continue

        if experiment_id in seen_manifest:
            errors.append(f"{experiment_id}: duplicate manifest record")
        seen_manifest.add(experiment_id)

        manifest_by_id[experiment_id] = record
        if isinstance(record.submit_count, int) and record.submit_count > 0:
            paid_manifest_ids.add(experiment_id)
        forbidden_fields = _forbidden_fields(row)
        for field in forbidden_fields:
            if field not in errors:
                errors.append(f"{experiment_id}: forbidden field: {field}")
        errors.extend(
            f"{experiment_id}: {error}"
            for error in validate_record(
                record,
                strict_protocol_requirements=strict_protocol_requirements,
            )
        )

        if record.protocol_version == "v2":
            _validate_stage_timestamps(
                experiment_id,
                record.state_sequence,
                record.stage_timestamps,
                errors,
            )

    if (
        (experiments / "credit-ledger.csv").is_file()
        is False
        and paid_manifest_ids
    ):
        errors.append("ledger missing")

    hashes_rows, hash_errors = _read_csv(
        root / "artifacts" / "hashes.csv",
        REQUIRED_HASH_COLUMNS,
    )
    errors.extend(hash_errors)
    hashes_by_sha: dict[str, dict[str, str]] = {
        row["sha256"]: row for row in hashes_rows if row.get("sha256")
    }
    scorecards_rows, score_errors = _read_csv(
        root / "artifacts" / "scorecards.csv",
        REQUIRED_SCORECARD_COLUMNS,
    )
    errors.extend(score_errors)
    scorecards_by_experiment: set[str] = {
        row["experiment_id"] for row in scorecards_rows if row.get("experiment_id")
    }

    job_events_rows, event_errors = _read_jsonl(experiments / "job-state-events.jsonl")
    errors.extend(f"job-events: {error}" for error in event_errors)
    job_events_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(job_events_rows, start=1):
        experiment_id = str(row.get("experiment_id", f"__missing__{index}"))
        for field in _forbidden_fields(row):
            errors.append(f"job-events {experiment_id}: forbidden field: {field}")
        if not row.get("experiment_id"):
            errors.append(f"job-events {experiment_id}: missing experiment_id")
            continue
        if not JOB_HASH.fullmatch(row.get("job_id_hash", "")):
            errors.append(
                f"job-events {experiment_id}: invalid or missing job_id_hash"
            )
        job_state_sequence = row.get("state_sequence")
        if not isinstance(job_state_sequence, list) or not job_state_sequence:
            errors.append(f"job-events {experiment_id}: state_sequence must be a non-empty list")
        terminal_state = row.get("terminal_state")
        if terminal_state is not None and not isinstance(terminal_state, str):
            errors.append(f"job-events {experiment_id}: terminal_state must be a string")
        if experiment_id in job_events_by_id:
            errors.append(f"{experiment_id}: duplicate job-state-events record")
        job_events_by_id[experiment_id] = row

    ledger_rows, ledger_errors = _read_csv(
        experiments / "credit-ledger.csv",
        {"experiment_id", "observed_at", "feature", "quote", "credit_before", "credit_after", "delta", "terminal_state", "notes"},
    )
    errors.extend(ledger_errors)

    spend = 0
    seen_ledger_rows: set[str] = set()
    previous_after: int | None = None
    ledger_ids: set[str] = set()
    if ledger_rows:
        for row_number, row in enumerate(ledger_rows, start=2):
            experiment_id = row.get("experiment_id", "<missing>")
            if experiment_id in seen_ledger_rows:
                errors.append(f"{experiment_id}: duplicate ledger row")
            seen_ledger_rows.add(experiment_id)
            ledger_ids.add(experiment_id)

            before = _as_int(row.get("credit_before"), f"{experiment_id} credit_before", errors)
            after = _as_int(row.get("credit_after"), f"{experiment_id} credit_after", errors)
            delta = _as_int(row.get("delta"), f"{experiment_id} delta", errors)
            if before is None or after is None or delta is None:
                continue
            if before + delta != after:
                errors.append(f"{experiment_id}: credit arithmetic mismatch")
            if previous_after is not None and before != previous_after:
                errors.append(f"{experiment_id}: ledger continuity mismatch")
            previous_after = after
            if delta < 0:
                spend += -delta

            manifest = manifest_by_id.get(experiment_id)
            if manifest is None:
                continue
            if manifest.ledger_delta is not None and manifest.ledger_delta != delta:
                errors.append(f"{experiment_id}: manifest/ledger delta mismatch")
            if manifest.submit_count > 0 and not _is_iso8601(row.get("observed_at")):
                errors.append(f"{experiment_id}: ledger observed_at must be ISO8601 UTC")

        if spend > max_spend:
            errors.append(f"budget exceeded: {spend} > {max_spend}")
        for experiment_id in paid_manifest_ids - ledger_ids:
            errors.append(f"{experiment_id}: paid manifest record missing ledger row")

    for experiment_id, record in manifest_by_id.items():
        submit_count = record.submit_count
        if not isinstance(submit_count, int) or submit_count < 0:
            continue
        if submit_count > 0 and experiment_id not in paid_manifest_ids:
            continue

        if experiment_id in paid_manifest_ids:
            if experiment_id not in job_events_by_id:
                errors.append(f"{experiment_id}: missing job state event")
            else:
                job_event = job_events_by_id[experiment_id]
                manifest_state = record.terminal_state
                event_state = job_event.get("terminal_state")
                if manifest_state is not None and manifest_state != event_state:
                    errors.append(
                        f"{experiment_id}: manifest terminal_state and job-events terminal_state mismatch"
                    )
                if record.job_id_hash is not None and record.job_id_hash != job_event.get(
                    "job_id_hash"
                ):
                    errors.append(
                        f"{experiment_id}: manifest job_id_hash mismatch with job-events"
                    )
                if record.state_sequence:
                    event_sequence = job_event.get("state_sequence")
                    if event_sequence != record.state_sequence:
                        if not isinstance(event_sequence, list):
                            errors.append(
                                f"{experiment_id}: job-events state_sequence must be list"
                            )
                        else:
                            prefix = record.state_sequence[: len(event_sequence)]
                            if event_sequence != record.state_sequence and event_sequence != prefix:
                                errors.append(
                                    f"{experiment_id}: job-events state_sequence diverges from manifest"
                                )

        if record.protocol_version == "v2":
            artifact_sha = (
                record.extra_fields.get("artifact_sha256")
                or record.artifacts.get("artifact_sha256")
                if isinstance(record.artifacts, dict)
                else None
            )
            if record.terminal_state == "succeeded" and not artifact_sha:
                errors.append(f"{experiment_id}: v2 terminal success requires artifact_sha256")
            if artifact_sha is not None and artifact_sha not in hashes_by_sha:
                errors.append(f"{experiment_id}: artifact_sha256 not found in hashes.csv")

            if record.control_experiment_id and record.control_experiment_id not in manifest_by_id:
                errors.append(f"{experiment_id}: control_experiment_id not found in manifest")
            scorecard_id = (
                record.scorecard_id
                or record.extra_fields.get("scorecard_id")
                or record.extra_fields.get("scorecard_ref")
                or record.extra_fields.get("scorecard")
            )
            if scorecard_id and scorecard_id not in scorecards_by_experiment:
                errors.append(f"{experiment_id}: scorecard_id not found in scorecards.csv")

        if record.terminal_state == "failed" and not record.extra_fields.get("notes"):
            errors.append(f"{experiment_id}: failed records should include notes")

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--max-spend", type=int, default=980)
    parser.add_argument(
        "--allow-legacy-protocol",
        action="store_true",
        help="Allow V2 field usage without protocol_version for historical exports.",
    )
    arguments = parser.parse_args()
    errors = validate(
        arguments.root,
        max_spend=arguments.max_spend,
        strict_protocol_requirements=not arguments.allow_legacy_protocol,
    )
    if errors:
        for error in errors:
            print(error)
        return 1
    print("evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
