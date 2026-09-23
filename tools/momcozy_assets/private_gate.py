from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never, TypeGuard

from .aggregate_index import (
    AggregateIndexSafetyError,
    AggregateIndexScopeError,
    AggregateIndexSourceError,
    _render_markdown,
    compile_aggregate_index,
    validate_aggregate_index_projection,
)

_BASELINE_PATH = Path(__file__).parent / "baselines" / "momcozy-m5-v1.json"
_CURRENT_MANIFEST = "aggregate-index-current.json"
_DIGEST_LENGTH = 64
_BASELINE_LIMIT = 64 * 1024
_MANIFEST_LIMIT = 64 * 1024
_PROJECTION_LIMIT = 16 * 1024 * 1024
_BASELINE_KEYS = {
    "aggregate_schema_version",
    "asset_type",
    "baseline_id",
    "counts",
    "coverage",
    "disposition",
    "findings",
    "limitations",
    "observed_at_present",
    "projection_digest",
    "resolution",
    "schema_version",
    "state",
    "unique_bundle_refs",
    "unique_relative_paths",
}
_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)


@dataclass(frozen=True, slots=True)
class PrivateGateResult:
    baseline_id: str
    state: str
    bundles: int


class PrivateGateFailure(RuntimeError):
    def __init__(self, code: str, exit_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        del message
        print("MOMCOZY_PRIVATE_GATE_FAILED code=USAGE_ERROR", file=sys.stderr)
        raise SystemExit(2)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _is_sha256(value: object) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and len(value) == _DIGEST_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _read_regular_file_at(
    directory_fd: int,
    name: str,
    *,
    limit: int,
    missing_code: str,
    invalid_code: str = "CURRENT_RELEASE_INVALID",
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or metadata.st_size > limit
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise PrivateGateFailure(
                invalid_code,
                4 if invalid_code != "BASELINE_INVALID" else 3,
            )
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > limit:
            raise PrivateGateFailure(
                invalid_code,
                4 if invalid_code != "BASELINE_INVALID" else 3,
            )
        return content
    except FileNotFoundError as error:
        raise PrivateGateFailure(missing_code, 4) from error
    except PrivateGateFailure:
        raise
    except OSError as error:
        raise PrivateGateFailure(
            invalid_code,
            4 if invalid_code != "BASELINE_INVALID" else 3,
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _directory_metadata_is_safe(
    metadata: os.stat_result, *, require_current_owner: bool
) -> bool:
    if not stat.S_ISDIR(metadata.st_mode):
        return False
    if require_current_owner and metadata.st_uid != os.getuid():
        return False
    writable = metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    if require_current_owner:
        return not writable
    return not writable or bool(metadata.st_mode & stat.S_ISVTX)


def _open_root_directory(root: Path) -> int:
    if not root.is_absolute() or any(part in {".", ".."} for part in root.parts):
        raise PrivateGateFailure("UNSAFE_ROOT", 3)
    descriptor = os.open(os.sep, _DIRECTORY_FLAGS)
    try:
        parts = root.parts[1:]
        for index, component in enumerate(parts):
            next_descriptor = os.open(
                component,
                _DIRECTORY_FLAGS,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
            metadata = os.fstat(descriptor)
            is_leaf = index == len(parts) - 1
            if not _directory_metadata_is_safe(
                metadata, require_current_owner=is_leaf
            ):
                raise PrivateGateFailure("UNSAFE_ROOT", 3)
        if not parts and not _directory_metadata_is_safe(
            os.fstat(descriptor), require_current_owner=True
        ):
            raise PrivateGateFailure("UNSAFE_ROOT", 3)
        return descriptor
    except PrivateGateFailure:
        os.close(descriptor)
        raise
    except OSError as error:
        os.close(descriptor)
        raise PrivateGateFailure("UNSAFE_ROOT", 3) from error


def _open_private_directory_at(parent_fd: int, name: str) -> int:
    try:
        descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        if not _directory_metadata_is_safe(
            os.fstat(descriptor), require_current_owner=True
        ):
            os.close(descriptor)
            raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4)
        return descriptor
    except PrivateGateFailure:
        raise
    except OSError as error:
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4) from error


def _read_json_object(content: bytes, *, code: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PrivateGateFailure(code, 4) from error
    if not isinstance(value, dict):
        raise PrivateGateFailure(code, 4)
    return value


def _validate_release_projection(
    json_bytes: bytes,
    markdown_bytes: bytes,
    projection_digest: str,
) -> None:
    index = _read_json_object(json_bytes, code="CURRENT_RELEASE_INVALID")
    try:
        validate_aggregate_index_projection(index)
    except (AggregateIndexSafetyError, AggregateIndexSourceError) as error:
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4) from error
    if (
        index.get("projection_digest") != projection_digest
        or _canonical_bytes(index) != json_bytes
    ):
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4)
    digest_input = dict(index)
    del digest_input["projection_digest"]
    if _sha256(_canonical_bytes(digest_input)) != projection_digest:
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4)
    try:
        rendered_markdown = _render_markdown(index)
    except (KeyError, TypeError, ValueError) as error:
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4) from error
    if rendered_markdown != markdown_bytes:
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4)


def _load_baseline() -> dict[str, Any]:
    directory_fd: int | None = None
    try:
        directory_fd = _open_root_directory(_BASELINE_PATH.parent)
        content = _read_regular_file_at(
            directory_fd,
            _BASELINE_PATH.name,
            limit=_BASELINE_LIMIT,
            missing_code="BASELINE_INVALID",
            invalid_code="BASELINE_INVALID",
        )
        value = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PrivateGateFailure) as error:
        raise PrivateGateFailure("BASELINE_INVALID", 3) from error
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
    if (
        not isinstance(value, dict)
        or set(value) != _BASELINE_KEYS
        or not _is_sha256(value.get("projection_digest"))
        or content != _canonical_bytes(value)
    ):
        raise PrivateGateFailure("BASELINE_INVALID", 3)
    return value


def _baseline_projection(index: dict[str, Any]) -> dict[str, Any]:
    entries = index["entries"]
    resolution: dict[str, int] = {}
    for entry in entries:
        value = entry["resolution"]
        key = value if isinstance(value, str) else "unknown"
        resolution[key] = resolution.get(key, 0) + 1
    return {
        "aggregate_schema_version": index["schema_version"],
        "asset_type": index["distributions"]["asset_type"],
        "baseline_id": "momcozy-m5-v1",
        "counts": index["counts"],
        "coverage": index["coverage"],
        "disposition": index["distributions"]["commercial_disposition"],
        "findings": len(index["findings"]),
        "limitations": index["limitations"],
        "observed_at_present": sum(
            entry["observed_at"] is not None for entry in entries
        ),
        "projection_digest": index["projection_digest"],
        "resolution": dict(sorted(resolution.items())),
        "schema_version": "momcozy-private-gate-baseline.v1",
        "state": index["state"],
        "unique_bundle_refs": len({entry["bundle_ref"] for entry in entries}),
        "unique_relative_paths": len({entry["relative_path"] for entry in entries}),
    }


def _load_current_release(root_fd: int) -> tuple[bytes, str, bytes, bytes]:
    manifest_bytes = _read_regular_file_at(
        root_fd,
        _CURRENT_MANIFEST,
        limit=_MANIFEST_LIMIT,
        missing_code="CURRENT_MISSING",
    )
    manifest = _read_json_object(manifest_bytes, code="CURRENT_MANIFEST_INVALID")
    expected_keys = {
        "json_path",
        "json_sha256",
        "markdown_path",
        "markdown_sha256",
        "projection_digest",
        "schema_version",
    }
    projection_digest = manifest.get("projection_digest")
    if not _is_sha256(projection_digest):
        raise PrivateGateFailure("CURRENT_MANIFEST_INVALID", 4)
    expected_json_path = (
        f"aggregate-index-releases/{projection_digest}/aggregate-index.json"
    )
    expected_markdown_path = (
        f"aggregate-index-releases/{projection_digest}/aggregate-index.md"
    )
    if (
        set(manifest) != expected_keys
        or manifest.get("schema_version") != "momcozy-aggregate-release.v1"
        or manifest.get("json_path") != expected_json_path
        or manifest.get("markdown_path") != expected_markdown_path
        or not _is_sha256(manifest.get("json_sha256"))
        or not _is_sha256(manifest.get("markdown_sha256"))
        or _canonical_bytes(manifest) != manifest_bytes
    ):
        raise PrivateGateFailure("CURRENT_MANIFEST_INVALID", 4)
    releases_fd: int | None = None
    release_fd: int | None = None
    try:
        releases_fd = _open_private_directory_at(root_fd, "aggregate-index-releases")
        release_fd = _open_private_directory_at(releases_fd, projection_digest)
        if set(os.listdir(release_fd)) != {"aggregate-index.json", "aggregate-index.md"}:
            raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4)
        json_bytes = _read_regular_file_at(
            release_fd,
            "aggregate-index.json",
            limit=_PROJECTION_LIMIT,
            missing_code="CURRENT_RELEASE_INVALID",
        )
        markdown_bytes = _read_regular_file_at(
            release_fd,
            "aggregate-index.md",
            limit=_PROJECTION_LIMIT,
            missing_code="CURRENT_RELEASE_INVALID",
        )
    except PrivateGateFailure:
        raise
    except OSError as error:
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4) from error
    finally:
        if release_fd is not None:
            os.close(release_fd)
        if releases_fd is not None:
            os.close(releases_fd)
    if (
        _sha256(json_bytes) != manifest["json_sha256"]
        or _sha256(markdown_bytes) != manifest["markdown_sha256"]
    ):
        raise PrivateGateFailure("CURRENT_RELEASE_INVALID", 4)
    _validate_release_projection(json_bytes, markdown_bytes, projection_digest)
    return manifest_bytes, projection_digest, json_bytes, markdown_bytes


def _evaluate_private_gate(
    root: Path, baseline: dict[str, Any]
) -> PrivateGateResult:
    root = Path(root).absolute()
    root_fd = _open_root_directory(root)
    try:
        first = compile_aggregate_index(root)
        if first.status == "blocked":
            raise PrivateGateFailure("FRESH_BLOCKED", 1)
        if _baseline_projection(first.index) != baseline:
            raise PrivateGateFailure("BASELINE_MISMATCH", 1)
        current = _load_current_release(root_fd)
        _, current_digest, json_bytes, markdown_bytes = current
        if (
            current_digest != first.projection_digest
            or json_bytes != first.json_bytes
            or markdown_bytes != first.markdown_bytes
        ):
            raise PrivateGateFailure("CURRENT_STALE", 5)
        second = compile_aggregate_index(root)
        if (
            second.projection_digest != first.projection_digest
            or second.json_bytes != first.json_bytes
            or second.markdown_bytes != first.markdown_bytes
        ):
            raise PrivateGateFailure("SOURCE_CHANGED", 3)
        try:
            final_current = _load_current_release(root_fd)
            path_metadata = os.stat(root, follow_symlinks=False)
        except (OSError, PrivateGateFailure) as error:
            raise PrivateGateFailure("SOURCE_CHANGED", 3) from error
        descriptor_metadata = os.fstat(root_fd)
        if (
            final_current != current
            or path_metadata.st_dev != descriptor_metadata.st_dev
            or path_metadata.st_ino != descriptor_metadata.st_ino
        ):
            raise PrivateGateFailure("SOURCE_CHANGED", 3)
        return PrivateGateResult(
            baseline_id=str(baseline["baseline_id"]),
            state=first.status,
            bundles=int(first.index["counts"]["bundles"]),
        )
    finally:
        os.close(root_fd)


def evaluate_private_gate(root: Path) -> PrivateGateResult:
    """Validate the approved local library against its tracked private baseline."""
    return _evaluate_private_gate(root, _load_baseline())


def main(argv: Sequence[str] | None = None) -> int:
    parser = _SafeArgumentParser(add_help=False)
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_private_gate(args.root)
    except AggregateIndexScopeError:
        print("MOMCOZY_PRIVATE_GATE_FAILED code=UNSAFE_ROOT", file=sys.stderr)
        return 3
    except AggregateIndexSafetyError:
        print("MOMCOZY_PRIVATE_GATE_FAILED code=UNSAFE_PROJECTION", file=sys.stderr)
        return 3
    except AggregateIndexSourceError as error:
        code = (
            "SOURCE_CHANGED"
            if str(error) == "aggregate source changed during scan"
            else "INVALID_SOURCE"
        )
        print(f"MOMCOZY_PRIVATE_GATE_FAILED code={code}", file=sys.stderr)
        return 3
    except PrivateGateFailure as error:
        print(f"MOMCOZY_PRIVATE_GATE_FAILED code={error.code}", file=sys.stderr)
        return error.exit_code
    except (OSError, UnicodeDecodeError, KeyError, TypeError, ValueError):
        print("MOMCOZY_PRIVATE_GATE_FAILED code=IO_FAILURE", file=sys.stderr)
        return 3
    print(
        "MOMCOZY_PRIVATE_GATE_OK "
        f"baseline={result.baseline_id} "
        f"state={result.state} "
        f"bundles={result.bundles}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
