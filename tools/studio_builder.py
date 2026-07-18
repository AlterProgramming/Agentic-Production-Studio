#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio_builder import BuilderError, StudioBuilder, load_plan  # noqa: E402


def render_preview(report: dict) -> str:
    lines = [
        f"Plan: {report['plan_id']}",
        f"Operations: {report['summary']['operations']}",
        f"Changed files: {report['summary']['changed_files']}",
    ]
    for change in report["changes"]:
        lines.append(f"- {change['action'].upper():6} {change['path']}")
        if change.get("diff"):
            lines.append(change["diff"].rstrip())
    if not report["changes"]:
        lines.append("No workspace changes are required.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan, apply, and verify surgical studio workspace changes")
    parser.add_argument("--root", default=".", help="Workspace root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Preview a plan without mutating the workspace")
    plan_parser.add_argument("plan")
    plan_parser.add_argument("--json", action="store_true")

    apply_parser = subparsers.add_parser("apply", help="Apply a validated plan transactionally")
    apply_parser.add_argument("plan")
    apply_parser.add_argument("--receipt")
    apply_parser.add_argument("--yes", action="store_true", help="Required acknowledgement for mutation")
    apply_parser.add_argument("--json", action="store_true")

    verify_parser = subparsers.add_parser("verify", help="Verify current files against an apply receipt")
    verify_parser.add_argument("receipt")
    verify_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    builder = StudioBuilder(args.root)
    try:
        if args.command == "plan":
            report = builder.preview(load_plan(args.plan))
            print(json.dumps(report, indent=2) if args.json else render_preview(report))
            return 0
        if args.command == "apply":
            if not args.yes:
                raise BuilderError("Apply requires --yes after reviewing the dry-run plan")
            report = builder.apply(load_plan(args.plan), args.receipt)
            output = json.dumps(report, indent=2) if args.json else render_preview(report) + f"\nReceipt: {report['receipt_path']}"
            print(output)
            return 0
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        report = builder.verify_receipt(receipt)
        print(json.dumps(report, indent=2) if args.json else f"Verification: {report['status']}")
        return 0 if report["status"] == "PASS" else 3
    except (BuilderError, OSError, json.JSONDecodeError) as exc:
        print(f"studio-builder: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
