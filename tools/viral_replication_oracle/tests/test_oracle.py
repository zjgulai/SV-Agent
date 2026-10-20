from __future__ import annotations

import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from tools.viral_replication_oracle import oracle as oracle_module
from tools.viral_replication_oracle.__main__ import DEFAULT_FIXTURE_ROOT, main
from tools.viral_replication_oracle.oracle import (
    CLOSED_DISPOSITIONS,
    PRIMARY_MECHANISMS,
    evaluate_fixture,
    run_oracle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = PROJECT_ROOT / ".agents/workflows/viral-replication/fixtures"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def oracle_case(
    *, expected_disposition: str, expected_blockers: list[str]
) -> dict[str, Any]:
    return {
        "fixture_id": "TEST-NARRATIVE",
        "scenario": "synthetic narrative oracle case",
        "oracle_cases": [
            {
                "case_id": "narrative-positive",
                "case_kind": "positive",
                "primary_mechanism": "narrative-transformation",
                "reference": {
                    "source_identity": "resolved",
                    "source_digest": "present",
                    "playability": "reproducible",
                    "rights_state": "analysis_and_adaptation_confirmed",
                },
                "routing": {
                    "candidate_mechanisms": ["narrative-transformation"],
                    "declared_primary": "narrative-transformation",
                },
                "contract": {
                    "changed_dimensions": ["narrative_arc"],
                    "declared_changed_dimension": "narrative_arc",
                    "facts_state": "confirmed_locked_only",
                    "rights_state": "confirmed",
                    "narrative_arc_state": "problem_intervention_result_bound",
                },
                "expected": {
                    "disposition": expected_disposition,
                    "blockers": expected_blockers,
                },
            }
        ],
    }


class FixtureOracleTests(unittest.TestCase):
    def test_json_readability_and_schema_failures_are_separate(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root / "broken.json"
            broken.write_text("{", encoding="utf-8")

            result = evaluate_fixture(broken)

            self.assertFalse(result.json_readable)
            self.assertFalse(result.schema_valid)
            self.assertEqual(
                [failure.code for failure in result.failures], ["JSON_NOT_READABLE"]
            )
            self.assertEqual(result.expectation_total, 0)

    def test_disposition_is_a_closed_schema_value(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            write_json(
                path, oracle_case(expected_disposition="ship", expected_blockers=[])
            )

            result = evaluate_fixture(path)

            self.assertTrue(result.json_readable)
            self.assertFalse(result.schema_valid)
            self.assertEqual(
                [failure.code for failure in result.failures],
                ["EXPECTED_DISPOSITION_INVALID"],
            )
            self.assertEqual(
                CLOSED_DISPOSITIONS,
                frozenset({"blocked", "proceed_with_limits", "ready_for_next_gate"}),
            )

    def test_workflow_expectation_is_derived_instead_of_echoed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            write_json(
                path,
                oracle_case(
                    expected_disposition="blocked",
                    expected_blockers=["invented_failure"],
                ),
            )

            result = evaluate_fixture(path)

            self.assertTrue(result.schema_valid)
            self.assertEqual(result.expectation_total, 1)
            self.assertEqual(result.expectation_passed, 0)
            self.assertEqual(
                [failure.code for failure in result.failures],
                [
                    "EXPECTATION_DISPOSITION_MISMATCH",
                    "EXPECTATION_FAILURE_CODES_MISMATCH",
                ],
            )

    def test_legacy_adapter_derives_codes_from_fixture_input(self) -> None:
        source = FIXTURE_ROOT / "VR-P3-001-reference-source-unstable.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["expected"]["blockers"] = ["source_digest_missing"]

        with TemporaryDirectory() as directory:
            path = Path(directory) / source.name
            write_json(path, payload)

            result = evaluate_fixture(path)

            self.assertTrue(result.schema_valid)
            self.assertEqual(result.expectation_total, 1)
            self.assertEqual(result.expectation_passed, 0)
            self.assertEqual(
                [failure.code for failure in result.failures],
                ["EXPECTATION_FAILURE_CODES_MISMATCH"],
            )

    def test_malformed_legacy_shape_is_a_stable_schema_failure(self) -> None:
        source = FIXTURE_ROOT / "VR-P3-001-reference-source-unstable.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["reference_bundle"] = []

        with TemporaryDirectory() as directory:
            path = Path(directory) / "renamed-fixture.json"
            write_json(path, payload)

            result = evaluate_fixture(path)

        self.assertTrue(result.json_readable)
        self.assertFalse(result.schema_valid)
        self.assertEqual(result.expectation_total, 0)
        self.assertEqual(
            [(failure.layer, failure.code) for failure in result.failures],
            [("schema", "LEGACY_FIXTURE_SHAPE_INVALID")],
        )

    def test_legacy_adapter_type_error_is_a_stable_schema_failure(self) -> None:
        source = FIXTURE_ROOT / "VR-P3-001-reference-source-unstable.json"

        def fail_adapter(_payload: object) -> object:
            raise TypeError("synthetic adapter type error")

        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            with patch.dict(
                oracle_module._LEGACY_ADAPTERS, {"VR-P3-001": fail_adapter}
            ):
                result = evaluate_fixture(path)

        self.assertFalse(result.schema_valid)
        self.assertEqual(
            [(failure.layer, failure.code) for failure in result.failures],
            [("schema", "LEGACY_ADAPTER_INPUT_INVALID")],
        )

    def test_cli_reports_malformed_legacy_shape_without_a_traceback(self) -> None:
        source = FIXTURE_ROOT / "VR-P3-001-reference-source-unstable.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["reference_bundle"] = []

        with TemporaryDirectory() as directory:
            write_json(Path(directory) / "bad.json", payload)
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([directory])

        self.assertEqual(exit_code, 1)
        self.assertIn("LEGACY_FIXTURE_SHAPE_INVALID", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_all_repository_fixtures_pass_schema_and_expectation_oracle(self) -> None:
        report = run_oracle(FIXTURE_ROOT)

        self.assertTrue(report.ok, report.render_text())
        self.assertEqual(report.json_readable, report.total_files)
        self.assertEqual(report.schema_valid, report.total_files)
        self.assertEqual(report.expectation_passed, report.expectation_total)
        self.assertGreaterEqual(report.expectation_total, 43)
        rendered = report.render_text()
        self.assertIn(f"fixture_schema={report.total_files}", rendered)
        self.assertNotIn(" schema=", rendered)

    def test_six_mechanisms_cover_positive_ambiguous_and_blocked(self) -> None:
        report = run_oracle(FIXTURE_ROOT)

        self.assertEqual(set(report.coverage), set(PRIMARY_MECHANISMS))
        for mechanism in PRIMARY_MECHANISMS:
            self.assertEqual(
                report.coverage[mechanism],
                frozenset({"positive", "ambiguous", "blocked"}),
            )

    def test_case_kind_counts_only_when_actual_semantics_match(self) -> None:
        scenarios: list[tuple[str, dict[str, Any]]] = []

        positive_is_blocked = oracle_case(
            expected_disposition="blocked",
            expected_blockers=["narrative_arc_incomplete"],
        )
        positive_case = positive_is_blocked["oracle_cases"][0]
        positive_case["contract"]["narrative_arc_state"] = "missing_result_binding"
        scenarios.append(("positive-is-blocked", positive_is_blocked))

        ambiguous_is_ready = oracle_case(
            expected_disposition="ready_for_next_gate", expected_blockers=[]
        )
        ambiguous_is_ready["oracle_cases"][0]["case_kind"] = "ambiguous"
        scenarios.append(("ambiguous-is-ready", ambiguous_is_ready))

        blocked_is_only_ambiguous = oracle_case(
            expected_disposition="blocked",
            expected_blockers=["primary_mechanism_ambiguous"],
        )
        blocked_case = blocked_is_only_ambiguous["oracle_cases"][0]
        blocked_case["case_kind"] = "blocked"
        blocked_case["routing"]["candidate_mechanisms"] = [
            "narrative-transformation",
            "experience-pov",
        ]
        scenarios.append(("blocked-is-only-ambiguous", blocked_is_only_ambiguous))

        for name, payload in scenarios:
            with self.subTest(name=name), TemporaryDirectory() as directory:
                path = Path(directory) / "fixture.json"
                write_json(path, payload)

                result = evaluate_fixture(path)

                self.assertTrue(result.schema_valid)
                self.assertEqual(result.expectation_passed, 1)
                self.assertEqual(result.coverage, set())
                self.assertEqual(
                    [(failure.layer, failure.code) for failure in result.failures],
                    [("coverage", "CASE_KIND_SEMANTICS_MISMATCH")],
                )

    def test_coverage_failure_uses_stable_code(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "only-one.json",
                oracle_case(
                    expected_disposition="ready_for_next_gate", expected_blockers=[]
                ),
            )

            report = run_oracle(root)

            self.assertFalse(report.ok)
            self.assertIn(
                "COVERAGE_MISSING", [failure.code for failure in report.failures]
            )

    def test_root_failures_are_distinct_and_do_not_masquerade_as_coverage(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing"
            regular_file = root / "fixture.json"
            regular_file.write_text("{}", encoding="utf-8")
            empty = root / "empty"
            empty.mkdir()

            cases = (
                (missing, "FIXTURE_ROOT_NOT_FOUND"),
                (regular_file, "FIXTURE_ROOT_NOT_DIRECTORY"),
                (empty, "FIXTURE_ROOT_NO_JSON"),
            )
            for fixture_root, expected_code in cases:
                with self.subTest(expected_code=expected_code):
                    report = run_oracle(fixture_root)
                    self.assertFalse(report.ok)
                    self.assertEqual(
                        [(failure.layer, failure.code) for failure in report.failures],
                        [("root", expected_code)],
                    )

    def test_default_fixture_root_is_cwd_independent(self) -> None:
        self.assertTrue(DEFAULT_FIXTURE_ROOT.is_absolute())
        self.assertTrue(DEFAULT_FIXTURE_ROOT.is_dir())

        previous_cwd = Path.cwd()
        with TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                output = StringIO()
                with redirect_stdout(output):
                    exit_code = main([])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIn("result=pass", output.getvalue())


if __name__ == "__main__":
    unittest.main()
