from __future__ import annotations

import argparse
import json
from pathlib import Path

from objectforge.delivery_scope1 import build_asset, build_scope1
from objectforge.planning.planner import Scope1Planner


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ObjectForge Scope 1 grammar-driven detailed assets.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--family", choices=["all", "lamp", "case", "table"], default="all")
    parser.add_argument("--variant")
    args = parser.parse_args()
    if args.family == "all":
        result = build_scope1(args.output)
    else:
        if not args.variant:
            raise SystemExit("--variant is required when --family is not all")
        result = build_asset(Scope1Planner.resolve(args.family, args.variant), args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
