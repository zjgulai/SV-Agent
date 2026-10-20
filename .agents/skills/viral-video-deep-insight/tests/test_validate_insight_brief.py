from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_insight_brief.py"
FIXTURES = ROOT / "tests" / "fixtures"


def run_fixture(name: str, mutate=None) -> subprocess.CompletedProcess[str]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(data)
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)
        handle.flush()
        return subprocess.run(
            [sys.executable, str(SCRIPT), handle.name],
            text=True,
            capture_output=True,
            check=False,
        )


class ValidateInsightBriefTests(unittest.TestCase):
    def test_valid_brief_passes(self) -> None:
        result = run_fixture("valid-brief.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALID:", result.stdout)

    def test_blocked_ranking_trap_is_a_valid_fail_closed_brief(self) -> None:
        result = run_fixture("blocked-ranking-trap.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALID:", result.stdout)

    def test_observed_zero_alias_is_rejected(self) -> None:
        result = run_fixture(
            "valid-brief.json",
            lambda data: data["observations"][0].update(
                {"availability": "observed_zero", "value": 0}
            ),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("observed_zero", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_conflicting_subject_requires_blocked_status(self) -> None:
        result = run_fixture(
            "valid-brief.json",
            lambda data: data["subject"].update({"binding_state": "conflict"}),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("conflicting subject binding", result.stdout)

    def test_unqualified_winner_claim_is_rejected(self) -> None:
        result = run_fixture(
            "valid-brief.json",
            lambda data: data["inferences"][0].update({"text": "This is the winner."}),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("overclaim", result.stdout)

    def test_malformed_source_refs_returns_invalid_not_traceback(self) -> None:
        result = run_fixture(
            "valid-brief.json",
            lambda data: data.update({"source_refs": [{"ref": "SRC-01"}]}),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_refs must contain non-empty strings", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_metric_unavailable_uses_section_state_instead(self) -> None:
        result = run_fixture(
            "valid-brief.json",
            lambda data: data["observations"][0].update(
                {"availability": "unavailable", "value": None}
            ),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("availability is invalid", result.stdout)

    def test_missing_media_gate_is_rejected(self) -> None:
        result = run_fixture(
            "valid-brief.json",
            lambda data: data.update({"media_gates": data["media_gates"][:-1]}),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing media gates", result.stdout)

    def test_ready_cannot_hide_a_blocked_media_gate(self) -> None:
        def mutate(data):
            data["status"] = "ready_for_next_gate"
            data["media_gates"][0]["state"] = "blocked"

        result = run_fixture("valid-brief.json", mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("blocked or unavailable media gates", result.stdout)

    def test_ready_cannot_use_unresolved_subject(self) -> None:
        def mutate(data):
            data["status"] = "ready_for_next_gate"
            data["subject"]["binding_state"] = "unresolved"

        result = run_fixture("valid-brief.json", mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reviewed subject relation", result.stdout)

    def test_ready_cannot_contain_unsupported_claim(self) -> None:
        def mutate(data):
            data["status"] = "ready_for_next_gate"
            data["claims"][0]["state"] = "unsupported"

        result = run_fixture("valid-brief.json", mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved product claims", result.stdout)

    def test_accepted_claims_must_share_one_product_snapshot(self) -> None:
        def mutate(data):
            data["claims"].append(
                {
                    "id": "CLM-03",
                    "state": "confirmed",
                    "fact_id": "FACT-OTHER",
                    "snapshot_id": "SNAP-OTHER",
                }
            )

        result = run_fixture("valid-brief.json", mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("one Product Snapshot", result.stdout)


if __name__ == "__main__":
    unittest.main()
