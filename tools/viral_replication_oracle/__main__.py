from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .oracle import run_oracle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_ROOT = PROJECT_ROOT / ".agents/workflows/viral-replication/fixtures"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate viral-replication synthetic fixtures deterministically."
    )
    parser.add_argument(
        "fixture_root", nargs="?", type=Path, default=DEFAULT_FIXTURE_ROOT
    )
    args = parser.parse_args(argv)
    report = run_oracle(args.fixture_root)
    print(report.render_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
