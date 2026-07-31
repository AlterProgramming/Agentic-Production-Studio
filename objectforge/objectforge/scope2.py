from __future__ import annotations

import argparse
import json
from pathlib import Path

from objectforge.delivery_scope2 import build_functional_asset, build_scope2
from objectforge.planning.functional import benchmark_briefs, default_planner


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ObjectForge Scope 2 goal-directed functional assets.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--brief", choices=[item.brief_id for item in benchmark_briefs()])
    args = parser.parse_args()
    if args.brief:
        brief = next(item for item in benchmark_briefs() if item.brief_id == args.brief)
        result = build_functional_asset(default_planner().plan(brief), args.output)
    else:
        result = build_scope2(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
