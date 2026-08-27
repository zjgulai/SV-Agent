"""Archive completed Oumomo image groups as independently auditable asset bundles.

The archive deliberately persists only a deterministic local receipt hash, never a
platform task ID, signed asset URL, account data, or browser session information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import struct
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .contracts import canonical_json_digest

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_PRODUCT_URL = "https://momcozy.com/products/m5-smart-wearable-breast-pump-upgraded-with-app-control"
_TRAILING_NUMBER = re.compile(r"-(\d+)$")
_MAX_ZIP_MEMBER_BYTES = 32 * 1024 * 1024
_MAX_ZIP_TOTAL_BYTES = 128 * 1024 * 1024


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_plan(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("batch plan must be a JSON object")
    return value


def _find_job(plan: dict[str, Any], job_id: str) -> tuple[int, dict[str, Any]]:
    jobs = plan.get("jobs")
    if not isinstance(jobs, list):
        raise TypeError("batch plan jobs must be a list")
    for index, candidate in enumerate(jobs):
        if isinstance(candidate, dict) and candidate.get("id") == job_id:
            return index, candidate
    raise ValueError(f"unknown job_id: {job_id}")


def _image_dimensions(path: Path) -> str:
    """Return dimensions where PNG metadata is available, otherwise preserve unknown."""
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and header[12:16] == b"IHDR":
            width, height = struct.unpack(">II", header[16:24])
            return f"{width} x {height} pixels"
    except OSError:
        pass
    return "dimensions not independently probed"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def archive_job(
    *,
    plan_path: Path,
    output_root: Path,
    job_id: str,
    source_paths: Sequence[Path],
    observed_at: str,
    reference_asset_sha256: str,
) -> list[Path]:
    """Create one complete asset bundle for every returned image of one planned job."""
    plan = _load_plan(plan_path)
    job_index, job = _find_job(plan, job_id)
    quantity = job.get("quantity")
    prompt = job.get("prompt")
    aspect = job.get("aspect")
    if not isinstance(quantity, int) or quantity < 1:
        raise ValueError("job quantity must be a positive integer")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("job prompt must be non-empty")
    if not isinstance(aspect, str) or not aspect.strip():
        raise ValueError("job aspect must be non-empty")
    if len(source_paths) != quantity:
        raise ValueError(f"expected {quantity} returned images, got {len(source_paths)}")
    if len(reference_asset_sha256) != 64:
        raise ValueError("reference_asset_sha256 must be a SHA-256 digest")

    quote_per_image = plan.get("quote_per_image")
    credit_before = plan.get("credit_before")
    batch_id = plan.get("batch_id")
    if not isinstance(quote_per_image, int) or quote_per_image < 0:
        raise ValueError("plan quote_per_image must be a non-negative integer")
    if not isinstance(credit_before, int):
        raise TypeError("plan credit_before must be an integer")
    if not isinstance(batch_id, str) or not batch_id:
        raise ValueError("plan batch_id must be non-empty")

    jobs = plan["jobs"]
    prior_spend = 0
    for prior in jobs[:job_index]:
        if not isinstance(prior, dict) or not isinstance(prior.get("quantity"), int):
            raise TypeError("every earlier job must have an integer quantity")
        prior_spend += prior["quantity"] * quote_per_image
    group_credit_before = credit_before - prior_spend

    bundles: list[Path] = []
    for variant_number, source in enumerate(source_paths, start=1):
        source = Path(source)
        extension = source.suffix.lower()
        if extension not in _IMAGE_EXTENSIONS or not source.is_file():
            raise ValueError(f"source must be an existing supported image: {source.name}")
        asset_id = f"{job_id}-v{variant_number:02d}"
        bundle = output_root / asset_id
        if bundle.exists():
            raise FileExistsError(f"refusing to overwrite existing bundle: {asset_id}")
        bundle.mkdir(parents=True)
        asset_path = bundle / f"asset{extension}"
        shutil.copy2(source, asset_path)

        prompt_content = (
            "# Frozen generation prompt\n\n"
            f"{prompt.strip()}\n\n"
            "# Returned variant\n\n"
            f"Variant {variant_number} of {quantity} returned from the same completed, "
            f"frozen Oumomo generation group `{job_id}`.\n"
        )
        prompt_path = bundle / "prompt.md"
        prompt_path.write_text(prompt_content, encoding="utf-8")

        variant_credit_before = group_credit_before - ((variant_number - 1) * quote_per_image)
        config = {
            "aspect_ratio": aspect,
            "batch_id": batch_id,
            "model": "GPT Image-2",
            "original_group_quantity": quantity,
            "reference_count": 1,
            "resolution": "1K",
            "variant_index": variant_number,
        }
        _write_json(
            bundle / "recipe.json",
            {
                "asset_id": asset_id,
                "asset_type": "image",
                "aspect_ratio": aspect,
                "config": config,
                "config_sha256": canonical_json_digest(config),
                "credit_after": variant_credit_before - quote_per_image,
                "credit_before": variant_credit_before,
                "model": "GPT Image-2",
                "observed_at": observed_at,
                "prompt_sha256": _sha256_file(prompt_path),
                "quote_credits": quote_per_image,
                "resolution": "1K",
                "terminal_state": "completed",
            },
        )
        receipt = {
            "archive_receipt_version": "v1",
            "batch_id": batch_id,
            "job_id": job_id,
            "variant_index": variant_number,
        }
        _write_json(
            bundle / "provenance.json",
            {
                "archive_note": "Completed Oumomo project card; raw platform task identity was not retained.",
                "product_source_url": _PRODUCT_URL,
                "reference_asset_sha256": [reference_asset_sha256],
                "task_id_hash": _sha256_bytes(
                    json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ),
            },
        )
        (bundle / "qa.md").write_text(
            "## Product identity\n\n"
            "Pending visual QA — archive only; confirm M5 pump, transparent cup, cream carry case "
            "and Momcozy wordmark fidelity before commercial use.\n\n"
            "## Text and claims\n\n"
            "Pending visual QA — no generated text, price, promotion, medical, comparison or award claim "
            "is approved for use until reviewed.\n\n"
            "## Technical check\n\n"
            f"Pass — {asset_path.name}, {_image_dimensions(asset_path)}; local SHA-256 is recorded in `hashes.sha256`.\n\n"
            "## Commercial disposition\n\n"
            "hold — source image is archived with its frozen prompt and receipt; require brand and legal review before publication.\n",
            encoding="utf-8",
        )
        (bundle / "hashes.sha256").write_text(
            f"{_sha256_file(asset_path)}  {asset_path.name}\n", encoding="utf-8"
        )
        bundles.append(bundle)
    return bundles


def _zip_entry_sort_key(name: str) -> tuple[int, str]:
    stem = Path(name).stem
    match = _TRAILING_NUMBER.search(stem)
    return (int(match.group(1)) if match else 0, name.casefold())


def archive_zip_job(
    *,
    plan_path: Path,
    output_root: Path,
    job_id: str,
    archive_path: Path,
    observed_at: str,
    reference_asset_sha256: str,
) -> list[Path]:
    """Safely unpack one UI-exported image ZIP and archive its returned variants."""
    plan = _load_plan(plan_path)
    _, job = _find_job(plan, job_id)
    quantity = job.get("quantity")
    if not isinstance(quantity, int) or quantity < 1:
        raise ValueError("job quantity must be a positive integer")

    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = []
            total_size = 0
            for info in archive.infolist():
                entry_path = PurePosixPath(info.filename)
                if info.is_dir() or entry_path.is_absolute() or ".." in entry_path.parts:
                    if not info.is_dir():
                        raise ValueError("ZIP contains an unsafe entry path")
                    continue
                if len(entry_path.parts) != 1 or entry_path.suffix.lower() not in _IMAGE_EXTENSIONS:
                    raise ValueError("ZIP must contain only top-level image files")
                if info.flag_bits & 0x1 or stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("ZIP must contain regular, unencrypted image files")
                if info.file_size > _MAX_ZIP_MEMBER_BYTES:
                    raise ValueError("ZIP member exceeds size limit")
                total_size += info.file_size
                if total_size > _MAX_ZIP_TOTAL_BYTES:
                    raise ValueError("ZIP total exceeds size limit")
                members.append(info)
            members.sort(key=lambda info: _zip_entry_sort_key(info.filename))
            if len(members) != quantity:
                raise ValueError(f"expected {quantity} images in ZIP, got {len(members)}")
            with tempfile.TemporaryDirectory(prefix="momcozy-archive-") as directory:
                extracted: list[Path] = []
                for number, member in enumerate(members, start=1):
                    target = Path(directory) / f"variant-{number:02d}{Path(member.filename).suffix.lower()}"
                    with archive.open(member) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                    extracted.append(target)
                return archive_job(
                    plan_path=plan_path,
                    output_root=output_root,
                    job_id=job_id,
                    source_paths=extracted,
                    observed_at=observed_at,
                    reference_asset_sha256=reference_asset_sha256,
                )
    except zipfile.BadZipFile as error:
        raise ValueError("archive_path must be a readable ZIP") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive one completed Momcozy image job")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", type=Path, action="append")
    source_group.add_argument("--zip", type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--reference-sha256", required=True)
    args = parser.parse_args()
    if args.zip is not None:
        bundles = archive_zip_job(
            plan_path=args.plan,
            output_root=args.output_root,
            job_id=args.job_id,
            archive_path=args.zip,
            observed_at=args.observed_at,
            reference_asset_sha256=args.reference_sha256,
        )
    else:
        bundles = archive_job(
            plan_path=args.plan,
            output_root=args.output_root,
            job_id=args.job_id,
            source_paths=args.source,
            observed_at=args.observed_at,
            reference_asset_sha256=args.reference_sha256,
        )
    print("\n".join(bundle.name for bundle in bundles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
