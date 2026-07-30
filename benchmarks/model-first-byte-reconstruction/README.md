# Model-first byte-reconstruction scene benchmark

## Purpose

Exercise the Foundation `Model-first scene generation` capability against a damaged-input case where the available bytes cannot be decoded into the original picture.

The benchmark retains the generated substitute as a scene before producing any derivative. It does **not** claim that the substitute matches the missing original frame.

## Executed workflow

```text
corrupted byte fragment
  -> recovery diagnosis and quarantine boundary
  -> generated substitute retained as source evidence
  -> structured scene specification
  -> animated GLB with named geometry, camera, and lights
  -> reopen validation
  -> hero, depth, and object-ID passes
  -> motion derivative
  -> hash-linked packaged handoff
```

## Builder

```bash
python3 tools/scene_from_image.py reconstruction.png \
  --out scene/scene.glb \
  --title "Byte Reconstruction Card Scene" \
  --max-texture 768
```

The builder writes `scene.glb` and a sidecar `scene.scene.json`. The completed handoff additionally contains the semantic graph, recovery receipt, render passes, motion data, preview, and provenance manifest described in `05_MODEL_FIRST_VISUAL_DOCTRINE.md`.

## Result

The retained model reopened successfully with three geometry objects, one embedded image, a named perspective camera, two punctual lights, and one two-channel loop animation. Geometry positions were finite and all face indices were within bounds.

The original-content claim remains quarantined because no intact image container or complete byte stream was available. The scene derivative itself passed its structural delivery gates.

See `receipt.json` for the file hashes, validation result, and acceptance evidence from the executed package.
