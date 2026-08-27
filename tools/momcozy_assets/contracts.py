from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_ASSET_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_EXTENSIONS = {".mp4"}
_RECIPE_FIELDS = {
    "asset_id",
    "asset_type",
    "model",
    "aspect_ratio",
    "resolution",
    "quote_credits",
    "credit_before",
    "credit_after",
    "observed_at",
    "prompt_sha256",
    "config",
    "config_sha256",
    "terminal_state",
}
_PROVENANCE_FIELDS = {
    "task_id_hash",
    "product_source_url",
    "reference_asset_sha256",
}
_QA_HEADINGS = (
    "## Product identity",
    "## Text and claims",
    "## Technical check",
    "## Commercial disposition",
)
_FORBIDDEN_PROVENANCE_KEYS = {
    "authorization",
    "cookie",
    "email",
    "headers",
    "password",
    "phone",
    "raw_task_id",
    "signed_url",
    "task_id",
    "token",
}
_HEX_64 = re.compile(r"[0-9a-f]{64}")


def canonical_json_digest(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append(f"invalid JSON: {label}")
        return None
    if not isinstance(content, dict):
        errors.append(f"JSON object required: {label}")
        return None
    return content


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and _HEX_64.fullmatch(value) is not None


def _find_forbidden_provenance_key(value: object) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).casefold()
            if normalized in _FORBIDDEN_PROVENANCE_KEYS:
                return str(key)
            nested_key = _find_forbidden_provenance_key(nested)
            if nested_key is not None:
                return nested_key
    elif isinstance(value, list):
        for nested in value:
            nested_key = _find_forbidden_provenance_key(nested)
            if nested_key is not None:
                return nested_key
    return None


def _validate_recipe(recipe: dict[str, Any], bundle: Path, asset: Path, errors: list[str]) -> None:
    for field in sorted(_RECIPE_FIELDS):
        if field not in recipe:
            errors.append(f"missing recipe field: {field}")
    if errors:
        return
    if recipe["asset_id"] != bundle.name:
        errors.append("recipe asset_id must match bundle directory")
    asset_type = recipe["asset_type"]
    if asset_type not in {"image", "video"}:
        errors.append("recipe asset_type must be image or video")
    elif asset_type == "image" and asset.suffix.lower() not in _IMAGE_EXTENSIONS:
        errors.append("image recipe requires image asset")
    elif asset_type == "video" and asset.suffix.lower() not in _VIDEO_EXTENSIONS:
        errors.append("video recipe requires MP4 asset")
    if not isinstance(recipe["model"], str) or not recipe["model"].strip():
        errors.append("recipe model must be a non-empty string")
    for field in ("quote_credits", "credit_before", "credit_after"):
        if not isinstance(recipe[field], int) or isinstance(recipe[field], bool):
            errors.append(f"recipe {field} must be an integer")
    if all(isinstance(recipe[field], int) and not isinstance(recipe[field], bool) for field in ("quote_credits", "credit_before", "credit_after")):
        if recipe["quote_credits"] < 0:
            errors.append("recipe quote_credits must be non-negative")
        if recipe["credit_before"] - recipe["credit_after"] != recipe["quote_credits"]:
            errors.append("recipe credit delta must equal quote_credits")
    if not isinstance(recipe["observed_at"], str) or not recipe["observed_at"].strip():
        errors.append("recipe observed_at must be a non-empty string")
    if recipe["terminal_state"] != "completed":
        errors.append("recipe terminal_state must be completed")
    if not _is_digest(recipe["prompt_sha256"]):
        errors.append("recipe prompt_sha256 must be a SHA-256 digest")
    elif recipe["prompt_sha256"] != _file_digest(bundle / "prompt.md"):
        errors.append("recipe prompt_sha256 does not match prompt.md")
    if not _is_digest(recipe["config_sha256"]):
        errors.append("recipe config_sha256 must be a SHA-256 digest")
    elif recipe["config_sha256"] != canonical_json_digest(recipe["config"]):
        errors.append("recipe config_sha256 does not match config")


def _validate_provenance(provenance: dict[str, Any], errors: list[str]) -> None:
    forbidden_key = _find_forbidden_provenance_key(provenance)
    if forbidden_key is not None:
        errors.append(f"forbidden provenance key: {forbidden_key}")
        return
    for field in sorted(_PROVENANCE_FIELDS):
        if field not in provenance:
            errors.append(f"missing provenance field: {field}")
    if errors:
        return
    if not _is_digest(provenance["task_id_hash"]):
        errors.append("provenance task_id_hash must be a SHA-256 digest")
    source_url = provenance["product_source_url"]
    parsed = urlparse(source_url) if isinstance(source_url, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        errors.append("provenance product_source_url must be a public HTTPS URL")
    reference_hashes = provenance["reference_asset_sha256"]
    if not isinstance(reference_hashes, list) or not reference_hashes or not all(_is_digest(item) for item in reference_hashes):
        errors.append("provenance reference_asset_sha256 must be a non-empty digest list")


def _validate_hashes(path: Path, asset: Path, errors: list[str]) -> None:
    expected_line = f"{_file_digest(asset)}  {asset.name}"
    lines = path.read_text(encoding="utf-8").splitlines()
    if expected_line not in lines:
        errors.append("hashes.sha256 must contain the asset SHA-256")


def validate_bundle(bundle: Path) -> list[str]:
    """Return deterministic validation errors for one local commercial asset bundle."""
    errors: list[str] = []
    required_names = ("prompt.md", "recipe.json", "provenance.json", "qa.md", "hashes.sha256")
    for name in required_names:
        if not (bundle / name).is_file():
            errors.append(f"missing required file: {name}")

    assets = sorted(
        path
        for path in bundle.glob("asset.*")
        if path.is_file() and path.suffix.lower() in _ASSET_EXTENSIONS
    )
    if not assets:
        errors.append("missing required file: asset.*")
    elif len(assets) > 1:
        errors.append("exactly one asset.* file is required")
    if len(assets) != 1:
        return errors

    asset = assets[0]
    recipe = (
        _load_json(bundle / "recipe.json", "recipe.json", errors)
        if (bundle / "recipe.json").is_file()
        else None
    )
    provenance = (
        _load_json(bundle / "provenance.json", "provenance.json", errors)
        if (bundle / "provenance.json").is_file()
        else None
    )
    if recipe is not None and (bundle / "prompt.md").is_file():
        _validate_recipe(recipe, bundle, asset, errors)
    if provenance is not None:
        _validate_provenance(provenance, errors)
    if (bundle / "qa.md").is_file():
        qa = (bundle / "qa.md").read_text(encoding="utf-8")
        for heading in _QA_HEADINGS:
            if heading not in qa:
                errors.append(f"missing QA heading: {heading}")
    if (bundle / "hashes.sha256").is_file():
        _validate_hashes(bundle / "hashes.sha256", asset, errors)
    return errors


def find_asset_bundles(root: Path) -> list[Path]:
    """Find bundle directories by their required recipe record."""
    return sorted({path.parent for path in root.rglob("recipe.json")})
