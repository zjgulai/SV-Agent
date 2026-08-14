from __future__ import annotations

import csv
import json
from pathlib import Path

from .contracts import ExperimentRecord, validate_record

MAX_CREDIT_SPEND = 980


def append_record(path: Path, record: ExperimentRecord) -> None:
    errors = validate_record(record)
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(record.to_mapping(), ensure_ascii=False, sort_keys=True) + "\n"
        )


def ledger_total(path: Path) -> int:
    total = 0
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            delta = int(row["delta"])
            if delta < 0:
                total += -delta
            if total > MAX_CREDIT_SPEND:
                raise ValueError(f"{MAX_CREDIT_SPEND} point budget exceeded")
    return total
