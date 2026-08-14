from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/scripts/validate_evidence.py"


def _canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SkillEvidenceValidatorTests(unittest.TestCase):
    def test_validator_script_is_available(self) -> None:
        """Removing the deterministic validator must break Skill acceptance."""

        self.assertTrue(SCRIPT.is_file())

    def _run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(root)],
            capture_output=True,
            check=False,
            shell=False,
            text=True,
            timeout=10,
        )

    def test_accepts_complete_reconciled_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            experiments = root / "experiments"
            experiments.mkdir()
            records = [
                {
                    "confidence": "F",
                    "experiment_id": "Z00",
                    "feature": "baseline",
                    "submit_count": 0,
                    "verdict": "pass",
                },
                {
                    "confidence": "F",
                    "experiment_id": "P01",
                    "feature": "paid",
                    "job_id_hash": "a" * 64,
                    "ledger_delta": -10,
                    "credit_before": 980,
                    "credit_after": 970,
                    "quote_before_submit": 10,
                    "submit_count": 1,
                    "verdict": "pass",
                    "artifact_sha256": "2" * 64,
                },
            ]
            (experiments / "experiment-manifest.jsonl").write_text(
                "".join(json.dumps(item) + "\n" for item in records),
                "utf-8",
            )
            (experiments / "credit-ledger.csv").write_text(
                "experiment_id,observed_at,feature,quote,credit_before,credit_after,delta,terminal_state,notes\n"
                "Z00,2026-08-11T00:00:00Z,baseline,0,980,980,0,completed,baseline\n"
                "P01,2026-08-11T00:01:00Z,paid,10,980,970,-10,succeeded,one submit\n",
                "utf-8",
            )
            (experiments / "job-state-events.jsonl").write_text(
                json.dumps(
                    {
                        "experiment_id": "P01",
                        "job_id_hash": "a" * 64,
                        "state_sequence": ["submitted", "succeeded"],
                        "terminal_state": "succeeded",
                    }
                )
                + "\n",
                "utf-8",
            )
            (root / "artifacts").mkdir()
            (root / "artifacts" / "hashes.csv").write_text(
                "experiment_id,artifact_path,sha256,bytes,mime,duration_seconds,width,height,fps,video_codec,audio_codec\n"
                "P01,outputs/tmp.mp4,2222222222222222222222222222222222222222222222222222222222222222,1234,video/mp4,15.1,720,1280,24,h264,aac\n",
                "utf-8",
            )
            (root / "artifacts" / "scorecards.csv").write_text(
                "experiment_id,identity_consistency,packaging_text,color_logo_consistency,factuality,shot_coherence,audio_intelligibility,technical_quality,overall,method,notes\n"
                "P01,5,5,5,5,5,5,5,5,manual,ok\n",
                "utf-8",
            )

            completed = self._run_validator(root)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("evidence valid", completed.stdout)

    def test_rejects_budget_break_sensitive_fields_and_invalid_job_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            experiments = root / "experiments"
            experiments.mkdir()
            (experiments / "experiment-manifest.jsonl").write_text(
                json.dumps(
                    {
                        "confidence": "high",
                        "credit_after": 1,
                        "credit_before": 1000,
                        "experiment_id": "BAD",
                        "feature": "paid",
                        "job_id_hash": "short",
                        "ledger_delta": -1000,
                        "quote_before_submit": 1000,
                        "raw_job_id": "private-task-id",
                        "submit_count": 1,
                        "verdict": "pass",
                    }
                )
                + "\n",
                "utf-8",
            )
            (experiments / "credit-ledger.csv").write_text(
                "experiment_id,observed_at,feature,quote,credit_before,credit_after,delta,terminal_state,notes\n"
                "BAD,2026-08-11T00:00:00Z,paid,1000,1000,0,-1001,succeeded,bad\n",
                "utf-8",
            )
            (experiments / "job-state-events.jsonl").write_text(
                json.dumps(
                    {
                        "experiment_id": "BAD",
                        "job_id_hash": "short",
                        "state_sequence": ["submitted", "succeeded"],
                        "terminal_state": "succeeded",
                    }
                )
                + "\n",
                "utf-8",
            )
            (root / "artifacts").mkdir()
            (root / "artifacts" / "hashes.csv").write_text(
                "experiment_id,artifact_path,sha256,bytes,mime,duration_seconds,width,height,fps,video_codec,audio_codec\n",
                "utf-8",
            )
            (root / "artifacts" / "scorecards.csv").write_text(
                "experiment_id,identity_consistency,packaging_text,color_logo_consistency,factuality,shot_coherence,audio_intelligibility,technical_quality,overall,method,notes\n",
                "utf-8",
            )

            completed = self._run_validator(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("budget exceeded", completed.stdout)
            self.assertIn("forbidden field: raw_job_id", completed.stdout)
            self.assertIn("job_id_hash must be a 64 character", completed.stdout)
            self.assertIn("credit arithmetic mismatch", completed.stdout)
            self.assertIn("confidence must be one of", completed.stdout)

    def test_accepts_protocol_v2_with_stage_timestamps_and_hash_crosscheck(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            experiments = root / "experiments"
            experiments.mkdir()
            config = {"count": 1, "ratio": "9:16", "resolution": "720P"}
            (experiments / "experiment-manifest.jsonl").write_text(
                json.dumps(
                    {
                        "protocol_version": "v2",
                        "study_id": "study-video-replica",
                        "experiment_id": "V2-A01",
                        "feature": "video-replica",
                        "observed_at": "2026-08-11T10:00:00Z",
                        "single_changed_variable": "reference",
                        "state_sequence": ["submitted", "generating", "succeeded"],
                        "stage_timestamps": [
                            {
                                "state": "submitted",
                                "observed_at": "2026-08-11T10:00:00Z",
                            },
                            {
                                "state": "generating",
                                "observed_at": "2026-08-11T10:00:01Z",
                            },
                            {
                                "state": "succeeded",
                                "observed_at": "2026-08-11T10:00:03Z",
                            },
                        ],
                        "terminal_state": "succeeded",
                    "quote_before_submit": 75,
                    "credit_before": 800,
                    "credit_after": 725,
                    "ledger_delta": -75,
                    "submit_count": 1,
                    "verdict": "pass",
                    "confidence": "F",
                    "job_id_hash": "f" * 64,
                    "config_canonical_json": config,
                    "config_digest": _canonical_digest(config),
                    "artifacts": {
                        "artifact_sha256": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
                    },
                },
                    separators=(",", ":"),
                )
                + "\n",
                "utf-8",
            )
            (experiments / "credit-ledger.csv").write_text(
                "experiment_id,observed_at,feature,quote,credit_before,credit_after,delta,terminal_state,notes\n"
                "V2-A01,2026-08-11T10:00:00Z,video-replica,75,800,725,-75,succeeded,v2 replica\n",
                "utf-8",
            )
            (experiments / "job-state-events.jsonl").write_text(
                json.dumps(
                    {
                        "experiment_id": "V2-A01",
                        "job_id_hash": "f" * 64,
                        "state_sequence": ["submitted", "generating", "succeeded"],
                        "terminal_state": "succeeded",
                    }
                )
                + "\n",
                "utf-8",
            )
            (root / "artifacts").mkdir()
            (root / "artifacts" / "hashes.csv").write_text(
                "experiment_id,artifact_path,sha256,bytes,mime,duration_seconds,width,height,fps,video_codec,audio_codec\n"
                "V2-A01,outputs/fixtures.mp4,deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef,12345,video/mp4,15.1,720,1280,24,h264,aac\n",
                "utf-8",
            )
            (root / "artifacts" / "scorecards.csv").write_text(
                "experiment_id,identity_consistency,packaging_text,color_logo_consistency,factuality,shot_coherence,audio_intelligibility,technical_quality,overall,method,notes\n"
                "V2-A01,4,5,4,5,3,4,4,4,manual,ok\n",
                "utf-8",
            )

            completed = self._run_validator(root)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("evidence valid", completed.stdout)


if __name__ == "__main__":
    unittest.main()
