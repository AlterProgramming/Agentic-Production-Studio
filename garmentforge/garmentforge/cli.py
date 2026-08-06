from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fit import install_clearance_pass

install_clearance_pass()

from .construction import build_package
from .validate import validate_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_package(args.output)
    receipt = validate_package(args.output)
    print(json.dumps({"manifest": manifest, "validation": receipt}, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
