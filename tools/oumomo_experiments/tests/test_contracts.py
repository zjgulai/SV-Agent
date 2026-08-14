from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.oumomo_experiments.contracts import (
    ExperimentRecord,
    canonical_json_digest,
    validate_record,
)
from tools.oumomo_experiments.record import append_record, ledger_total


class ExperimentContractTests(unittest.TestCase):
    def test_rejects_paid_record_without_quote_and_credit_delta(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "S-B01",
                "feature": "video-script",
                "verdict": "pass",
                "confidence": "F",
                "submit_count": 1,
            }
        )

        self.assertEqual(
            validate_record(record),
            [
                (
                    "paid submission requires quote_before_submit, credit_before, "
                    "credit_after and ledger_delta"
                )
            ],
        )

    def test_rejects_sensitive_fields_and_raw_job_ids(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "Z00",
                "feature": "account-baseline",
                "verdict": "blocked",
                "confidence": "F",
                "cookie": "secret",
                "job_id": "raw-job-id",
            }
        )

        self.assertEqual(
            validate_record(record),
            ["forbidden field: cookie", "raw job_id is forbidden; store job_id_hash"],
        )

    def test_rejects_non_sha256_job_hash(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "S-B01",
                "feature": "video-script",
                "verdict": "pass",
                "confidence": "F",
                "submit_count": 0,
                "job_id_hash": "short",
            }
        )

        self.assertEqual(
            validate_record(record),
            ["job_id_hash must be a 64 character lowercase hexadecimal digest"],
        )

    def test_rejects_unknown_confidence_and_verdict_values(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "Z00",
                "feature": "account-baseline",
                "verdict": "maybe",
                "confidence": "certain",
            }
        )

        self.assertEqual(
            validate_record(record),
            [
                "confidence must be one of: F, I-H, I-M, U, Vendor claim",
                "verdict must be one of: blocked, fail, inconclusive, pass",
            ],
        )

    def test_ledger_total_rejects_more_than_980_points(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.csv"
            path.write_text(
                "experiment_id,quote,delta,balance_after\n"
                "A,500,-500,480\n"
                "B,500,-500,-20\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "980 point budget exceeded"):
                ledger_total(path)

    def test_appends_valid_record_as_canonical_jsonl(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "Z00",
                "feature": "account-baseline",
                "verdict": "pass",
                "confidence": "F",
                "submit_count": 0,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            append_record(path, record)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                '{"confidence": "F", "experiment_id": "Z00", '
                '"feature": "account-baseline", "submit_count": 0, '
                '"verdict": "pass"}\n',
            )

    def test_v2_protocol_requires_contract_fields(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "V2-MISS",
                "feature": "viral-script",
                "verdict": "pass",
                "confidence": "F",
                "protocol_version": "v2",
                "study_id": "S-video-replica",
                "observed_at": "2026-08-11T12:00:00Z",
                "state_sequence": ["submitted", "succeeded"],
                "terminal_state": "succeeded",
                "submit_count": 1,
                "quote_before_submit": 75,
                "credit_before": 800,
                "credit_after": 725,
                "ledger_delta": -75,
                "single_changed_variable": "reference",
                "config_canonical_json": {"count": 1, "ratio": "9:16"},
                "config_digest": canonical_json_digest({"count": 1, "ratio": "9:16"}),
            }
        )

        self.assertEqual(validate_record(record), [])

    def test_v2_protocol_rejects_mismatch_digest(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "V2-BAD",
                "feature": "viral-script",
                "verdict": "fail",
                "confidence": "F",
                "protocol_version": "v2",
                "study_id": "S-video-replica",
                "observed_at": "2026-08-11T12:00:00Z",
                "state_sequence": ["submitted", "succeeded"],
                "terminal_state": "succeeded",
                "submit_count": 1,
                "quote_before_submit": 75,
                "credit_before": 800,
                "credit_after": 725,
                "ledger_delta": -75,
                "single_changed_variable": "reference",
                "config_canonical_json": {"count": 1},
                "config_digest": "0" * 64,
            }
        )

        self.assertIn(
            "config_digest does not match config_canonical_json",
            validate_record(record),
        )

    def test_v2_protocol_missing_protocol_version_with_v2_fields(self) -> None:
        record = ExperimentRecord.from_mapping(
            {
                "experiment_id": "V2-MISSING",
                "feature": "viral-script",
                "verdict": "pass",
                "confidence": "F",
                "observed_at": "2026-08-11T12:00:00Z",
                "single_changed_variable": "reference",
                "state_sequence": ["submitted", "succeeded"],
                "terminal_state": "succeeded",
                "submit_count": 0,
            }
        )

        self.assertEqual(
            validate_record(record),
            ["protocol_version is required when v2 fields are present"],
        )


if __name__ == "__main__":
    unittest.main()
