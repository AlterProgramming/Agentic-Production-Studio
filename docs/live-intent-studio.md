# Live intent studio

The Production Studio includes a loopback-only console that makes real work legible through semantic events.

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

## Reference recreation

Configure a retained output directory and image adapter:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --recreation-output-directory /path/to/recreation-runs \
  --image-generator-command '/path/to/image-adapter' \
  --image-evaluator-command '/path/to/image-evaluator'
```

Choose **Reference recreation pipeline**. The runtime repeatedly edits the current best parent, scores each candidate against semantic anchors, emits compute waits and cooldowns, promotes only measured improvements, and persists resumable lineage.

## Video projects — local runtime compute

The primary video path is local and does not require an account, API key, or remote generation service:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --video-output-directory /path/to/video-runs \
  --video-generator-command 'python3 tools/local_video_shot_adapter.py'
```

Choose **Video-native shot project** and submit a dependency-ordered project plan. The local adapter uses FFmpeg on the current runtime to produce dense continuous video, exact frame counts, retained candidates, and targeted repair passes. Remote adapters remain optional extensions behind the same command contract.

## Boundaries

- The HTTP service binds to loopback only.
- Builder mode is preview-only and does not mutate the workspace.
- Workspace and reference access is restricted to explicit `--allow-root` paths.
- SceneForge artifacts are served only when they remain inside the configured data directory.
- Recreation and video candidates are accepted only inside their configured output directories.
- Generation and repair work is bounded by the job configuration.
- Local runtime compute is the default video execution path.
- External credentials are neither required nor requested by the local path.
- This development surface does not replace or publish the Command Center SceneForge gateway.

The shared event contract is `contracts/intent-event.schema.json` and must remain conformant with the copy in BrightEngine Forge.
