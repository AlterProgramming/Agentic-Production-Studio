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

Configure a provider adapter and a retained output directory:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --recreation-output-directory /path/to/recreation-runs \
  --image-generator-command 'python3 tools/openai_reference_recreation_adapter.py' \
  --image-evaluator-command 'python3 tools/openai_reference_recreation_adapter.py'
```

Choose **Reference recreation pipeline**. The runtime repeatedly edits the current best parent, scores each candidate against semantic anchors, emits rate waits and provider cooldowns, promotes only measured improvements, and persists resumable lineage. See `docs/reference-recreation.md` for the command contract and operating boundaries.

## Boundaries

- The HTTP service binds to loopback only.
- Builder mode is preview-only and does not mutate the workspace.
- Workspace and reference access is restricted to explicit `--allow-root` paths.
- SceneForge artifacts are served only when they remain inside the configured data directory.
- Recreation candidates are accepted only inside the configured recreation output directory.
- Generation request count, retry count, and rate are bounded by the job configuration.
- Provider credentials stay in the adapter environment, outside browser requests and retained state.
- This development adapter does not replace or publish the Command Center SceneForge gateway.

The shared event contract is `contracts/intent-event.schema.json` and must remain conformant with the copy in BrightEngine Forge.
