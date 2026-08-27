from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    from tools.momcozy_assets.contracts import validate_bundle
except ModuleNotFoundError:
    validate_bundle = None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_complete_bundle(bundle: Path, *, asset_name: str = "asset.png") -> None:
    bundle.mkdir(parents=True)
    asset = bundle / asset_name
    asset_bytes = b"Momcozy M5 asset fixture"
    asset.write_bytes(asset_bytes)
    prompt = "Create a clean product image of Momcozy M5 Smart.\n"
    prompt_path = bundle / "prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    config = {
        "model": "GPT Image-2",
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "quantity": 1,
    }
    (bundle / "recipe.json").write_text(
        json.dumps(
            {
                "asset_id": bundle.name,
                "asset_type": "image",
                "model": config["model"],
                "aspect_ratio": config["aspect_ratio"],
                "resolution": config["resolution"],
                "quote_credits": 2,
                "credit_before": 668,
                "credit_after": 666,
                "observed_at": "2026-08-15T19:31:35-07:00",
                "prompt_sha256": _sha256(prompt.encode("utf-8")),
                "config": config,
                "config_sha256": _sha256(
                    json.dumps(
                        config,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                ),
                "terminal_state": "completed",
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle / "provenance.json").write_text(
        json.dumps(
            {
                "task_id_hash": _sha256(b"local-task-id"),
                "product_source_url": "https://momcozy.com/products/m5-smart",
                "reference_asset_sha256": [_sha256(b"reference-image")],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle / "qa.md").write_text(
        """## Product identity
pass
## Text and claims
pass
## Technical check
pass
## Commercial disposition
approved
""",
        encoding="utf-8",
    )
    (bundle / "hashes.sha256").write_text(
        f"{_sha256(asset_bytes)}  {asset_name}\n",
        encoding="utf-8",
    )


class AssetBundleContractTests(unittest.TestCase):
    def test_validate_bundle_accepts_complete_image_bundle(self) -> None:
        self.assertIsNotNone(validate_bundle, "validator module is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "IMG-M5-003-app-control-4x5"
            _write_complete_bundle(bundle)

            self.assertEqual(validate_bundle(bundle), [])

    def test_validate_bundle_rejects_missing_prompt_and_raw_task_id(self) -> None:
        self.assertIsNotNone(validate_bundle, "validator module is not implemented")
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "IMG-M5-003-app-control-4x5"
            _write_complete_bundle(bundle)
            (bundle / "prompt.md").unlink()
            (bundle / "provenance.json").write_text(
                '{"task_id":"raw"}',
                encoding="utf-8",
            )

            self.assertEqual(
                validate_bundle(bundle),
                [
                    "missing required file: prompt.md",
                    "forbidden provenance key: task_id",
                ],
            )
