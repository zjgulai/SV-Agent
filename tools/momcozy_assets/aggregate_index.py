from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from urllib.parse import parse_qsl, urlparse

from .contracts import find_asset_bundles, find_bundle_assets, validate_bundle

BuildStatus = Literal["complete", "partial", "blocked"]
_DISPOSITIONS = ("approved", "hold", "revision-needed", "rejected")
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "credential",
    "sig",
    "signature",
    "token",
    "x-amz-credential",
    "x-amz-signature",
    "x-goog-credential",
    "x-goog-signature",
    "api_key",
    "apikey",
    "auth",
    "secret",
    "session",
}
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SAFE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}")
_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
_EMBEDDED_ABSOLUTE_PATH = re.compile(
    r"(?:^|[^A-Za-z0-9._-])(?:/\S+|[A-Za-z]:[\\/]|\\\\)"
)
_RELEASES_DIRECTORY = "aggregate-index-releases"
_CURRENT_MANIFEST = "aggregate-index-current.json"
_SCOPE_MARKER = ".momcozy-aggregate-scope.json"
_ALLOWED_MODELS = {"GPT Image-2", "Seedance 2.0", "Seedance 2.0 Mini"}
_ALLOWED_ASPECT_RATIOS = {"1:1", "2:3", "3:2", "9:16", "16:9"}
_ALLOWED_RESOLUTIONS = {"1K", "480P"}
_ALLOWED_CONCEPT_GROUPS = {
    "PDP",
    "desktop_campaign",
    "detail_support",
    "pdp_retail",
    "vertical_social",
}
_ALLOWED_CHANNELS = {
    "PDP",
    "Catalog or paid-social hero",
    "Desktop advertising masthead",
    "Desktop PDP masthead",
    "Device-free workday banner",
    "PDP carry-case feature strip",
    "PDP controls and cup detail",
    "Retailer or category banner",
    "TikTok or social static cover",
    "TikTok product-and-case draft",
    "TikTok product-detail draft",
    "Travel-settle-in landing banner",
    "YouTube or CTV end-card base",
}
_ISO_8601_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_PRIVATE_TOKEN = re.compile(
    r"(?i)(?:\b(?:sk|pk)_(?:live|test)_[a-z0-9_-]{8,}|"
    r"\bgh[pousr]_[a-z0-9]{16,}|\bAKIA[0-9A-Z]{16}\b|"
    r"\bxox[baprs]-[a-z0-9-]{20,}|\bglpat-[a-z0-9_-]{16,}|"
    r"\bnpm_[a-z0-9_-]{20,}|\bAIza[a-z0-9_-]{20,}|"
    r"\beyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,})"
)
_UUID = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
)


class AggregateIndexSafetyError(RuntimeError):
    """Raised without the unsafe value when a projection could disclose secrets."""


class AggregateIndexScopeError(RuntimeError):
    """Raised when the caller selects a broad or unsafe filesystem scope."""


class AggregateIndexSourceError(RuntimeError):
    """Raised without source content when structured metadata is invalid."""


@dataclass(frozen=True, slots=True)
class AggregateIndexCompilation:
    status: BuildStatus
    index: dict[str, Any]
    json_bytes: bytes
    markdown_bytes: bytes
    projection_digest: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _assert_safe_projection(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _assert_safe_projection(str(key))
            _assert_safe_projection(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_safe_projection(nested)
        return
    if not isinstance(value, str):
        return
    folded = value.casefold()
    if (
        value.startswith(("/", "\\\\"))
        or re.match(r"^[a-zA-Z]:[\\/]", value)
        or _EMBEDDED_ABSOLUTE_PATH.search(value)
        or _EMAIL.search(value)
        or _PRIVATE_TOKEN.search(value)
        or _UUID.search(value)
        or "http://" in folded
        or "https://" in folded
        or "file://" in folded
    ):
        raise AggregateIndexSafetyError("unsafe aggregate projection")
    if (
        "authorization:" in folded
        or "set-cookie:" in folded
        or "cookie:" in folded
        or re.search(r"\bbearer\s+[a-z0-9._~-]+", folded)
    ):
        raise AggregateIndexSafetyError("unsafe aggregate projection")
    parsed = urlparse(value)
    if parsed.scheme == "file":
        raise AggregateIndexSafetyError("unsafe aggregate projection")
    if parsed.scheme in {"http", "https"}:
        if parsed.username or parsed.password:
            raise AggregateIndexSafetyError("unsafe aggregate projection")
        query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
        if query_keys & _SENSITIVE_QUERY_KEYS:
            raise AggregateIndexSafetyError("unsafe aggregate projection")


def _closed_value(value: object, allowed: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    _assert_safe_projection(value)
    return value if value in allowed else None


def _closed_timestamp(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    _assert_safe_projection(value)
    if _ISO_8601_UTC.fullmatch(value) is not None:
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _project_relative_path(path: Path) -> str:
    value = path.as_posix()
    if not path.parts or any(_SAFE_REF.fullmatch(part) is None for part in path.parts):
        raise AggregateIndexSafetyError("unsafe aggregate projection")
    _assert_safe_projection(value)
    return value


def _require_safe_ref(value: object) -> str:
    if not isinstance(value, str) or _SAFE_REF.fullmatch(value) is None:
        raise AggregateIndexSourceError("invalid aggregate source")
    return value


def _require_optional_digest(value: object) -> None:
    if value is not None and (
        not isinstance(value, str) or _DIGEST.fullmatch(value) is None
    ):
        raise AggregateIndexSourceError("invalid aggregate source")


def _require_safe_relative_path(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, str) or "\\" in value:
        raise AggregateIndexSourceError("invalid aggregate source")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise AggregateIndexSourceError("invalid aggregate source")


def _normalize_disposition(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = re.sub(r"[`*_]", "", value.strip()).casefold()
    normalized = re.sub(r"^status\s*:\s*", "", normalized)
    for disposition in _DISPOSITIONS:
        if normalized == disposition or normalized.startswith(f"{disposition} "):
            return disposition.replace("-", "_")
    return "unknown"


def _commercial_disposition(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    _, separator, section = content.partition("## Commercial disposition")
    if not separator:
        return "missing"
    first_line = next((line.strip() for line in section.splitlines() if line.strip()), "")
    return _normalize_disposition(first_line)


def _render_markdown(index: dict[str, Any]) -> bytes:
    counts = index["counts"]
    lines = [
        "# Momcozy Aggregate Index",
        "",
        f"- State: `{index['state']}`",
        f"- Bundles: `{counts['bundles']}`",
        f"- Structurally valid: `{counts['valid']}`",
        f"- Quarantined: `{counts['quarantined']}`",
        f"- Projection digest: `{index['projection_digest']}`",
        "",
        "## Bundles",
        "",
        "| Bundle | Type | Aspect | Validation | Commercial disposition |",
        "|---|---|---|---|---|",
    ]
    for entry in index["entries"]:
        lines.append(
            "| {bundle_ref} | {asset_type} | {aspect_ratio} | {validation_status} | "
            "{commercial_disposition} |".format(**entry)
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _distribution(values: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = value if isinstance(value, str) and value else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def validate_aggregate_index_projection(index: dict[str, Any]) -> None:
    """Validate one persisted Aggregate Index v1 without consulting source files."""
    index_keys = {
        "brand_workspace",
        "counts",
        "coverage",
        "distributions",
        "entries",
        "findings",
        "limitations",
        "projection_digest",
        "schema_version",
        "scope",
        "state",
    }
    entry_keys = {
        "artifact_sha256",
        "aspect_ratio",
        "asset_type",
        "batch",
        "bundle_record_digest",
        "bundle_ref",
        "channel",
        "commercial_approval",
        "commercial_disposition",
        "concept_group",
        "config_sha256",
        "model",
        "observed_at",
        "prompt_sha256",
        "relative_path",
        "resolution",
        "scoped_index_membership",
        "validation_status",
    }
    finding_severity = {
        "ARTIFACT_HASH_REUSED": "warning",
        "BATCH_MEMBERSHIP_CONFLICT": "blocking",
        "BUNDLE_ID_CONTENT_CONFLICT": "blocking",
        "BUNDLE_ID_DUPLICATE": "blocking",
        "BUNDLE_INVALID": "blocking",
        "BUNDLE_REQUIRED_FILE_MISSING": "blocking",
        "CONCEPT_GROUP_CONFLICT": "blocking",
        "DECLARED_BUNDLE_MISSING": "blocking",
        "LEDGER_STATUS_CONFLICT": "blocking",
        "SCOPED_ASPECT_CONFLICT": "blocking",
        "SCOPED_BUNDLE_MISSING": "blocking",
        "SCOPED_HASH_CONFLICT": "blocking",
        "SCOPED_PATH_CONFLICT": "blocking",
        "SCOPED_PROMPT_HASH_CONFLICT": "blocking",
        "SCOPED_STATUS_CONFLICT": "blocking",
        "SCOPED_TYPE_CONFLICT": "blocking",
        "UNRECOGNIZED_RECIPE_VALUE": "warning",
    }

    def invalid() -> None:
        raise AggregateIndexSourceError("invalid aggregate projection")

    def valid_availability(
        value: object,
        *,
        allowed: set[str] | None = None,
        safe_ref: bool = False,
    ) -> bool:
        if not isinstance(value, dict) or set(value) != {"availability", "value"}:
            return False
        availability = value.get("availability")
        projected = value.get("value")
        if availability == "unknown":
            return projected is None
        if availability != "present" or not isinstance(projected, str):
            return False
        if allowed is not None:
            return projected in allowed
        return not safe_ref or _SAFE_REF.fullmatch(projected) is not None

    if (
        set(index) != index_keys
        or index.get("brand_workspace") != "momcozy"
        or index.get("schema_version") != "momcozy-aggregate-index.v1"
        or index.get("scope") != "whole_workspace"
        or not isinstance(index.get("entries"), list)
        or not isinstance(index.get("findings"), list)
        or not isinstance(index.get("limitations"), list)
        or not isinstance(index.get("projection_digest"), str)
        or _DIGEST.fullmatch(index["projection_digest"]) is None
    ):
        invalid()
    _assert_safe_projection(index)
    entries: list[dict[str, Any]] = []
    for raw_entry in index["entries"]:
        if not isinstance(raw_entry, dict) or set(raw_entry) != entry_keys:
            invalid()
        entry = raw_entry
        for digest_field in (
            "artifact_sha256",
            "config_sha256",
            "prompt_sha256",
        ):
            _require_optional_digest(entry[digest_field])
        if (
            not isinstance(entry["bundle_record_digest"], str)
            or _DIGEST.fullmatch(entry["bundle_record_digest"]) is None
            or not isinstance(entry["bundle_ref"], str)
            or _SAFE_REF.fullmatch(entry["bundle_ref"]) is None
            or entry["aspect_ratio"] not in _ALLOWED_ASPECT_RATIOS | {None}
            or entry["asset_type"] not in {"image", "video", None}
            or entry["model"] not in _ALLOWED_MODELS | {None}
            or entry["resolution"] not in _ALLOWED_RESOLUTIONS | {None}
            or entry["commercial_disposition"]
            not in {
                "approved",
                "hold",
                "rejected",
                "revision_needed",
                "missing",
                "unknown",
            }
            or entry["scoped_index_membership"] not in {"indexed", "unindexed"}
            or entry["validation_status"] not in {"valid", "quarantined"}
            or entry["commercial_approval"] != {"availability": "unknown"}
            or not valid_availability(entry["batch"], safe_ref=True)
            or not valid_availability(entry["channel"], allowed=_ALLOWED_CHANNELS)
            or not valid_availability(
                entry["concept_group"], allowed=_ALLOWED_CONCEPT_GROUPS
            )
        ):
            invalid()
        observed_at = entry["observed_at"]
        if observed_at is not None and _closed_timestamp(observed_at) != observed_at:
            invalid()
        relative_path = entry["relative_path"]
        if not isinstance(relative_path, str) or "\\" in relative_path:
            invalid()
        projected_path = PurePosixPath(relative_path)
        if (
            projected_path.is_absolute()
            or not projected_path.parts
            or any(_SAFE_REF.fullmatch(part) is None for part in projected_path.parts)
        ):
            invalid()
        entries.append(entry)
    if entries != sorted(
        entries, key=lambda entry: (entry["relative_path"], entry["bundle_ref"])
    ):
        invalid()

    findings: list[dict[str, str]] = []
    for raw_finding in index["findings"]:
        if (
            not isinstance(raw_finding, dict)
            or set(raw_finding) != {"bundle_ref", "code", "message", "severity"}
            or not all(isinstance(value, str) for value in raw_finding.values())
            or _SAFE_REF.fullmatch(raw_finding["bundle_ref"]) is None
            or finding_severity.get(raw_finding["code"])
            != raw_finding["severity"]
        ):
            invalid()
        findings.append(raw_finding)
    if findings != sorted(
        findings, key=lambda finding: (finding["bundle_ref"], finding["code"])
    ):
        invalid()

    quarantined = sum(
        entry["validation_status"] == "quarantined" for entry in entries
    )
    expected_counts = {
        "bundles": len(entries),
        "quarantined": quarantined,
        "valid": len(entries) - quarantined,
    }
    expected_coverage = {
        field: {
            "known": sum(entry[field]["availability"] == "present" for entry in entries),
            "unknown": sum(
                entry[field]["availability"] == "unknown" for entry in entries
            ),
        }
        for field in ("batch", "channel", "commercial_approval", "concept_group")
    }
    expected_distributions = {
        "aspect_ratio": _distribution([entry["aspect_ratio"] for entry in entries]),
        "asset_type": _distribution([entry["asset_type"] for entry in entries]),
        "batch": _distribution([entry["batch"]["value"] for entry in entries]),
        "channel": _distribution([entry["channel"]["value"] for entry in entries]),
        "commercial_disposition": {
            disposition: sum(
                entry["commercial_disposition"] == disposition for entry in entries
            )
            for disposition in (
                "approved",
                "hold",
                "rejected",
                "revision_needed",
                "missing",
                "unknown",
            )
        },
        "concept_group": _distribution(
            [entry["concept_group"]["value"] for entry in entries]
        ),
        "model": _distribution([entry["model"] for entry in entries]),
        "validation_status": _distribution(
            [entry["validation_status"] for entry in entries]
        ),
    }
    expected_limitations = ["COMMERCIAL_APPROVAL_UNAVAILABLE"]
    if any(finding["code"] == "UNRECOGNIZED_RECIPE_VALUE" for finding in findings):
        expected_limitations.append("RECIPE_PROJECTION_INCOMPLETE")
    for field, code in (
        ("batch", "BATCH_METADATA_INCOMPLETE"),
        ("channel", "CHANNEL_METADATA_INCOMPLETE"),
        ("concept_group", "CONCEPT_GROUP_METADATA_INCOMPLETE"),
    ):
        if expected_coverage[field]["unknown"]:
            expected_limitations.append(code)
    disposition = expected_distributions["commercial_disposition"]
    if disposition["unknown"]:
        expected_limitations.append("QA_DISPOSITION_UNKNOWN")
    if disposition["missing"]:
        expected_limitations.append("QA_DISPOSITION_MISSING")
    expected_limitations.sort()
    expected_state = (
        "blocked"
        if any(finding["severity"] == "blocking" for finding in findings)
        else "partial"
    )
    digest_input = dict(index)
    projection_digest = digest_input.pop("projection_digest")
    if (
        index["counts"] != expected_counts
        or index["coverage"] != expected_coverage
        or index["distributions"] != expected_distributions
        or index["limitations"] != expected_limitations
        or index["state"] != expected_state
        or hashlib.sha256(_canonical_bytes(digest_input)).hexdigest()
        != projection_digest
    ):
        invalid()


def _find_bundle_candidates(root: Path) -> list[Path]:
    candidates = set(find_asset_bundles(root))
    for name in ("prompt.md", "provenance.json", "qa.md", "hashes.sha256", "asset.*"):
        candidates.update(path.parent for path in root.rglob(name) if path.is_file())
    return sorted(candidates)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AggregateIndexSourceError("invalid aggregate source") from error
    if not isinstance(value, dict):
        raise AggregateIndexSourceError("invalid aggregate source")
    return value


def _validate_scope_marker(root: Path) -> None:
    try:
        value = json.loads((root / _SCOPE_MARKER).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AggregateIndexScopeError("unsafe aggregate root") from error
    if value != {
        "brand_workspace": "momcozy",
        "schema_version": "momcozy-aggregate-scope.v1",
    }:
        raise AggregateIndexScopeError("unsafe aggregate root")


def _load_scoped_library_indexes(root: Path) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("library-index.json")):
        value = _read_json_object(path)
        if value.get("schema_version") != "momcozy-local-library.v1":
            raise AggregateIndexSourceError("invalid aggregate source")
        batch_id = _require_safe_ref(value.get("batch_id"))
        entries = value.get("entries")
        if not isinstance(entries, list):
            raise AggregateIndexSourceError("invalid aggregate source")
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                raise AggregateIndexSourceError("invalid aggregate source")
            bundle_ref = _require_safe_ref(raw_entry.get("asset_id"))
            if bundle_ref in by_id:
                raise AggregateIndexSourceError("invalid aggregate source")
            for field in ("type", "aspect_ratio", "intended_channel", "status"):
                if field in raw_entry and not isinstance(raw_entry[field], str):
                    raise AggregateIndexSourceError("invalid aggregate source")
            _require_safe_relative_path(raw_entry.get("relative_asset_path"))
            _require_optional_digest(raw_entry.get("artifact_sha256"))
            _require_optional_digest(raw_entry.get("prompt_sha256"))
            by_id[bundle_ref] = {**raw_entry, "_batch_id": batch_id}
    return by_id


def _load_batch_sources(
    root: Path,
) -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
    set[str],
]:
    batches: dict[str, set[str]] = {}
    concept_groups: dict[str, set[str]] = {}
    dispositions: dict[str, set[str]] = {}
    declared_refs: set[str] = set()
    seen_ledger_records: set[tuple[str, str]] = set()
    seen_ledger_batches: set[str] = set()
    for path in sorted(root.rglob("batch-*-ledger.json")):
        value = _read_json_object(path)
        schema_version = value.get("schema_version")
        if schema_version is not None and schema_version != "momcozy-asset-ledger.v1":
            raise AggregateIndexSourceError("invalid aggregate source")
        batch_id = _require_safe_ref(value.get("batch_id"))
        if batch_id in seen_ledger_batches:
            raise AggregateIndexSourceError("invalid aggregate source")
        seen_ledger_batches.add(batch_id)
        records = value.get("assets", value.get("entries"))
        if not isinstance(records, list):
            raise AggregateIndexSourceError("invalid aggregate source")
        for record in records:
            if not isinstance(record, dict):
                raise AggregateIndexSourceError("invalid aggregate source")
            bundle_ref = _require_safe_ref(record.get("asset_id"))
            identity = (batch_id, bundle_ref)
            if identity in seen_ledger_records:
                raise AggregateIndexSourceError("invalid aggregate source")
            seen_ledger_records.add(identity)
            if "qa_status" in record and not isinstance(record["qa_status"], str):
                raise AggregateIndexSourceError("invalid aggregate source")
            batches.setdefault(bundle_ref, set()).add(batch_id)
            disposition = _normalize_disposition(record.get("qa_status"))
            if disposition != "unknown":
                dispositions.setdefault(bundle_ref, set()).add(disposition)
            declared_refs.add(bundle_ref)
    seen_plan_jobs: set[tuple[str, str]] = set()
    for path in sorted(root.rglob("batch-*-plan.json")):
        value = _read_json_object(path)
        if value.get("schema_version") not in {
            "momcozy-asset-batch.v1",
            "momcozy-image-batch.v1",
        }:
            raise AggregateIndexSourceError("invalid aggregate source")
        batch_id = _require_safe_ref(value.get("batch_id"))
        jobs = value.get("jobs")
        if not isinstance(jobs, list):
            raise AggregateIndexSourceError("invalid aggregate source")
        for job in jobs:
            if (
                not isinstance(job, dict)
                or not isinstance(job.get("quantity"), int)
                or isinstance(job.get("quantity"), bool)
                or job["quantity"] < 1
            ):
                raise AggregateIndexSourceError("invalid aggregate source")
            job_id = _require_safe_ref(job.get("id"))
            identity = (batch_id, job_id)
            if identity in seen_plan_jobs:
                raise AggregateIndexSourceError("invalid aggregate source")
            seen_plan_jobs.add(identity)
            family = job.get("family")
            if family is not None and not isinstance(family, str):
                raise AggregateIndexSourceError("invalid aggregate source")
            for variant_number in range(1, job["quantity"] + 1):
                bundle_ref = f"{job_id}-v{variant_number:02d}"
                batches.setdefault(bundle_ref, set()).add(batch_id)
                concept_group = _closed_value(family, _ALLOWED_CONCEPT_GROUPS)
                if concept_group is not None:
                    concept_groups.setdefault(bundle_ref, set()).add(concept_group)
                declared_refs.add(bundle_ref)
    return batches, concept_groups, dispositions, declared_refs


def _path_has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.absolute().parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _capture_source_state(root: Path) -> tuple[tuple[object, ...], ...]:
    state: list[tuple[object, ...]] = []
    try:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if relative.parts and relative.parts[0] == _RELEASES_DIRECTORY:
                continue
            if path.name in {
                _CURRENT_MANIFEST,
                "aggregate-index.json",
                "aggregate-index.md",
            }:
                continue
            if not path.is_file():
                continue
            stat = path.stat(follow_symlinks=False)
            state.append(
                (
                    relative.as_posix(),
                    stat.st_dev,
                    stat.st_ino,
                    stat.st_size,
                    stat.st_mtime_ns,
                    _sha256_file(path),
                )
            )
    except OSError as error:
        raise AggregateIndexSourceError("invalid aggregate source") from error
    return tuple(state)


def compile_aggregate_index(root: Path) -> AggregateIndexCompilation:
    """Compile one approved local Momcozy Brand Workspace into safe index bytes."""
    root = Path(root).absolute()
    if (
        _path_has_symlink_component(root)
        or not root.is_dir()
        or root.resolve() == Path.home().resolve()
        or root.resolve().parent == root.resolve()
        or (root / ".git").exists()
        or any(path.name == ".git" for path in root.rglob(".git"))
    ):
        raise AggregateIndexScopeError("unsafe aggregate root")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise AggregateIndexScopeError("unsafe aggregate root")
    _validate_scope_marker(root)
    source_state = _capture_source_state(root)
    scoped_entries = _load_scoped_library_indexes(root)
    (
        source_batches,
        source_concept_groups,
        source_dispositions,
        source_declared_refs,
    ) = _load_batch_sources(root)
    entries: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    recipe_projection_incomplete = False
    for bundle in _find_bundle_candidates(root):
        try:
            errors = validate_bundle(bundle)
        except (OSError, UnicodeDecodeError) as error:
            raise AggregateIndexSourceError("invalid aggregate source") from error
        recipe_path = bundle / "recipe.json"
        try:
            recipe = (
                json.loads(recipe_path.read_text(encoding="utf-8"))
                if recipe_path.is_file()
                else {}
            )
        except json.JSONDecodeError:
            recipe = {}
        except (OSError, UnicodeDecodeError) as error:
            raise AggregateIndexSourceError("invalid aggregate source") from error
        if not isinstance(recipe, dict):
            recipe = {}
        assets = find_bundle_assets(bundle)
        bundle_ref = _require_safe_ref(recipe.get("asset_id", bundle.name))
        scoped_entry = scoped_entries.get(bundle_ref)
        channel = _closed_value(
            scoped_entry.get("intended_channel") if scoped_entry is not None else None,
            _ALLOWED_CHANNELS,
        )
        batch_candidates = set(source_batches.get(bundle_ref, set()))
        if scoped_entry is not None:
            batch_candidates.add(scoped_entry["_batch_id"])
        config = recipe.get("config")
        if isinstance(config, dict) and isinstance(config.get("batch_id"), str):
            batch_candidates.add(_require_safe_ref(config["batch_id"]))
        batch_value = next(iter(batch_candidates)) if len(batch_candidates) == 1 else None
        concept_candidates = source_concept_groups.get(bundle_ref, set())
        concept_group = (
            next(iter(concept_candidates)) if len(concept_candidates) == 1 else None
        )
        try:
            commercial_disposition = (
                _commercial_disposition(bundle / "qa.md")
                if (bundle / "qa.md").is_file()
                else "missing"
            )
        except (OSError, UnicodeDecodeError) as error:
            raise AggregateIndexSourceError("invalid aggregate source") from error
        supported_asset_names = {path.name for path in assets}
        bundle_file_digests = {
            path.name: _sha256_file(path)
            for path in sorted(bundle.iterdir())
            if path.is_file()
            and (
                path.name
                in {
                    "hashes.sha256",
                    "prompt.md",
                    "provenance.json",
                    "qa.md",
                    "recipe.json",
                }
                or path.name in supported_asset_names
            )
        }
        bundle_record_digest = hashlib.sha256(
            _canonical_bytes(bundle_file_digests)
        ).hexdigest()
        projected_recipe_values = {
            "aspect_ratio": _closed_value(
                recipe.get("aspect_ratio"), _ALLOWED_ASPECT_RATIOS
            ),
            "asset_type": _closed_value(recipe.get("asset_type"), {"image", "video"}),
            "model": _closed_value(recipe.get("model"), _ALLOWED_MODELS),
            "observed_at": _closed_timestamp(recipe.get("observed_at")),
            "resolution": _closed_value(
                recipe.get("resolution"), _ALLOWED_RESOLUTIONS
            ),
        }
        for field, projected_value in projected_recipe_values.items():
            if recipe.get(field) is None or projected_value is not None:
                continue
            recipe_projection_incomplete = True
            findings.append(
                {
                    "bundle_ref": bundle_ref,
                    "code": "UNRECOGNIZED_RECIPE_VALUE",
                    "message": f"recipe {field} is outside the safe aggregate vocabulary",
                    "severity": "warning",
                }
            )
        entry = {
            "artifact_sha256": _sha256_file(assets[0]) if len(assets) == 1 else None,
            "aspect_ratio": projected_recipe_values["aspect_ratio"],
            "asset_type": projected_recipe_values["asset_type"],
            "batch": {
                "availability": "present" if batch_value is not None else "unknown",
                "value": batch_value,
            },
            "bundle_ref": bundle_ref,
            "bundle_record_digest": bundle_record_digest,
            "channel": {
                "availability": "present" if channel is not None else "unknown",
                "value": channel,
            },
            "commercial_disposition": commercial_disposition,
            "commercial_approval": {"availability": "unknown"},
            "concept_group": {
                "availability": "present" if concept_group is not None else "unknown",
                "value": concept_group,
            },
            "config_sha256": (
                recipe.get("config_sha256")
                if isinstance(recipe.get("config_sha256"), str)
                and _DIGEST.fullmatch(recipe["config_sha256"]) is not None
                else None
            ),
            "model": projected_recipe_values["model"],
            "observed_at": projected_recipe_values["observed_at"],
            "prompt_sha256": (
                recipe.get("prompt_sha256")
                if isinstance(recipe.get("prompt_sha256"), str)
                and _DIGEST.fullmatch(recipe["prompt_sha256"]) is not None
                else None
            ),
            "relative_path": _project_relative_path(bundle.relative_to(root)),
            "resolution": projected_recipe_values["resolution"],
            "scoped_index_membership": (
                "indexed" if scoped_entry is not None else "unindexed"
            ),
            "validation_status": "valid" if not errors else "quarantined",
        }
        entries.append(entry)
        if len(batch_candidates) > 1:
            findings.append(
                {
                    "bundle_ref": bundle_ref,
                    "code": "BATCH_MEMBERSHIP_CONFLICT",
                    "message": "structured sources disagree about batch membership",
                    "severity": "blocking",
                }
            )
        if len(concept_candidates) > 1:
            findings.append(
                {
                    "bundle_ref": bundle_ref,
                    "code": "CONCEPT_GROUP_CONFLICT",
                    "message": "structured sources disagree about concept group",
                    "severity": "blocking",
                }
            )
        ledger_dispositions = source_dispositions.get(bundle_ref, set())
        if (
            commercial_disposition != "unknown"
            and ledger_dispositions
            and ledger_dispositions != {commercial_disposition}
        ):
            findings.append(
                {
                    "bundle_ref": bundle_ref,
                    "code": "LEDGER_STATUS_CONFLICT",
                    "message": "ledger QA status conflicts with bundle QA disposition",
                    "severity": "blocking",
                }
            )
        if scoped_entry is not None:
            scoped_disposition = _normalize_disposition(scoped_entry.get("status"))
            if (
                commercial_disposition != "unknown"
                and scoped_disposition != "unknown"
                and commercial_disposition != scoped_disposition
            ):
                findings.append(
                    {
                        "bundle_ref": bundle_ref,
                        "code": "SCOPED_STATUS_CONFLICT",
                        "message": "scoped status conflicts with bundle QA disposition",
                        "severity": "blocking",
                    }
                )
            scoped_hash = scoped_entry.get("artifact_sha256")
            if (
                isinstance(scoped_hash, str)
                and isinstance(entry["artifact_sha256"], str)
                and scoped_hash != entry["artifact_sha256"]
            ):
                findings.append(
                    {
                        "bundle_ref": bundle_ref,
                        "code": "SCOPED_HASH_CONFLICT",
                        "message": "scoped artifact digest conflicts with the bundle artifact",
                        "severity": "blocking",
                    }
                )
            scoped_prompt_hash = scoped_entry.get("prompt_sha256")
            if (
                isinstance(scoped_prompt_hash, str)
                and isinstance(entry["prompt_sha256"], str)
                and scoped_prompt_hash != entry["prompt_sha256"]
            ):
                findings.append(
                    {
                        "bundle_ref": bundle_ref,
                        "code": "SCOPED_PROMPT_HASH_CONFLICT",
                        "message": "scoped prompt digest conflicts with the bundle recipe",
                        "severity": "blocking",
                    }
                )
            scoped_type = scoped_entry.get("type")
            if isinstance(scoped_type, str) and scoped_type != entry["asset_type"]:
                findings.append(
                    {
                        "bundle_ref": bundle_ref,
                        "code": "SCOPED_TYPE_CONFLICT",
                        "message": "scoped asset type conflicts with the bundle recipe",
                        "severity": "blocking",
                    }
                )
            scoped_aspect = scoped_entry.get("aspect_ratio")
            if isinstance(scoped_aspect, str) and scoped_aspect != entry["aspect_ratio"]:
                findings.append(
                    {
                        "bundle_ref": bundle_ref,
                        "code": "SCOPED_ASPECT_CONFLICT",
                        "message": "scoped aspect ratio conflicts with the bundle recipe",
                        "severity": "blocking",
                    }
                )
            scoped_path = scoped_entry.get("relative_asset_path")
            actual_asset_path = (
                assets[0].relative_to(root).as_posix() if len(assets) == 1 else None
            )
            if isinstance(scoped_path, str) and scoped_path != actual_asset_path:
                findings.append(
                    {
                        "bundle_ref": bundle_ref,
                        "code": "SCOPED_PATH_CONFLICT",
                        "message": "scoped asset path conflicts with the bundle artifact",
                        "severity": "blocking",
                    }
                )
        findings.extend(
            {
                "bundle_ref": str(entry["bundle_ref"]),
                "code": (
                    "BUNDLE_REQUIRED_FILE_MISSING"
                    if error.startswith("missing required file:")
                    else "BUNDLE_INVALID"
                ),
                "message": error,
                "severity": "blocking",
            }
            for error in errors
        )

    entries.sort(key=lambda entry: (entry["relative_path"], entry["bundle_ref"]))
    entries_by_ref: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        entries_by_ref.setdefault(str(entry["bundle_ref"]), []).append(entry)
    for missing_ref in sorted(set(scoped_entries) - set(entries_by_ref)):
        findings.append(
            {
                "bundle_ref": missing_ref,
                "code": "SCOPED_BUNDLE_MISSING",
                "message": "scoped index references a bundle absent from the approved scope",
                "severity": "blocking",
            }
        )
    for missing_ref in sorted(source_declared_refs - set(entries_by_ref)):
        findings.append(
            {
                "bundle_ref": missing_ref,
                "code": "DECLARED_BUNDLE_MISSING",
                "message": "batch source references a bundle absent from the approved scope",
                "severity": "blocking",
            }
        )
    for bundle_ref, matching in sorted(entries_by_ref.items()):
        if len(matching) < 2:
            continue
        artifact_hashes = {entry["artifact_sha256"] for entry in matching}
        findings.append(
            {
                "bundle_ref": bundle_ref,
                "code": (
                    "BUNDLE_ID_DUPLICATE"
                    if len(artifact_hashes) == 1
                    else "BUNDLE_ID_CONTENT_CONFLICT"
                ),
                "message": "bundle identity is not unique within the approved scope",
                "severity": "blocking",
            }
        )
    entries_by_artifact: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        artifact_hash = entry["artifact_sha256"]
        if isinstance(artifact_hash, str):
            entries_by_artifact.setdefault(artifact_hash, []).append(entry)
    for matching in entries_by_artifact.values():
        bundle_refs = sorted({str(entry["bundle_ref"]) for entry in matching})
        if len(bundle_refs) < 2:
            continue
        findings.append(
            {
                "bundle_ref": bundle_refs[0],
                "code": "ARTIFACT_HASH_REUSED",
                "message": f"artifact digest is shared by {len(bundle_refs)} bundle identities",
                "severity": "warning",
            }
        )
    findings.sort(key=lambda finding: (finding["bundle_ref"], finding["code"]))
    quarantined = sum(entry["validation_status"] == "quarantined" for entry in entries)
    disposition_counts = {
        disposition: sum(
            entry["commercial_disposition"] == disposition for entry in entries
        )
        for disposition in (
            "approved",
            "hold",
            "rejected",
            "revision_needed",
            "missing",
            "unknown",
        )
    }
    channel_known = sum(entry["channel"]["availability"] == "present" for entry in entries)
    batch_known = sum(entry["batch"]["availability"] == "present" for entry in entries)
    concept_known = sum(
        entry["concept_group"]["availability"] == "present" for entry in entries
    )
    limitations = ["COMMERCIAL_APPROVAL_UNAVAILABLE"]
    if recipe_projection_incomplete:
        limitations.append("RECIPE_PROJECTION_INCOMPLETE")
    if batch_known != len(entries):
        limitations.append("BATCH_METADATA_INCOMPLETE")
    if channel_known != len(entries):
        limitations.append("CHANNEL_METADATA_INCOMPLETE")
    if concept_known != len(entries):
        limitations.append("CONCEPT_GROUP_METADATA_INCOMPLETE")
    if disposition_counts["unknown"]:
        limitations.append("QA_DISPOSITION_UNKNOWN")
    if disposition_counts["missing"]:
        limitations.append("QA_DISPOSITION_MISSING")
    limitations.sort()
    state: BuildStatus = (
        "blocked"
        if any(finding["severity"] == "blocking" for finding in findings)
        else "partial"
    )
    index: dict[str, Any] = {
        "brand_workspace": "momcozy",
        "counts": {
            "bundles": len(entries),
            "quarantined": quarantined,
            "valid": len(entries) - quarantined,
        },
        "coverage": {
            "batch": {"known": batch_known, "unknown": len(entries) - batch_known},
            "channel": {
                "known": channel_known,
                "unknown": len(entries) - channel_known,
            },
            "commercial_approval": {"known": 0, "unknown": len(entries)},
            "concept_group": {
                "known": concept_known,
                "unknown": len(entries) - concept_known,
            },
        },
        "distributions": {
            "aspect_ratio": _distribution(
                [entry["aspect_ratio"] for entry in entries]
            ),
            "asset_type": _distribution([entry["asset_type"] for entry in entries]),
            "batch": _distribution([entry["batch"]["value"] for entry in entries]),
            "channel": _distribution([entry["channel"]["value"] for entry in entries]),
            "commercial_disposition": disposition_counts,
            "concept_group": _distribution(
                [entry["concept_group"]["value"] for entry in entries]
            ),
            "model": _distribution([entry["model"] for entry in entries]),
            "validation_status": _distribution(
                [entry["validation_status"] for entry in entries]
            ),
        },
        "entries": entries,
        "findings": findings,
        "limitations": limitations,
        "schema_version": "momcozy-aggregate-index.v1",
        "scope": "whole_workspace",
        "state": state,
    }
    if _capture_source_state(root) != source_state:
        raise AggregateIndexSourceError("aggregate source changed during scan")
    _assert_safe_projection(index)
    digest = hashlib.sha256(_canonical_bytes(index)).hexdigest()
    index["projection_digest"] = digest
    validate_aggregate_index_projection(index)
    json_bytes = _canonical_bytes(index)
    markdown_bytes = _render_markdown(index)
    return AggregateIndexCompilation(
        status=state,
        index=index,
        json_bytes=json_bytes,
        markdown_bytes=markdown_bytes,
        projection_digest=digest,
    )


def _atomic_write(path: Path, content: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _publish_release(root: Path, compilation: AggregateIndexCompilation) -> None:
    releases = root / _RELEASES_DIRECTORY
    releases.mkdir(exist_ok=True)
    if releases.is_symlink() or not releases.is_dir():
        raise OSError("unsafe release directory")
    release = releases / compilation.projection_digest
    json_name = "aggregate-index.json"
    markdown_name = "aggregate-index.md"
    if release.exists():
        if (
            not release.is_dir()
            or (release / json_name).read_bytes() != compilation.json_bytes
            or (release / markdown_name).read_bytes() != compilation.markdown_bytes
        ):
            raise OSError("release digest collision")
    else:
        staging = Path(tempfile.mkdtemp(dir=releases, prefix=".staging-"))
        try:
            for name, content in (
                (json_name, compilation.json_bytes),
                (markdown_name, compilation.markdown_bytes),
            ):
                with (staging / name).open("xb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.replace(staging, release)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    relative_release = release.relative_to(root).as_posix()
    manifest = {
        "json_path": f"{relative_release}/{json_name}",
        "json_sha256": hashlib.sha256(compilation.json_bytes).hexdigest(),
        "markdown_path": f"{relative_release}/{markdown_name}",
        "markdown_sha256": hashlib.sha256(compilation.markdown_bytes).hexdigest(),
        "projection_digest": compilation.projection_digest,
        "schema_version": "momcozy-aggregate-release.v1",
    }
    _assert_safe_projection(manifest)
    _atomic_write(root / _CURRENT_MANIFEST, _canonical_bytes(manifest))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic Momcozy whole-workspace Aggregate Index"
    )
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    root = args.root.absolute()
    try:
        compilation = compile_aggregate_index(root)
        if compilation.status == "blocked":
            print(
                "INDEX_BLOCKED "
                f"bundles={compilation.index['counts']['bundles']} "
                f"digest={compilation.projection_digest}"
            )
            return 1
        _publish_release(root, compilation)
    except AggregateIndexScopeError:
        print("INDEX_FAILED code=UNSAFE_AGGREGATE_ROOT", file=sys.stderr)
        return 3
    except AggregateIndexSafetyError:
        print("INDEX_FAILED code=UNSAFE_AGGREGATE_PROJECTION", file=sys.stderr)
        return 3
    except AggregateIndexSourceError:
        print("INDEX_FAILED code=INVALID_AGGREGATE_SOURCE", file=sys.stderr)
        return 3
    except (OSError, UnicodeDecodeError):
        print("INDEX_FAILED code=AGGREGATE_IO_FAILURE", file=sys.stderr)
        return 3
    print(
        "INDEX_RELEASED "
        f"state={compilation.status} "
        f"bundles={compilation.index['counts']['bundles']} "
        f"digest={compilation.projection_digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
