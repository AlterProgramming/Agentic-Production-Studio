# Agentic Production Studio Agent Instructions

## Session zero: initialize in Agent Command Center

Before reading task implementation files, changing source, dispatching long-horizon work, or making a completion claim, read `.agent/command-center.json` and initialize through `AlterProgramming/Agent-Command-Center`.

Preferred local command:

```bash
python3 "$COMMAND_CENTER_ROOT/scripts/session_bootstrap.py" \
  --session-id <stable-session-id> \
  --repository AlterProgramming/Agentic-Production-Studio \
  --scope visual-production \
  --text "<task summary>" \
  --output <handoff-or-receipt-path>
```

When Command Center is not checked out locally, use connected repository tools to read its canonical, capability, and session registries from `main`, apply the same resolution semantics, and retain an equivalent `assistant.command-center-bootstrap-receipt` in the handoff. Bootstrap is fail-closed.

After initialization, read `CAPABILITY_BINDINGS.json` before significant visual-production work.

For mnemonic or memory-informed reconstruction:

1. preserve embodied and artifact layers separately;
2. validate the scene contract with `capabilities/mnemonic-3d-separation/validate_scene.py`;
3. retain provenance and conflicting hypotheses;
4. do not claim a production rig, cloth solver, or runtime unless execution evidence exists;
5. produce a completion receipt that distinguishes contract validation from rendered or deployed execution.

The command-center capability registry is authoritative for inherited implementation behavior; canonical visual doctrine remains in the command-center memory registry.
