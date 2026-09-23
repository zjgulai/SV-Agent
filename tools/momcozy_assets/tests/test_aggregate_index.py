from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from tools.momcozy_assets.aggregate_index import (
        AggregateIndexSafetyError,
        AggregateIndexScopeError,
        AggregateIndexSourceError,
        compile_aggregate_index,
    )
except ModuleNotFoundError:
    AggregateIndexScopeError = None
    AggregateIndexSafetyError = None
    AggregateIndexSourceError = None
    compile_aggregate_index = None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _approve_root(root: Path) -> None:
    (root / ".momcozy-aggregate-scope.json").write_text(
        json.dumps(
            {
                "brand_workspace": "momcozy",
                "schema_version": "momcozy-aggregate-scope.v1",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _compile(root: Path):
    _approve_root(root)
    return compile_aggregate_index(root)


def _write_bundle(
    bundle: Path,
    *,
    disposition: str = "approved",
    asset_bytes: bytes = b"aggregate asset fixture",
) -> None:
    bundle.mkdir(parents=True)
    asset = bundle / "asset.png"
    asset.write_bytes(asset_bytes)
    prompt = "Sensitive prompt body that must not be projected.\n"
    (bundle / "prompt.md").write_text(prompt, encoding="utf-8")
    config = {
        "aspect_ratio": "1:1",
        "model": "GPT Image-2",
        "resolution": "1K",
    }
    (bundle / "recipe.json").write_text(
        json.dumps(
            {
                "asset_id": bundle.name,
                "asset_type": "image",
                "model": "GPT Image-2",
                "aspect_ratio": "1:1",
                "resolution": "1K",
                "quote_credits": 2,
                "credit_before": 2,
                "credit_after": 0,
                "observed_at": "2026-08-30T00:00:00Z",
                "prompt_sha256": _sha256(prompt.encode()),
                "config": config,
                "config_sha256": _sha256(
                    json.dumps(
                        config,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode()
                ),
                "terminal_state": "completed",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle / "provenance.json").write_text(
        json.dumps(
            {
                "task_id_hash": _sha256(b"private task identity"),
                "product_source_url": "https://momcozy.com/products/m5-smart",
                "reference_asset_sha256": [_sha256(b"reference")],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle / "qa.md").write_text(
        "## Product identity\npass\n"
        "## Text and claims\npass\n"
        "## Technical check\npass\n"
        f"## Commercial disposition\n{disposition}\n",
        encoding="utf-8",
    )
    (bundle / "hashes.sha256").write_text(
        f"{_sha256(asset_bytes)}  asset.png\n",
        encoding="utf-8",
    )


def _set_batch_id(bundle: Path, batch_id: str) -> None:
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["config"]["batch_id"] = batch_id
    recipe["config_sha256"] = _sha256(
        json.dumps(
            recipe["config"],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    )
    recipe_path.write_text(json.dumps(recipe, sort_keys=True), encoding="utf-8")


def _current_release(root: Path) -> tuple[dict[str, object], bytes, bytes]:
    manifest = json.loads((root / "aggregate-index-current.json").read_text(encoding="utf-8"))
    json_path = root / str(manifest["json_path"])
    markdown_path = root / str(manifest["markdown_path"])
    return manifest, json_path.read_bytes(), markdown_path.read_bytes()


class AggregateIndexTests(unittest.TestCase):
    def test_compile_projects_one_valid_bundle_without_source_text(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "safe-bundle")

            compilation = _compile(root)

            self.assertEqual(compilation.index["counts"]["bundles"], 1)
            self.assertEqual(compilation.index["counts"]["valid"], 1)
            self.assertEqual(
                compilation.index["entries"][0]["commercial_disposition"],
                "approved",
            )
            self.assertEqual(
                compilation.index["entries"][0]["commercial_approval"],
                {"availability": "unknown"},
            )
            self.assertEqual(
                compilation.index["coverage"]["commercial_approval"],
                {"known": 0, "unknown": 1},
            )
            self.assertIn(
                "COMMERCIAL_APPROVAL_UNAVAILABLE",
                compilation.index["limitations"],
            )
            self.assertNotIn(b"Sensitive prompt body", compilation.json_bytes)
            self.assertNotIn(b"private task identity", compilation.json_bytes)
            self.assertNotIn(b"momcozy.com", compilation.json_bytes)
            self.assertNotIn(str(root).encode(), compilation.json_bytes)

    def test_compile_is_independent_of_bundle_creation_order(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_root = Path(first).resolve()
            second_root = Path(second).resolve()
            _write_bundle(first_root / "bundle-b", disposition="hold", asset_bytes=b"b")
            _write_bundle(first_root / "bundle-a", asset_bytes=b"a")
            _write_bundle(second_root / "bundle-a", asset_bytes=b"a")
            _write_bundle(second_root / "bundle-b", disposition="hold", asset_bytes=b"b")

            first_compilation = _compile(first_root)
            second_compilation = _compile(second_root)

            self.assertEqual(first_compilation.json_bytes, second_compilation.json_bytes)
            self.assertEqual(first_compilation.markdown_bytes, second_compilation.markdown_bytes)
            self.assertEqual(
                first_compilation.projection_digest,
                second_compilation.projection_digest,
            )

    def test_compile_digest_changes_when_bundle_evidence_changes(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "bundle-a"
            _write_bundle(bundle)
            first = _compile(root)
            first_record_digest = first.index["entries"][0]["bundle_record_digest"]
            with (bundle / "qa.md").open("a", encoding="utf-8") as stream:
                stream.write("Reviewer note changed without changing the disposition.\n")

            second = _compile(root)

            self.assertNotEqual(
                first_record_digest,
                second.index["entries"][0]["bundle_record_digest"],
            )
            self.assertNotEqual(first.projection_digest, second.projection_digest)
            self.assertEqual(
                second.index["entries"][0]["commercial_disposition"],
                "approved",
            )

    def test_compile_keeps_commercial_dispositions_distinct(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for number, disposition in enumerate(
                ("approved", "hold", "revision-needed", "rejected", "pending review"),
                start=1,
            ):
                _write_bundle(
                    root / f"bundle-{number}",
                    disposition=disposition,
                    asset_bytes=f"asset-{number}".encode(),
                )

            compilation = _compile(root)

            self.assertEqual(
                compilation.index["distributions"]["commercial_disposition"],
                {
                    "approved": 1,
                    "hold": 1,
                    "missing": 0,
                    "rejected": 1,
                    "revision_needed": 1,
                    "unknown": 1,
                },
            )

    def test_compile_quarantines_bundle_candidate_with_missing_recipe(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "incomplete-bundle"
            _write_bundle(bundle)
            (bundle / "recipe.json").unlink()

            compilation = _compile(root)

            self.assertEqual(compilation.status, "blocked")
            self.assertEqual(compilation.index["counts"]["bundles"], 1)
            self.assertEqual(compilation.index["counts"]["quarantined"], 1)
            self.assertEqual(
                compilation.index["findings"][0]["code"],
                "BUNDLE_REQUIRED_FILE_MISSING",
            )
            self.assertEqual(
                compilation.index["entries"][0]["commercial_disposition"],
                "approved",
            )

    def test_compile_blocks_duplicate_bundle_identity(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "first" / "same-bundle")
            _write_bundle(root / "second" / "same-bundle")

            compilation = _compile(root)

            self.assertEqual(compilation.status, "blocked")
            self.assertIn(
                "BUNDLE_ID_DUPLICATE",
                {finding["code"] for finding in compilation.index["findings"]},
            )

    def test_compile_reports_reused_artifact_without_blocking(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a", asset_bytes=b"same-artifact")
            _write_bundle(root / "bundle-b", asset_bytes=b"same-artifact")

            compilation = _compile(root)

            self.assertEqual(compilation.status, "partial")
            finding = next(
                item
                for item in compilation.index["findings"]
                if item["code"] == "ARTIFACT_HASH_REUSED"
            )
            self.assertEqual(finding["severity"], "warning")

    def test_compile_reconciles_supported_scoped_library_index(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a", asset_bytes=b"asset-a")
            _write_bundle(root / "bundle-b", asset_bytes=b"asset-b")
            (root / "library-index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "momcozy-local-library.v1",
                        "batch_id": "E-A",
                        "index_scope": "fixture scope",
                        "product": "Momcozy M5 Smart",
                        "entries": [
                            {
                                "asset_id": "bundle-a",
                                "type": "image",
                                "aspect_ratio": "1:1",
                                "intended_channel": "PDP",
                                "status": "approved",
                                "relative_asset_path": "bundle-a/asset.png",
                                "artifact_sha256": _sha256(b"asset-a"),
                                "prompt_sha256": _sha256(
                                    b"Sensitive prompt body that must not be projected.\n"
                                ),
                            }
                        ],
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            compilation = _compile(root)

            entries = {entry["bundle_ref"]: entry for entry in compilation.index["entries"]}
            self.assertEqual(
                entries["bundle-a"]["batch"],
                {"availability": "present", "value": "E-A"},
            )
            self.assertEqual(
                entries["bundle-a"]["channel"],
                {"availability": "present", "value": "PDP"},
            )
            self.assertEqual(
                entries["bundle-b"]["channel"],
                {"availability": "unknown", "value": None},
            )
            self.assertEqual(
                compilation.index["coverage"]["channel"],
                {"known": 1, "unknown": 1},
            )
            self.assertEqual(
                compilation.index["distributions"]["channel"],
                {"PDP": 1, "unknown": 1},
            )
            self.assertEqual(
                compilation.index["distributions"]["batch"],
                {"E-A": 1, "unknown": 1},
            )

    def test_compile_discovers_nested_supported_scoped_library_index(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "batch-a" / "bundle-a", asset_bytes=b"asset-a")
            (root / "batch-a" / "library-index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "momcozy-local-library.v1",
                        "batch_id": "A",
                        "entries": [
                            {
                                "asset_id": "bundle-a",
                                "type": "image",
                                "aspect_ratio": "1:1",
                                "intended_channel": "PDP",
                                "status": "approved",
                                "relative_asset_path": "batch-a/bundle-a/asset.png",
                                "artifact_sha256": _sha256(b"asset-a"),
                                "prompt_sha256": _sha256(
                                    b"Sensitive prompt body that must not be projected.\n"
                                ),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            compilation = _compile(root)

            self.assertEqual(
                compilation.index["entries"][0]["channel"],
                {"availability": "present", "value": "PDP"},
            )

    def test_compile_fails_closed_on_duplicate_or_malformed_scoped_entries(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a")
            index_path = root / "library-index.json"
            for entries in (
                [{"asset_id": "bundle-a"}, {"asset_id": "bundle-a"}],
                [{"status": "approved"}],
            ):
                with self.subTest(entries=entries):
                    index_path.write_text(
                        json.dumps(
                            {
                                "schema_version": "momcozy-local-library.v1",
                                "batch_id": "A",
                                "entries": entries,
                            }
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaises(AggregateIndexSourceError):
                        _compile(root)

    def test_compile_uses_only_supported_media_as_bundle_artifact(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "bundle-a"
            _write_bundle(bundle, asset_bytes=b"supported")
            (bundle / "asset.txt").write_text("unsupported sidecar", encoding="utf-8")

            compilation = _compile(root)

            self.assertEqual(
                compilation.index["entries"][0]["artifact_sha256"],
                _sha256(b"supported"),
            )

    def test_compile_preserves_supported_video_resolution_and_offset_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "bundle-a"
            _write_bundle(bundle)
            recipe_path = bundle / "recipe.json"
            recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
            recipe["resolution"] = "480P"
            recipe["observed_at"] = "2026-08-30T08:15:00-07:00"
            recipe_path.write_text(json.dumps(recipe, sort_keys=True), encoding="utf-8")

            compilation = _compile(root)

            entry = compilation.index["entries"][0]
            self.assertEqual(entry["resolution"], "480P")
            self.assertEqual(entry["observed_at"], "2026-08-30T15:15:00Z")

    def test_compile_reports_unrecognized_recipe_projection_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "bundle-a"
            _write_bundle(bundle)
            recipe_path = bundle / "recipe.json"
            recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
            recipe["resolution"] = "future-resolution"
            recipe_path.write_text(json.dumps(recipe, sort_keys=True), encoding="utf-8")

            compilation = _compile(root)

            self.assertIsNone(compilation.index["entries"][0]["resolution"])
            self.assertIn(
                "UNRECOGNIZED_RECIPE_VALUE",
                {finding["code"] for finding in compilation.index["findings"]},
            )
            self.assertIn("RECIPE_PROJECTION_INCOMPLETE", compilation.index["limitations"])
            self.assertNotIn(b"future-resolution", compilation.json_bytes)

    def test_compile_blocks_scoped_status_conflict(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a", disposition="approved")
            (root / "library-index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "momcozy-local-library.v1",
                        "batch_id": "E-A",
                        "entries": [
                            {
                                "asset_id": "bundle-a",
                                "status": "revision-needed",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            compilation = _compile(root)

            self.assertEqual(compilation.status, "blocked")
            self.assertIn(
                "SCOPED_STATUS_CONFLICT",
                {finding["code"] for finding in compilation.index["findings"]},
            )

    def test_compile_blocks_scoped_hash_conflict_and_missing_reference(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a", asset_bytes=b"actual")
            (root / "library-index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "momcozy-local-library.v1",
                        "batch_id": "E-A",
                        "entries": [
                            {
                                "asset_id": "bundle-a",
                                "status": "approved",
                                "artifact_sha256": _sha256(b"different"),
                            },
                            {
                                "asset_id": "missing-bundle",
                                "status": "approved",
                                "artifact_sha256": _sha256(b"missing"),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            compilation = _compile(root)

            self.assertEqual(compilation.status, "blocked")
            self.assertEqual(
                {finding["code"] for finding in compilation.index["findings"]},
                {"SCOPED_BUNDLE_MISSING", "SCOPED_HASH_CONFLICT"},
            )

    def test_compile_reconciles_ledgers_and_frozen_batch_plan(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "legacy-bundle")
            for variant in ("v01", "v02"):
                bundle = root / f"planned-job-{variant}"
                _write_bundle(bundle, disposition="hold", asset_bytes=variant.encode())
                _set_batch_id(bundle, "F")
            (root / "batch-c-ledger.json").write_text(
                json.dumps(
                    {
                        "batch_id": "C",
                        "assets": [
                            {"asset_id": "legacy-bundle", "qa_status": "approved"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "batch-f-all-credits-plan.json").write_text(
                json.dumps(
                    {
                        "schema_version": "momcozy-image-batch.v1",
                        "batch_id": "F",
                        "jobs": [
                            {
                                "id": "planned-job",
                                "family": "PDP",
                                "aspect": "1:1",
                                "quantity": 2,
                                "prompt": "not projected",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            compilation = _compile(root)

            entries = {entry["bundle_ref"]: entry for entry in compilation.index["entries"]}
            self.assertEqual(
                compilation.index["coverage"]["batch"],
                {"known": 3, "unknown": 0},
            )
            self.assertEqual(
                compilation.index["coverage"]["concept_group"],
                {"known": 2, "unknown": 1},
            )
            self.assertEqual(
                entries["planned-job-v01"]["concept_group"],
                {"availability": "present", "value": "PDP"},
            )
            self.assertNotIn(b"not projected", compilation.json_bytes)

    def test_compile_blocks_ledger_status_conflict(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a", disposition="approved")
            (root / "batch-c-ledger.json").write_text(
                json.dumps(
                    {
                        "batch_id": "C",
                        "assets": [
                            {"asset_id": "bundle-a", "qa_status": "revision-needed"}
                        ],
                    }
                ),
                encoding="utf-8",
            )

            compilation = _compile(root)

            self.assertEqual(compilation.status, "blocked")
            self.assertIn(
                "LEDGER_STATUS_CONFLICT",
                {finding["code"] for finding in compilation.index["findings"]},
            )

    def test_compile_fails_closed_on_malformed_batch_sources(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        sources = {
            "batch-a-ledger.json": {
                "schema_version": "unsupported-ledger.v999",
                "batch_id": "A",
                "assets": [{"asset_id": "bundle-a", "qa_status": "approved"}],
            },
            "batch-f-plan.json": {
                "schema_version": "momcozy-asset-batch.v1",
                "batch_id": "F",
                "jobs": [{"id": "job-a", "quantity": 0}],
            },
        }
        for filename, source in sources.items():
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                _write_bundle(root / "bundle-a")
                (root / filename).write_text(json.dumps(source), encoding="utf-8")

                with self.assertRaises(AggregateIndexSourceError):
                    _compile(root)

    def test_compile_fails_closed_on_sensitive_projected_value(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        self.assertIsNotNone(AggregateIndexSafetyError, "safety error is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a")
            (root / "library-index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "momcozy-local-library.v1",
                        "batch_id": "E-A",
                        "entries": [
                            {
                                "asset_id": "bundle-a",
                                "status": "approved",
                                "intended_channel": (
                                    "https://example.invalid/file?token=secret-sentinel"
                                ),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(AggregateIndexSafetyError) as raised:
                _compile(root)

            self.assertEqual(str(raised.exception), "unsafe aggregate projection")
            self.assertNotIn("secret-sentinel", str(raised.exception))

    def test_compile_fails_closed_on_common_private_identifiers_and_urls(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        unsafe_values = (
            "reviewer-secret@example.com",
            "file:///Users/private/library",
            "review from /Users/private/library",
            "https://example.invalid/object?X-Goog-Signature=secret",
            "review https://example.invalid/object?X-Goog-Signature=secret",
            "from /opt/private-file",
            "path=/etc/passwd",
            "note=file:///Users/private/library",
            "sk_live_private_sentinel",
            "xoxb-" + ("a" * 20),
            "glpat-abcdefghijklmnopqrst",
            "npm_abcdefghijklmnopqrstuvwxyz123456",
            "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXY123456789",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.signature",
        )
        for unsafe_value in unsafe_values:
            with (
                self.subTest(unsafe_value=unsafe_value),
                tempfile.TemporaryDirectory() as directory,
                self.assertRaises(AggregateIndexSafetyError),
            ):
                    root = Path(directory).resolve()
                    _write_bundle(root / "bundle-a")
                    (root / "library-index.json").write_text(
                        json.dumps(
                            {
                                "schema_version": "momcozy-local-library.v1",
                                "batch_id": "A",
                                "entries": [
                                    {
                                        "asset_id": "bundle-a",
                                        "status": "approved",
                                        "intended_channel": unsafe_value,
                                    }
                                ],
                            }
                        ),
                        encoding="utf-8",
                    )

                    _compile(root)

    def test_compile_rejects_symlinked_aggregate_root(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        self.assertIsNotNone(AggregateIndexScopeError, "scope error is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            library = parent / "library"
            _write_bundle(library / "bundle-a")
            symlink = parent / "linked-library"
            symlink.symlink_to(library, target_is_directory=True)

            with self.assertRaises(AggregateIndexScopeError) as raised:
                _compile(symlink)

            self.assertEqual(str(raised.exception), "unsafe aggregate root")

    def test_compile_rejects_symlink_in_aggregate_root_path(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            physical = parent / "physical"
            library = physical / "library"
            _write_bundle(library / "bundle-a")
            linked = parent / "linked"
            linked.symlink_to(physical, target_is_directory=True)

            with self.assertRaises(AggregateIndexScopeError):
                _compile(linked / "library")

    def test_compile_rejects_unapproved_broad_parent_scope(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            approved = parent / "approved-library"
            _write_bundle(approved / "bundle-a")
            _write_bundle(parent / "unrelated-sibling" / "bundle-b")
            _approve_root(approved)

            with self.assertRaises(AggregateIndexScopeError):
                compile_aggregate_index(parent)

    def test_compile_rejects_unsafe_relative_path_segments(self) -> None:
        unsafe_segments = (
            "path=etc",
            "note=file:",
            "token=" + ("xoxb-" + ("a" * 20)),
        )
        for segment in unsafe_segments:
            with self.subTest(segment=segment), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                _write_bundle(root / segment / "bundle-a")

                with self.assertRaises(AggregateIndexSafetyError):
                    _compile(root)

    def test_compile_fails_closed_on_invalid_structured_source(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        self.assertIsNotNone(AggregateIndexSourceError, "source error is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a")
            (root / "library-index.json").write_text("{private-value", encoding="utf-8")

            with self.assertRaises(AggregateIndexSourceError) as raised:
                _compile(root)

            self.assertEqual(str(raised.exception), "invalid aggregate source")
            self.assertNotIn("private-value", str(raised.exception))

    def test_cli_publishes_one_current_immutable_release(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a")
            expected = _compile(root)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.momcozy_assets.aggregate_index",
                    str(root),
                ],
                cwd=Path(__file__).resolve().parents[3],
                check=False,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            manifest, json_bytes, markdown_bytes = _current_release(root)
            self.assertEqual(json_bytes, expected.json_bytes)
            self.assertEqual(markdown_bytes, expected.markdown_bytes)
            self.assertEqual(manifest["projection_digest"], expected.projection_digest)
            self.assertNotIn(str(root).encode(), completed.stdout)

    def test_cli_blocked_build_preserves_current_release(self) -> None:
        self.assertIsNotNone(compile_aggregate_index, "aggregate compiler is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "bundle-a"
            _write_bundle(bundle)
            _approve_root(root)
            command = [
                sys.executable,
                "-m",
                "tools.momcozy_assets.aggregate_index",
                str(root),
            ]
            first = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parents[3],
                check=False,
                capture_output=True,
            )
            self.assertEqual(first.returncode, 0, first.stderr.decode())
            before = _current_release(root)
            (bundle / "recipe.json").unlink()

            blocked = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parents[3],
                check=False,
                capture_output=True,
            )

            self.assertEqual(blocked.returncode, 1, blocked.stderr.decode())
            self.assertIn(b"INDEX_BLOCKED", blocked.stdout)
            self.assertEqual(_current_release(root), before)

    def test_cli_publish_failure_has_stable_error_and_no_current_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _write_bundle(root / "bundle-a")
            _approve_root(root)
            (root / "aggregate-index-current.json").mkdir()

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.momcozy_assets.aggregate_index",
                    str(root),
                ],
                cwd=Path(__file__).resolve().parents[3],
                check=False,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 3)
            self.assertEqual(
                completed.stderr,
                b"INDEX_FAILED code=AGGREGATE_IO_FAILURE\n",
            )
            self.assertNotIn(str(root).encode(), completed.stderr)
            self.assertTrue((root / "aggregate-index-current.json").is_dir())


if __name__ == "__main__":
    unittest.main()
