# Live intent studio

The Production Studio now includes a loopback-only console that makes real work legible through semantic events.

## Builder preview

```bash
python3 tools/studio_console.py --allow-root /path/to/workspace
```

Open `http://127.0.0.1:8765`, choose **Studio Builder preview**, and submit a normal builder plan. The console calls the existing `StudioBuilder.preview` path, streams operation-level intent events, and returns the ordinary non-mutating preview receipt.

## BrightEngine SceneForge

Check out `AlterProgramming/BrightEngine-Forge` with the matching live-intent branch, then run:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/workspace \
  --sceneforge-runner /path/to/BrightEngine-Forge/agent-api/sceneforge-studio-runner.mjs \
  --sceneforge-data-directory /path/to/local-data
```

The console invokes the existing first-party `executeModelFirst` runtime through the SceneForge studio runner. The runner observes retained artifacts as they are created, emits `studio.intent-event` JSONL, and returns the generated hero render, preview, scene, and receipt through the local console.

## Boundaries

- The HTTP service binds to loopback only.
- Builder mode is preview-only and does not mutate the workspace.
- Workspace access is restricted to explicit `--allow-root` paths.
- SceneForge artifacts are served only when they remain inside the configured data directory.
- This development adapter does not replace or publish the Command Center SceneForge gateway.

The shared contract is `contracts/intent-event.schema.json` and must remain conformant with the copy in BrightEngine Forge.
