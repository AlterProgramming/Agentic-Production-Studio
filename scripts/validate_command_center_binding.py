#!/usr/bin/env python3
"""Validate the repository's mandatory Agent Command Center session binding."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / ".agent" / "command-center.json"
AGENTS = ROOT / "AGENTS.md"


def main() -> int:
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(binding.get("schema_version") == "1.0.0", "schema_version must be 1.0.0")
    require(binding.get("kind") == "assistant.command-center-session-binding", "invalid binding kind")
    require(binding.get("repository") == "AlterProgramming/Agentic-Production-Studio", "repository mismatch")
    require(binding.get("required") is True, "binding must be required")
    require(binding.get("fail_closed") is True, "binding must fail closed")
    authority = binding.get("authority", {})
    require(authority.get("repository") == "AlterProgramming/Agent-Command-Center", "Command Center authority mismatch")
    require(authority.get("branch") == "main", "authority branch must be main")
    require(authority.get("bootstrap_script") == "scripts/session_bootstrap.py", "bootstrap script mismatch")
    command = binding.get("local_bootstrap", {}).get("command", "")
    require("session_bootstrap.py" in command, "local bootstrap must invoke session_bootstrap.py")
    require("AlterProgramming/Agentic-Production-Studio" in command, "local bootstrap must bind this repository")
    reads = binding.get("connector_bootstrap", {}).get("required_reads", [])
    require(len(reads) == 3, "connector bootstrap must read all three Command Center registries")
    receipt = binding.get("receipt", {})
    require(receipt.get("kind") == "assistant.command-center-bootstrap-receipt", "receipt kind mismatch")
    require(receipt.get("required_value") is True, "initialized receipt value must be true")
    agents = AGENTS.read_text(encoding="utf-8")
    require("Session zero: initialize in Agent Command Center" in agents, "AGENTS.md does not require session initialization")
    require("Bootstrap is fail-closed" in agents, "AGENTS.md does not state fail-closed behavior")

    if errors:
        for error in errors:
            print(f"command-center-binding error: {error}", file=sys.stderr)
        return 1
    print("Production Studio Command Center binding valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
