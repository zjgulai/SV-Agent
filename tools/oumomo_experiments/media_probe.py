from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_media(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"error": "file_not_found", "probe_status": "error"}

    result: dict[str, Any] = {
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration,size,bit_rate:"
            "stream=index,codec_type,codec_name,width,height,r_frame_rate,"
            "sample_rate,channels"
        ),
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return {
            **result,
            "probe_error": "ffprobe_unavailable",
            "probe_status": "unavailable",
        }
    except subprocess.TimeoutExpired:
        return {
            **result,
            "probe_error": "ffprobe_timeout",
            "probe_status": "error",
        }

    if completed.returncode != 0:
        return {
            **result,
            "probe_error": "ffprobe_failed",
            "probe_status": "error",
        }

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            **result,
            "probe_error": "ffprobe_invalid_json",
            "probe_status": "error",
        }
    return {
        **result,
        "format": payload.get("format", {}),
        "probe_status": "ok",
        "streams": payload.get("streams", []),
    }
