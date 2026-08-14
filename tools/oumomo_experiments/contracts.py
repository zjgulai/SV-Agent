from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

_HEX_64 = re.compile(r"[0-9a-f]{64}")
_KNOWN_FIELDS = {
    "experiment_id",
    "feature",
    "verdict",
    "confidence",
    "submit_count",
    "quote_before_submit",
    "credit_before",
    "credit_after",
    "ledger_delta",
    "job_id_hash",
    "protocol_version",
    "study_id",
    "observed_at",
    "control_experiment_id",
    "single_changed_variable",
    "config_digest",
    "config_canonical_json",
    "state_sequence",
    "terminal_state",
    "stage_timestamps",
    "artifacts",
    "scorecard_id",
}

_FORBIDDEN_FIELDS = {
    "authorization",
    "cookie",
    "headers",
    "password",
    "phone",
    "raw_job_id",
    "signed_url",
    "token",
}

_CONFIDENCE_VALUES = {"F", "I-H", "I-M", "U", "Vendor claim"}
_VERDICT_VALUES = {"blocked", "fail", "inconclusive", "pass"}
_ALLOWED_PROTOCOLS = {None, "v1", "v2"}
_V2_REQUIRED = {
    "protocol_version",
    "observed_at",
    "single_changed_variable",
    "state_sequence",
    "terminal_state",
}


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    feature: str
    verdict: str
    confidence: str
    submit_count: int = 0
    quote_before_submit: int | None = None
    credit_before: int | None = None
    credit_after: int | None = None
    ledger_delta: int | None = None
    job_id_hash: str | None = None
    protocol_version: str | None = None
    study_id: str | None = None
    observed_at: str | None = None
    control_experiment_id: str | None = None
    single_changed_variable: str | None = None
    config_digest: str | None = None
    config_canonical_json: Any | None = None
    state_sequence: list[str] | None = None
    terminal_state: str | None = None
    stage_timestamps: list[dict[str, Any]] | None = None
    artifacts: dict[str, Any] | None = None
    scorecard_id: str | None = None
    extra_fields: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ExperimentRecord:
        fields = dict(value)
        known = {key: fields.pop(key) for key in tuple(fields) if key in _KNOWN_FIELDS}
        return cls(**known, extra_fields=fields)

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "feature": self.feature,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "submit_count": self.submit_count,
        }
        for name in (
            "quote_before_submit",
            "credit_before",
            "credit_after",
            "ledger_delta",
            "job_id_hash",
            "protocol_version",
            "study_id",
            "observed_at",
            "control_experiment_id",
            "single_changed_variable",
            "config_digest",
            "config_canonical_json",
            "state_sequence",
            "terminal_state",
            "stage_timestamps",
            "artifacts",
            "scorecard_id",
        ):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        result.update(self.extra_fields)
        return result


def canonical_json_digest(value: Any) -> str:
    """Return deterministic JSON digest for config snapshots."""
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate_record(
    record: ExperimentRecord, *, strict_protocol_requirements: bool = True
) -> list[str]:
    errors: list[str] = []
    if record.protocol_version not in _ALLOWED_PROTOCOLS:
        errors.append("protocol_version must be v1 or v2")
    if record.confidence not in _CONFIDENCE_VALUES:
        errors.append("confidence must be one of: F, I-H, I-M, U, Vendor claim")
    if record.verdict not in _VERDICT_VALUES:
        errors.append("verdict must be one of: blocked, fail, inconclusive, pass")
    if record.submit_count > 0 and any(
        value is None
        for value in (
            record.quote_before_submit,
            record.credit_before,
            record.credit_after,
            record.ledger_delta,
        )
    ):
        errors.append(
            "paid submission requires quote_before_submit, "
            "credit_before, credit_after and ledger_delta"
        )

    if strict_protocol_requirements and (
        record.protocol_version is None
        and any(
            value is not None
            for value in (
                record.observed_at,
                record.single_changed_variable,
                record.state_sequence,
                record.terminal_state,
                record.config_digest,
                record.config_canonical_json,
            )
        )
    ):
        errors.append("protocol_version is required when v2 fields are present")

    if record.protocol_version == "v2":
        missing = sorted(field for field in _V2_REQUIRED if getattr(record, field) is None)
        if missing:
            errors.append(f"v2 protocol record missing fields: {', '.join(missing)}")
        if record.study_id is None or not _is_non_empty_string(record.study_id):
            errors.append("v2 protocol record requires study_id")
        if not _is_non_empty_string(record.single_changed_variable):
            errors.append("single_changed_variable must be a non-empty string for v2")
        if not _is_non_empty_string(record.config_digest):
            errors.append("config_digest must be a non-empty string for v2")
        if record.config_digest is not None and _HEX_64.fullmatch(record.config_digest) is None:
            errors.append("config_digest must be a 64 character lowercase hexadecimal digest")
        if record.state_sequence is not None:
            if not isinstance(record.state_sequence, list) or not record.state_sequence:
                errors.append("state_sequence must be a non-empty list for v2")
            elif not all(_is_non_empty_string(item) for item in record.state_sequence):
                errors.append("state_sequence must only contain non-empty strings for v2")
        else:
            errors.append("state_sequence must be a non-empty list for v2")
        if record.stage_timestamps is not None and not isinstance(record.stage_timestamps, list):
            errors.append("stage_timestamps must be a list when present")

        if record.config_digest is not None and isinstance(
            record.config_canonical_json, (dict, list)
        ):
            if record.config_digest != canonical_json_digest(record.config_canonical_json):
                errors.append("config_digest does not match config_canonical_json")
        elif record.config_digest is not None:
            errors.append("config_canonical_json required when config_digest is present")
        if not _is_non_empty_string(record.terminal_state):
            errors.append("terminal_state must be a non-empty string for v2")
        if not isinstance(record.stage_timestamps or [], list):
            errors.append("stage_timestamps must be a list when present")

    if (
        record.protocol_version is None
        and record.state_sequence is not None
        and not isinstance(record.state_sequence, list)
    ):
        errors.append("state_sequence must be a list")

    for name in sorted(record.extra_fields):
        normalized = name.casefold()
        if normalized == "job_id":
            errors.append("raw job_id is forbidden; store job_id_hash")
        elif normalized in _FORBIDDEN_FIELDS:
            errors.append(f"forbidden field: {name}")

    if record.job_id_hash is not None and _HEX_64.fullmatch(record.job_id_hash) is None:
        errors.append("job_id_hash must be a 64 character lowercase hexadecimal digest")

    return errors
