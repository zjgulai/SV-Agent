from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        shell=False,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError("ffmpeg_failed")


def create_degradations(
    source: Path,
    output_directory: Path,
    *,
    ffmpeg_binary: str = "ffmpeg",
) -> dict[str, object]:
    if shutil.which(ffmpeg_binary) is None:
        return {"reason": "ffmpeg_unavailable", "status": "unavailable"}
    if not source.is_file():
        return {"reason": "source_not_found", "status": "error"}

    output_directory.mkdir(parents=True, exist_ok=True)
    source_sha256 = _sha256(source)
    variants: list[dict[str, Any]] = []
    specifications: list[tuple[str, str, dict[str, Any], list[str] | None]] = [
        ("D-00", "original", {"operation": "byte_copy"}, None),
        (
            "D-01",
            "strong_compression",
            {"audio_bitrate": "48k", "crf": 40, "preset": "veryfast"},
            ["-c:v", "libx264", "-crf", "40", "-preset", "veryfast", "-c:a", "aac", "-b:a", "48k"],
        ),
        (
            "D-02",
            "wrong_aspect_ratio",
            {"crop": "240x240", "target_ratio": "1:1"},
            [
                "-vf",
                "scale=240:240:force_original_aspect_ratio=increase,crop=240:240",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
            ],
        ),
        ("D-03", "muted", {"audio": "removed"}, ["-c:v", "copy", "-an"]),
        (
            "D-04",
            "audio_video_offset",
            {"audio_offset_seconds": 0.5},
            [
                "-itsoffset",
                "0.5",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
            ],
        ),
        (
            "D-05",
            "key_visual_obscured",
            {"opacity": 0.85, "time_range_seconds": [6.0, 9.0]},
            [
                "-vf",
                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.85:t=fill:enable='between(t,6,9)'",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
            ],
        ),
    ]

    for degradation_id, transform_type, parameters, ffmpeg_arguments in specifications:
        artifact_file = f"{degradation_id}-{transform_type}.mp4"
        artifact_path = output_directory / artifact_file
        if ffmpeg_arguments is None:
            shutil.copy2(source, artifact_path)
        else:
            _run(
                [
                    ffmpeg_binary,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(source),
                    *ffmpeg_arguments,
                    str(artifact_path),
                ]
            )
        variants.append(
            {
                "artifact_file": artifact_file,
                "artifact_sha256": _sha256(artifact_path),
                "degradation_id": degradation_id,
                "parameters": parameters,
                "source_sha256": source_sha256,
                "transform_type": transform_type,
            }
        )

    manifest: dict[str, object] = {
        "source_file": source.name,
        "source_sha256": source_sha256,
        "status": "completed",
        "variants": variants,
    }
    (output_directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    result = create_degradations(arguments.source, arguments.output_directory)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
