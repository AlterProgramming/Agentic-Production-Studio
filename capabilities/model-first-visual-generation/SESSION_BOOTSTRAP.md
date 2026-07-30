# Model-First Visual Generation — Session Bootstrap

This document exists because canonical memory and executable capability are different things.

Loading `visual-generation.model-first.v1` from the Agent Command Center tells a session what the governing visual doctrine is. It does **not** install SceneForge, AvatarForge, prior container files, or prior session artifacts.

## Required startup sequence

When a request may require model-first visual generation:

1. Retrieve `capabilities/model-first-visual-generation/capability.json`.
2. Read `availability.status` and inspect the session's actual tools.
3. Confirm that the session can execute first-party source locally.
4. Materialize the required repository files before promising execution.
5. Run a bounded entrypoint and retain its execution receipt.
6. Verify that a persistent scene/model was written before the accepted render.
7. Reopen the retained asset and run the listed validation gates.
8. Only then claim model-first completion.

## Tool-routing rule

A platform image generator may be used as a source-image, texture, concept, or reconstruction stage when platform instructions require it. It must not silently become the terminal artifact when the accepted request requires retained scene continuity.

```text
prompt
  -> optional source/concept image
  -> structured scene specification
  -> persistent model or scene
  -> reopen validation and recovery
  -> final render
  -> motion / alternate-view / interactive derivative
```

## Current first-party executable path

The public studio repository currently exposes a bounded image-to-scene builder:

```bash
python3 tools/scene_from_image.py INPUT_IMAGE \
  --out OUTPUT_DIR/scene/scene.glb \
  --title "Scene title"
```

This creates a retained GLB with named geometry, an embedded source image, camera, lighting, animation, and a scene sidecar. It proves that the image is no longer only a flat terminal file.

The richer AvatarForge/SceneForge runtime—character rigs, recovery, poses, locomotion, speech coordination, and textile simulation—must be separately materialized until it is deployed as a stable first-party service or installed tool.

## Fail-closed behavior

A session must stop and disclose the boundary when any of these are true:

- no local execution environment is available;
- the named first-party source cannot be materialized;
- only a flat image exists;
- the scene/model was not written before the final render;
- the persisted model cannot be reopened;
- provenance cannot link the render back to the persisted model;
- the session is relying on another conversation's inaccessible container state.

The correct statement is:

> The model-first doctrine is loaded, but the executable runtime is not available in this session. The flat image is only a lightweight output or source stage, not a retained modeled scene.

## Completion receipt

A full claim requires a receipt containing at least:

```json
{
  "capability_id": "visual-generation.model-first.v1",
  "runtime_entrypoint": "...",
  "persistent_scene_written_before_render": true,
  "scene_path": "scene/scene.glb",
  "scene_sha256": "...",
  "reopened": true,
  "validation": "pass",
  "hero_render": "renders/hero.png",
  "derivative": "motion/orbit.mp4",
  "recovery_receipt": "scene/recovery.json"
}
```

Without that evidence, the session may describe intent or doctrine, but not executable model-first completion.
