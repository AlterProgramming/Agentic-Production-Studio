from __future__ import annotations

import argparse
import json
from pathlib import Path

from objectforge.delivery_scope3 import build_designed_asset, build_scope3
from objectforge.design.language import design_languages, get_design_language
from objectforge.planning.functional import benchmark_briefs, default_planner


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ObjectForge Scope 3 procedural design-language assets.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--brief", choices=[item.brief_id for item in benchmark_briefs()])
    parser.add_argument("--language", choices=[item.language_id for item in design_languages()])
    args = parser.parse_args()

    if args.brief or args.language:
        if not args.brief or not args.language:
            parser.error("--brief and --language must be supplied together")
        brief = next(item for item in benchmark_briefs() if item.brief_id == args.brief)
        result = build_designed_asset(
            default_planner().plan(brief),
            get_design_language(args.language),
            args.output,
        )
    else:
        result = build_scope3(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
