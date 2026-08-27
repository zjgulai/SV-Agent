from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

try:
    from tools.momcozy_assets.archive_batch import archive_job
    from tools.momcozy_assets.contracts import validate_bundle
except ModuleNotFoundError:
    archive_job = None
    validate_bundle = None

try:
    from tools.momcozy_assets.archive_batch import archive_zip_job
except (ImportError, ModuleNotFoundError):
    archive_zip_job = None


class ArchiveBatchTests(unittest.TestCase):
    def test_archive_job_creates_one_valid_bundle_per_returned_image(self) -> None:
        self.assertIsNotNone(archive_job, "archive module is not implemented")
        self.assertIsNotNone(validate_bundle, "validator module is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "batch_id": "M5-F-test",
                        "credit_before": 6,
                        "quote_per_image": 2,
                        "jobs": [
                            {
                                "id": "IMG-M5-077-detail-collection-3x2",
                                "aspect": "3:2",
                                "quantity": 3,
                                "prompt": "Exact approved product prompt.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            downloaded = []
            for number in range(1, 4):
                path = root / f"download-{number}.png"
                path.write_bytes(f"fixture-{number}".encode())
                downloaded.append(path)

            bundles = archive_job(
                plan_path=plan_path,
                output_root=root / "library",
                job_id="IMG-M5-077-detail-collection-3x2",
                source_paths=downloaded,
                observed_at="2026-08-26T12:00:00-07:00",
                reference_asset_sha256="a" * 64,
            )

            self.assertEqual(
                [bundle.name for bundle in bundles],
                [
                    "IMG-M5-077-detail-collection-3x2-v01",
                    "IMG-M5-077-detail-collection-3x2-v02",
                    "IMG-M5-077-detail-collection-3x2-v03",
                ],
            )
            for bundle in bundles:
                self.assertEqual(validate_bundle(bundle), [])
                self.assertEqual(json.loads((bundle / "recipe.json").read_text())["quote_credits"], 2)
                self.assertEqual(json.loads((bundle / "provenance.json").read_text())["reference_asset_sha256"], ["a" * 64])

    def test_archive_zip_job_extracts_only_expected_image_entries(self) -> None:
        self.assertIsNotNone(archive_zip_job, "ZIP archive support is not implemented")
        self.assertIsNotNone(validate_bundle, "validator module is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "batch_id": "M5-F-test",
                        "credit_before": 4,
                        "quote_per_image": 2,
                        "jobs": [
                            {
                                "id": "IMG-M5-076-detail-control-cup-9x16",
                                "aspect": "9:16",
                                "quantity": 2,
                                "prompt": "Exact approved product prompt.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            archive_path = root / "returned-images.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("GPT Image-2-2.png", b"second")
                archive.writestr("GPT Image-2-1.png", b"first")

            bundles = archive_zip_job(
                plan_path=plan_path,
                output_root=root / "library",
                job_id="IMG-M5-076-detail-control-cup-9x16",
                archive_path=archive_path,
                observed_at="2026-08-26T12:00:00-07:00",
                reference_asset_sha256="b" * 64,
            )

            self.assertEqual([bundle.name for bundle in bundles], [
                "IMG-M5-076-detail-control-cup-9x16-v01",
                "IMG-M5-076-detail-control-cup-9x16-v02",
            ])
            self.assertEqual((bundles[0] / "asset.png").read_bytes(), b"first")
            self.assertEqual((bundles[1] / "asset.png").read_bytes(), b"second")
            for bundle in bundles:
                self.assertEqual(validate_bundle(bundle), [])

    def test_archive_zip_job_rejects_oversized_member_before_writing_bundles(self) -> None:
        self.assertIsNotNone(archive_zip_job, "ZIP archive support is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "batch_id": "M5-F-test",
                        "credit_before": 2,
                        "quote_per_image": 2,
                        "jobs": [
                            {
                                "id": "IMG-M5-076-detail-control-cup-9x16",
                                "aspect": "9:16",
                                "quantity": 1,
                                "prompt": "Exact approved product prompt.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            archive_path = root / "returned-images.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("GPT Image-2-1.png", b"too-large-for-test")

            with (
                patch("tools.momcozy_assets.archive_batch._MAX_ZIP_MEMBER_BYTES", 1),
                self.assertRaisesRegex(ValueError, "member exceeds size limit"),
            ):
                archive_zip_job(
                    plan_path=plan_path,
                    output_root=root / "library",
                    job_id="IMG-M5-076-detail-control-cup-9x16",
                    archive_path=archive_path,
                    observed_at="2026-08-26T12:00:00-07:00",
                    reference_asset_sha256="c" * 64,
                )
            self.assertFalse((root / "library").exists())
