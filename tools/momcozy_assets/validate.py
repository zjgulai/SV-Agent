from __future__ import annotations

import argparse
from pathlib import Path

from .contracts import find_asset_bundles, validate_bundle


def validate_library(root: Path) -> list[str]:
    bundles = find_asset_bundles(root)
    if not bundles:
        return ["no asset bundles found"]
    errors: list[str] = []
    for bundle in bundles:
        for error in validate_bundle(bundle):
            errors.append(f"{bundle.relative_to(root)}: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local Momcozy asset bundles")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    errors = validate_library(args.root)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"valid asset bundles: {len(find_asset_bundles(args.root))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
