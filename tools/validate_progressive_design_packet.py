#!/usr/bin/env python3
"""Validate one sealed Progressive Design implementation packet before launch."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"packet validation failed: {message}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    contract_path = (root / args.contract).resolve()
    try:
        contract_path.relative_to(root)
    except ValueError:
        fail("contract path escapes repository root")
    if not contract_path.is_file():
        fail(f"missing contract: {args.contract}")

    value = json.loads(contract_path.read_text(encoding="utf-8"))
    required = {
        "version",
        "experiment_id",
        "condition_id",
        "condition_name",
        "packet_markdown",
        "launch_prompt",
        "branch",
        "source_path",
        "evidence_path",
        "allowed_read_paths",
        "allowed_write_prefixes",
        "frozen_brief_path",
        "frozen_brief_sha256",
        "contamination_policy",
    }
    missing = sorted(required - set(value))
    if missing:
        fail(f"missing fields: {', '.join(missing)}")
    if value["version"] != "1.0":
        fail("unsupported contract version")
    if not SHA256_RE.fullmatch(value["frozen_brief_sha256"]):
        fail("invalid frozen brief SHA-256")
    if not value["branch"].startswith("agent/"):
        fail("assigned branch must begin with agent/")

    read_paths = value["allowed_read_paths"]
    write_prefixes = value["allowed_write_prefixes"]
    if not isinstance(read_paths, list) or not read_paths or len(read_paths) != len(set(read_paths)):
        fail("allowed_read_paths must be a nonempty unique list")
    if not isinstance(write_prefixes, list) or len(write_prefixes) != 1:
        fail("exactly one write prefix is required")

    own_packet = value["packet_markdown"]
    own_contract = str(args.contract)
    own_launch = value["launch_prompt"]
    for required_path in (own_packet, own_contract, own_launch, value["frozen_brief_path"]):
        if required_path not in read_paths:
            fail(f"required path absent from read allowlist: {required_path}")

    condition_root = str(Path(value["source_path"]).parent)
    if write_prefixes[0].rstrip("/") != condition_root.rstrip("/"):
        fail("write prefix must be the assigned condition root")
    if not value["evidence_path"].startswith(condition_root + "/"):
        fail("evidence path is outside assigned condition root")

    for relative in read_paths:
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            fail(f"read path escapes repository root: {relative}")
        if not path.exists():
            fail(f"allowed read path does not exist: {relative}")

    brief = root / value["frozen_brief_path"]
    if sha256(brief) != value["frozen_brief_sha256"]:
        fail("frozen brief hash mismatch")

    source = root / value["source_path"]
    if not source.is_dir():
        fail("assigned source directory is missing")
    entries = sorted(source.iterdir(), key=lambda item: item.name)
    if [entry.name for entry in entries] != [".gitkeep"]:
        fail("source directory must contain only .gitkeep")
    if not entries[0].is_file() or entries[0].stat().st_size != 0:
        fail(".gitkeep must be a zero-byte regular file")

    launch_text = (root / own_launch).read_text(encoding="utf-8")
    if own_packet not in launch_text or value["branch"] not in launch_text:
        fail("launch prompt does not bind its own packet and branch")
    forbidden_markers = value.get("forbidden_launch_markers", [])
    found = [marker for marker in forbidden_markers if marker and marker in launch_text]
    if found:
        fail(f"launch prompt leaks unassigned markers: {found}")

    policy = value["contamination_policy"]
    if policy.get("exclusion_only_references_count_as_contamination") is not False:
        fail("contamination policy must exempt exclusion-only references")
    if not policy.get("abort_on_operative_unassigned_material"):
        fail("contamination policy must abort on operative unassigned material")

    print(json.dumps({
        "status": "valid",
        "experiment_id": value["experiment_id"],
        "condition_id": value["condition_id"],
        "packet": own_packet,
        "source_empty": True,
        "frozen_brief_sha256": value["frozen_brief_sha256"],
        "write_prefix": write_prefixes[0],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
