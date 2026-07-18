# Surgical Builder Substrate

## Why this is foundational

A production studio needs more than generators and validators. It needs a controlled way to make a narrow change without repainting, regenerating, or repackaging unrelated work.

The builder substrate establishes the invariant:

> Every mutation is planned, path-confined, previewable, guarded by current-state expectations, transactionally applied, and followed by a verifiable receipt.

## Current command surface

```bash
python3 tools/studio_builder.py plan examples/builder/storm-contract-lock.json
python3 tools/studio_builder.py apply examples/builder/storm-contract-lock.json --yes
python3 tools/studio_builder.py verify .studio-builder/receipts/<receipt>.json
```

`apply` intentionally requires `--yes`. The operator is expected to inspect the dry-run write set and text diffs first.

## Implemented operations

- `write_text`: create or explicitly overwrite a text file.
- `replace_text`: replace an exact occurrence count; reject broad or stale matches.
- `json_patch`: update exact JSON pointers with optional expected-old-value guards.
- `copy_file`: copy a workspace source with optional source checksum verification.
- `delete_file`: delete only when the current checksum matches the plan.
- `image_normalize`: place an RGBA source on an exact transparent canvas using explicit source and target anchors.

Operations run through an extension registry so image, animation, Godot, preview, and packaging operators can be added without changing the planning and evidence contract.

## Safety and evidence

- Absolute paths and `..` traversal are rejected.
- Every output must match an `allowed_paths` pattern.
- Preconditions are checked against the real workspace.
- All operations are simulated before the first disk write.
- Postconditions are checked against the simulated final state.
- Text changes include unified diffs.
- Apply writes a receipt containing the plan hash and before/after file hashes.
- Verify detects any output drift after the build.
- An apply failure restores files already touched by the transaction.

## Foundational capability ladder

### Foundation — now implemented

1. Workspace confinement
2. Explicit write-set planning
3. Guarded surgical mutation
4. Dry-run diffs
5. Transactional application
6. Reproducible evidence receipts
7. Post-build drift verification
8. Extensible operation registry
9. Anchor-aware image normalization

### Next operators

1. `image.palette_enforce`: approved colors, deterministic remap, and violation evidence
2. `animation.align`: stable-region or anchor alignment across frame sequences
3. `animation.contact_sheet`: deterministic review artifact
4. `preview.gif`: exact FPS and loop behavior from the manifest
5. `godot.spriteframes_compile`: generate `.tres` from the locked manifest
6. `package.assemble`: ZIP with manifest-derived inclusion and checksums

### Later orchestration

- dependency graph and incremental rebuilds;
- content-addressed artifact cache;
- sandboxed adapters for Aseprite, ImageMagick, Godot, Blender, and model endpoints;
- human approval checkpoints between design proof and volume production;
- benchmark telemetry for labor, runtime, defects, and retries.

The next specialized capability should be implemented as a registered operation rather than a separate one-off script. This keeps the studio surgical as the tool surface grows.
