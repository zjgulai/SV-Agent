from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.oumomo_experiments import create_degradations as degradations


class CreateDegradationsTests(unittest.TestCase):
    def test_create_degradations_module_is_available(self) -> None:
        """Deleting the production module must break the public tool contract."""

        self.assertIsNotNone(
            importlib.util.find_spec("tools.oumomo_experiments.create_degradations")
        )

    def test_missing_ffmpeg_returns_unavailable_without_media(self) -> None:
        """Pretending success when ffmpeg is absent must fail this test."""

        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            source = directory / "source.mp4"
            source.write_bytes(b"controlled-source")
            output = directory / "out"

            self.assertTrue(hasattr(degradations, "create_degradations"))
            result = degradations.create_degradations(
                source,
                output,
                ffmpeg_binary="definitely-not-an-ffmpeg-binary",
            )

            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result["reason"], "ffmpeg_unavailable")
            self.assertEqual(list(output.glob("*.mp4")), [])

    def test_generates_six_hashed_controlled_variants(self) -> None:
        """Dropping a required variant, transform parameter or hash must fail."""

        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg unavailable")
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            source = directory / "source.mp4"
            completed = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=160x240:r=12:d=2",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=16000:duration=2",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(source),
                ],
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            output = directory / "out"
            try:
                result = degradations.create_degradations(source, output)
            except NotImplementedError:
                self.fail("controlled degradation generation is not implemented")

            self.assertEqual(result["status"], "completed")
            manifest = json.loads((output / "manifest.json").read_text("utf-8"))
            variants = manifest["variants"]
            self.assertEqual(
                [item["transform_type"] for item in variants],
                [
                    "original",
                    "strong_compression",
                    "wrong_aspect_ratio",
                    "muted",
                    "audio_video_offset",
                    "key_visual_obscured",
                ],
            )
            self.assertEqual(len({item["degradation_id"] for item in variants}), 6)
            self.assertEqual(len({item["source_sha256"] for item in variants}), 1)
            obscured = next(
                item for item in variants if item["transform_type"] == "key_visual_obscured"
            )
            self.assertEqual(obscured["parameters"]["time_range_seconds"], [6.0, 9.0])
            for item in variants:
                self.assertTrue(item["parameters"])
                self.assertEqual(len(item["artifact_sha256"]), 64)
                self.assertTrue((output / item["artifact_file"]).is_file())


if __name__ == "__main__":
    unittest.main()
