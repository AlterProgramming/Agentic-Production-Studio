#!/usr/bin/env python3
"""Initialize an isolated four-condition Progressive Design experiment from blank source states."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

FAMILY_CHOICES = ("content-led", "transactional", "expressive")
CONDITIONS = (
    ("A", "control", "A-control"),
    ("B", "progressive", "B-progressive"),
    ("C", "spatial", "C-spatial"),
    ("D", "reconciled", "D-reconciled"),
)
REQUIRED_EVIDENCE = (
    "desktop-primary",
    "desktop-secondary",
    "mobile-primary",
    "mobile-interaction",
    "route-validation",
    "link-validation",
    "application-state-validation",
    "responsive-overflow-check",
    "keyboard-focus-check",
    "contrast-legibility-review",
    "reduced-motion-review",
    "frozen-content-fidelity-note",
    "blank-state-isolation-receipt",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Parent directory for the run")
    parser.add_argument("--experiment-id", required=True, help="Lowercase kebab-case identifier")
    parser.add_argument("--family", choices=FAMILY_CHOICES, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--brief", type=Path, required=True, help="Frozen Markdown brief")
    parser.add_argument(
        "--budget",
        default="one bounded implementation pass",
        help="Equal implementation budget recorded for each condition",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", args.experiment_id):
        raise SystemExit("--experiment-id must be 3-64 lowercase kebab-case characters")
    if not args.brief.is_file():
        raise SystemExit(f"Frozen brief not found: {args.brief}")

    run_dir = args.root.resolve() / args.experiment_id
    if run_dir.exists():
        raise SystemExit(f"Refusing to overwrite existing run: {run_dir}")

    run_dir.mkdir(parents=True)
    frozen_brief = run_dir / "FROZEN_BRIEF.md"
    shutil.copyfile(args.brief, frozen_brief)

    for relative in (
        "fixtures/content",
        "fixtures/images",
        "comparisons",
        "evaluation",
        "receipts",
    ):
        (run_dir / relative).mkdir(parents=True)

    condition_entries = []
    for condition_id, name, dirname in CONDITIONS:
        condition_root = run_dir / "conditions" / dirname
        source = condition_root / "source"
        evidence = condition_root / "evidence"
        source.mkdir(parents=True)
        evidence.mkdir(parents=True)

        source_entries = list(source.iterdir())
        if source_entries:
            raise SystemExit(f"Condition source was not empty at initialization: {source}")

        prompt_path = condition_root / "PROMPT.md"
        prompt_path.write_text(
            f"# Condition {condition_id} — {name}\n\n"
            "Begin from the empty `source/` directory. Use the repository's "
            "`benchmarks/progressive-design/FRESH_SESSION_PROMPT.md` with this condition assignment.\n",
            encoding="utf-8",
        )
        receipt = {
            "source_empty_at_initialization": True,
            "source_initial_entries": [],
            "existing_implementation_provided": False,
            "starter_design_provided": False,
            "shared_code": False,
            "prior_output_exposure": False,
            "implementation_budget": args.budget,
            "environment_differences": [],
        }
        write_json(condition_root / "isolation-receipt.json", receipt)
        condition_entries.append(
            {
                "id": condition_id,
                "name": name,
                "source_path": str(source.relative_to(run_dir)),
                "evidence_path": str(evidence.relative_to(run_dir)),
                "prompt_path": str(prompt_path.relative_to(run_dir)),
                "isolation_receipt": {
                    "source_empty_at_initialization": True,
                    "shared_code": False,
                    "prior_output_exposure": False,
                    "implementation_budget": args.budget,
                },
            }
        )

    write_json(run_dir / "fixtures" / "route-contract.json", {"routes": [], "states": []})
    write_json(run_dir / "evaluation" / "blind-order.json", {"order": [], "mapping_sealed": True})
    write_json(run_dir / "evaluation" / "scores.json", {"evaluations": [], "overall_preference": None})
    (run_dir / "evaluation" / "observations.md").write_text("# Blind observations\n", encoding="utf-8")
    (run_dir / "evaluation" / "decision.md").write_text("# Experiment decision\n", encoding="utf-8")

    manifest = {
        "version": "1.1",
        "experiment_id": args.experiment_id,
        "task_family": args.family,
        "title": args.title,
        "blank_state": {
            "existing_implementation_provided": False,
            "starter_design_provided": False,
            "prior_condition_source_allowed": False,
            "shared_visual_system_allowed": False,
        },
        "frozen_brief": {
            "path": "FROZEN_BRIEF.md",
            "sha256": sha256(frozen_brief),
            "frozen_at": datetime.now(timezone.utc).isoformat(),
        },
        "conditions": condition_entries,
        "required_evidence": list(REQUIRED_EVIDENCE),
        "evaluation": {
            "blind_order_path": "evaluation/blind-order.json",
            "scores_path": "evaluation/scores.json",
            "observations_path": "evaluation/observations.md",
            "decision_path": "evaluation/decision.md",
            "overall_preference_separate": True,
        },
        "validation_boundary": {
            "browser_engine": False,
            "static": False,
            "application_state": False,
            "limitations": [],
        },
    }
    write_json(run_dir / "experiment.json", manifest)
    write_json(
        run_dir / "receipts" / "initialization.json",
        {
            "experiment_id": args.experiment_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "frozen_brief_sha256": manifest["frozen_brief"]["sha256"],
            "blank_state": True,
            "condition_sources_empty": True,
            "conditions": [condition_id for condition_id, _, _ in CONDITIONS],
        },
    )

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
