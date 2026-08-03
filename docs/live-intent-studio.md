# Live intent studio

The Production Studio includes a loopback-only console that makes real work legible through semantic events. The surface now supports builder preview, retained SceneForge execution, iterative reference recreation, and dependency-ordered video projects.

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

## Reference recreation and video projects

Configure the image and video adapters and their retained output roots:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --recreation-output-directory /path/to/recreation-runs \
  --image-generator-command 'python3 tools/openai_reference_recreation_adapter.py' \
  --image-evaluator-command 'python3 tools/openai_reference_recreation_adapter.py' \
  --video-output-directory /path/to/video-runs \
  --video-generator-command 'python3 tools/openai_video_shot_adapter.py' \
  --video-evaluator-command '/path/to/video-evaluator'
```

Choose **Reference recreation pipeline** for retained image iteration or **Video-native shot project** for a dependency-ordered project plan. Video projects expose candidate generation, provider progress, targeted repair passes, temporal scoring, best-candidate promotion, and resumable state through the same SSE surface. The browser renders the current best MP4 artifact rather than treating video as a sequence of still-image cards.

See `docs/reference-recreation.md` and `docs/video-native-runtime.md` for the respective adapter contracts, scoring rules, and operating boundaries.

## Boundaries

- The HTTP service binds to loopback only.
- Builder mode is preview-only and does not mutate the workspace.
- Workspace and reference access are restricted to explicit `--allow-root` paths.
- SceneForge artifacts are served only when they remain inside the configured data directory.
- Recreation and video artifacts are served only when they remain inside their configured output directories.
- Generation request count, retry count, rate, candidate count, and repair count are bounded by configuration.
- Provider credentials stay in adapter process environments and are not accepted through browser requests.
- This development adapter does not replace or publish the Command Center SceneForge gateway.

The shared semantic event contract is `contracts/intent-event.schema.json`. Video project plans additionally conform to `contracts/video-project.schema.json`.
