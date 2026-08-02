from __future__ import annotations

import argparse
import json
from pathlib import Path

from objectforge.delivery_scope4 import build_scope4, build_system_variant
from objectforge.design.language import get_design_language
from objectforge.systems.planner import benchmark_system_brief, default_system_planner


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ObjectForge Scope 4 multi-object coherent systems.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", choices=("field_service", "precision_lab"))
    args = parser.parse_args()
    if args.language:
        plan = default_system_planner().plan(benchmark_system_brief())
        result = build_system_variant(plan, get_design_language(args.language), args.output)
    else:
        result = build_scope4(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
