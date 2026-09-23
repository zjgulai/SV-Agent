from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.momcozy_assets.aggregate_index import (
    _render_markdown,
    compile_aggregate_index,
)
from tools.momcozy_assets.private_gate import (
    PrivateGateFailure,
    _baseline_projection,
    _evaluate_private_gate,
)
from tools.momcozy_assets.tests.test_aggregate_index import (
    _approve_root,
    _set_batch_id,
    _sha256,
    _write_bundle,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _run_module(module: str, root: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", module, str(root)],
        cwd=_PROJECT_ROOT,
        check=False,
        capture_output=True,
    )


def _make_video_bundle(bundle: Path, *, disposition: str) -> None:
    asset_bytes = bundle.name.encode("utf-8")
    _write_bundle(bundle, disposition=disposition, asset_bytes=asset_bytes)
    image = bundle / "asset.png"
    video = bundle / "asset.mp4"
    image.rename(video)
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["asset_type"] = "video"
    recipe["model"] = "Seedance 2.0 Mini"
    recipe["resolution"] = "480P"
    recipe_path.write_text(json.dumps(recipe, sort_keys=True), encoding="utf-8")
    (bundle / "hashes.sha256").write_text(
        f"{_sha256(asset_bytes)}  asset.mp4\n",
        encoding="utf-8",
    )


def _make_approved_library(root: Path) -> None:
    _approve_root(root)
    scoped_entries: list[dict[str, str]] = []
    for number in range(1, 13):
        bundle = root / f"scoped-{number:03d}"
        _write_bundle(bundle, disposition="approved", asset_bytes=bundle.name.encode())
        _set_batch_id(bundle, "E-A")
        scoped_entries.append(
            {
                "asset_id": bundle.name,
                "intended_channel": "PDP",
                "status": "approved",
            }
        )
    for number in range(1, 199):
        disposition = "approved" if number <= 24 else "hold"
        bundle = root / f"planned-v{number:02d}"
        _write_bundle(bundle, disposition=disposition, asset_bytes=bundle.name.encode())
        _set_batch_id(bundle, "F")
    for number in range(1, 26):
        disposition = "hold" if number <= 24 else "rejected"
        bundle = root / f"legacy-{number:03d}"
        _write_bundle(bundle, disposition=disposition, asset_bytes=bundle.name.encode())
        _set_batch_id(bundle, "F")
    for number in range(1, 10):
        disposition = "rejected" if number == 1 else "revision-needed"
        _make_video_bundle(root / f"video-{number:03d}", disposition=disposition)
    (root / "library-index.json").write_text(
        json.dumps(
            {
                "batch_id": "E-A",
                "entries": scoped_entries,
                "schema_version": "momcozy-local-library.v1",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (root / "batch-f-plan.json").write_text(
        json.dumps(
            {
                "batch_id": "F",
                "jobs": [
                    {
                        "family": "pdp_retail",
                        "id": "planned",
                        "quantity": 198,
                    }
                ],
                "schema_version": "momcozy-asset-batch.v1",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _install_mutated_current(root: Path, mutate) -> None:
    current_path = root / "aggregate-index-current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    index = json.loads((root / current["json_path"]).read_text(encoding="utf-8"))
    mutate(index)
    index_without_digest = dict(index)
    del index_without_digest["projection_digest"]
    projection_digest = hashlib.sha256(
        _canonical_json(index_without_digest)
    ).hexdigest()
    index["projection_digest"] = projection_digest
    json_bytes = _canonical_json(index)
    markdown_bytes = _render_markdown(index)
    release = root / "aggregate-index-releases" / projection_digest
    release.mkdir()
    (release / "aggregate-index.json").write_bytes(json_bytes)
    (release / "aggregate-index.md").write_bytes(markdown_bytes)
    current.update(
        {
            "json_path": (
                f"aggregate-index-releases/{projection_digest}/aggregate-index.json"
            ),
            "json_sha256": hashlib.sha256(json_bytes).hexdigest(),
            "markdown_path": (
                f"aggregate-index-releases/{projection_digest}/aggregate-index.md"
            ),
            "markdown_sha256": hashlib.sha256(markdown_bytes).hexdigest(),
            "projection_digest": projection_digest,
        }
    )
    current_path.write_bytes(_canonical_json(current))


def _publish(root: Path) -> None:
    completed = _run_module("tools.momcozy_assets.aggregate_index", root)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.decode())


def _approved_baseline(root: Path) -> dict[str, object]:
    compilation = compile_aggregate_index(root)
    baseline = _baseline_projection(compilation.index)
    baseline["projection_digest"] = compilation.projection_digest
    return baseline


def _assert_gate_failure(
    test: unittest.TestCase,
    root: Path,
    baseline: dict[str, object],
    *,
    code: str,
    exit_code: int,
) -> None:
    with test.assertRaises(PrivateGateFailure) as raised:
        _evaluate_private_gate(root, baseline)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(raised.exception.exit_code, exit_code)


def _assert_safe_cli_failure(
    test: unittest.TestCase,
    completed: subprocess.CompletedProcess[bytes],
    root: Path,
    *,
    code: str,
    exit_code: int,
) -> None:
    test.assertEqual(completed.returncode, exit_code, completed.stderr.decode())
    test.assertEqual(
        completed.stderr,
        f"MOMCOZY_PRIVATE_GATE_FAILED code={code}\n".encode(),
    )
    test.assertEqual(completed.stdout, b"")
    test.assertNotIn(str(root).encode(), completed.stdout + completed.stderr)


class PrivateGateTests(unittest.TestCase):
    def test_approved_current_passes_without_writing_private_library(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            before = _snapshot(root)

            result = _evaluate_private_gate(root, baseline)

            self.assertEqual(
                (result.baseline_id, result.state, result.bundles),
                ("momcozy-m5-v1", "partial", 244),
            )
            self.assertEqual(_snapshot(root), before)

    def test_missing_current_release_fails_closed_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            before = _snapshot(root)

            _assert_gate_failure(
                self, root, baseline, code="CURRENT_MISSING", exit_code=4
            )
            self.assertEqual(_snapshot(root), before)

    def test_stale_current_release_fails_when_bundle_evidence_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            _publish(root)
            with (root / "scoped-001" / "qa.md").open("a", encoding="utf-8") as stream:
                stream.write("Reviewer note changed without changing disposition.\n")
            baseline = _approved_baseline(root)
            before = _snapshot(root)

            _assert_gate_failure(
                self, root, baseline, code="CURRENT_STALE", exit_code=5
            )
            self.assertEqual(_snapshot(root), before)

    def test_self_consistent_inventory_drift_fails_the_fixed_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            for path in (root / "legacy-001").iterdir():
                path.unlink()
            (root / "legacy-001").rmdir()
            _publish(root)
            before = _snapshot(root)

            _assert_gate_failure(
                self, root, baseline, code="BASELINE_MISMATCH", exit_code=1
            )
            self.assertEqual(_snapshot(root), before)

    def test_same_shape_evidence_substitution_fails_the_fixed_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            replacement = b"different approved-looking evidence"
            (root / "scoped-001" / "asset.png").write_bytes(replacement)
            (root / "scoped-001" / "hashes.sha256").write_text(
                f"{_sha256(replacement)}  asset.png\n",
                encoding="utf-8",
            )
            _publish(root)
            before = _snapshot(root)

            _assert_gate_failure(
                self, root, baseline, code="BASELINE_MISMATCH", exit_code=1
            )
            self.assertEqual(_snapshot(root), before)

    def test_blocked_fresh_compile_preserves_the_existing_current_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            (root / "scoped-001" / "recipe.json").unlink()
            before = _snapshot(root)

            _assert_gate_failure(
                self, root, baseline, code="FRESH_BLOCKED", exit_code=1
            )
            self.assertEqual(_snapshot(root), before)

    def test_manifest_with_unexpected_field_is_rejected_without_path_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            manifest_path = root / "aggregate-index-current.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["private_path"] = str(root / "secret")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            before = _snapshot(root)

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_MANIFEST_INVALID",
                exit_code=4,
            )
            self.assertEqual(_snapshot(root), before)

    def test_tampered_release_is_rejected_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            manifest = json.loads(
                (root / "aggregate-index-current.json").read_text(encoding="utf-8")
            )
            release_json = root / manifest["json_path"]
            release_json.write_bytes(release_json.read_bytes() + b"\n")
            before = _snapshot(root)

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )
            self.assertEqual(_snapshot(root), before)

    def test_hash_consistent_malformed_release_is_invalid_not_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            manifest_path = root / "aggregate-index-current.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            malformed = _canonical_json({"not": "an aggregate index"})
            (root / manifest["json_path"]).write_bytes(malformed)
            manifest["json_sha256"] = hashlib.sha256(malformed).hexdigest()
            manifest_path.write_bytes(_canonical_json(manifest))
            before = _snapshot(root)

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )
            self.assertEqual(_snapshot(root), before)

    def test_noncanonical_current_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            manifest_path = root / "aggregate-index-current.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_path.write_text(
                json.dumps(manifest, separators=(",", ":")),
                encoding="utf-8",
            )
            before = _snapshot(root)

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_MANIFEST_INVALID",
                exit_code=4,
            )
            self.assertEqual(_snapshot(root), before)

    def test_self_consistent_invalid_nested_availability_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            _install_mutated_current(
                root,
                lambda index: index["entries"][0]["commercial_approval"].update(
                    {"availability": "present"}
                ),
            )

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )

    def test_self_consistent_sensitive_relative_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            _install_mutated_current(
                root,
                lambda index: index["entries"][0].update(
                    {"relative_path": "/private/secret"}
                ),
            )

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )

    def test_self_consistent_derived_count_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            _install_mutated_current(
                root,
                lambda index: index["counts"].update(
                    {"bundles": index["counts"]["bundles"] + 1}
                ),
            )

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )

    def test_self_consistent_invalid_finding_severity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)

            def add_invalid_finding(index: dict[str, object]) -> None:
                entries = index["entries"]
                findings = index["findings"]
                assert isinstance(entries, list)
                assert isinstance(findings, list)
                findings.append(
                    {
                        "bundle_ref": entries[0]["bundle_ref"],
                        "code": "ARTIFACT_HASH_REUSED",
                        "message": "bounded finding",
                        "severity": "notice",
                    }
                )

            _install_mutated_current(root, add_invalid_finding)

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )

    def test_group_world_writable_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            original_mode = stat.S_IMODE(root.stat().st_mode)
            root.chmod(0o777)
            try:
                _assert_gate_failure(
                    self, root, baseline, code="UNSAFE_ROOT", exit_code=3
                )
            finally:
                root.chmod(original_mode)

    def test_sticky_world_writable_private_directories_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            manifest = json.loads(
                (root / "aggregate-index-current.json").read_text(encoding="utf-8")
            )
            directories = [
                root,
                root / "aggregate-index-releases",
                root / "aggregate-index-releases" / manifest["projection_digest"],
            ]
            for target in directories:
                with self.subTest(target=target.name):
                    original_mode = stat.S_IMODE(target.stat().st_mode)
                    target.chmod(0o1777)
                    try:
                        expected = (
                            "UNSAFE_ROOT"
                            if target == root
                            else "CURRENT_RELEASE_INVALID"
                        )
                        expected_exit = 3 if target == root else 4
                        _assert_gate_failure(
                            self,
                            root,
                            baseline,
                            code=expected,
                            exit_code=expected_exit,
                        )
                    finally:
                        target.chmod(original_mode)

    def test_group_world_writable_release_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            releases = root / "aggregate-index-releases"
            original_mode = stat.S_IMODE(releases.stat().st_mode)
            releases.chmod(0o777)
            try:
                _assert_gate_failure(
                    self,
                    root,
                    baseline,
                    code="CURRENT_RELEASE_INVALID",
                    exit_code=4,
                )
            finally:
                releases.chmod(original_mode)

    def test_hardlinked_release_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            root = parent / "library"
            root.mkdir()
            _make_approved_library(root)
            baseline = _approved_baseline(root)
            _publish(root)
            manifest = json.loads(
                (root / "aggregate-index-current.json").read_text(encoding="utf-8")
            )
            (parent / "linked-release.json").hardlink_to(root / manifest["json_path"])
            before = _snapshot(root)

            _assert_gate_failure(
                self,
                root,
                baseline,
                code="CURRENT_RELEASE_INVALID",
                exit_code=4,
            )
            self.assertEqual(_snapshot(root), before)

    def test_unapproved_root_is_rejected_without_path_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            completed = _run_module("tools.momcozy_assets.private_gate", root)

            _assert_safe_cli_failure(
                self, completed, root, code="UNSAFE_ROOT", exit_code=3
            )

    def test_usage_error_does_not_echo_arguments(self) -> None:
        secret = "/private/momcozy/do-not-echo"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.momcozy_assets.private_gate",
                secret,
                "unexpected",
            ],
            cwd=_PROJECT_ROOT,
            check=False,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(
            completed.stderr,
            b"MOMCOZY_PRIVATE_GATE_FAILED code=USAGE_ERROR\n",
        )
        self.assertEqual(completed.stdout, b"")
        self.assertNotIn(secret.encode(), completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
