from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.oumomo_experiments.media_probe import probe_media


class MediaProbeTests(unittest.TestCase):
    def test_missing_file_returns_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = probe_media(Path(directory) / "missing.mp4")

        self.assertEqual(
            result,
            {"error": "file_not_found", "probe_status": "error"},
        )

    def test_hashes_bytes_and_handles_missing_ffprobe(self) -> None:
        payload = b"oumomo-media-probe-fixture"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.mp4"
            path.write_bytes(payload)
            with patch(
                "tools.oumomo_experiments.media_probe.subprocess.run",
                side_effect=FileNotFoundError,
            ):
                result = probe_media(path)

        self.assertEqual(result["bytes"], len(payload))
        self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(result["probe_status"], "unavailable")
        self.assertEqual(result["probe_error"], "ffprobe_unavailable")
        self.assertNotIn(str(path), repr(result))


if __name__ == "__main__":
    unittest.main()
