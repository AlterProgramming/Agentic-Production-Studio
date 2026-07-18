# Storm V1 — Integrated Animation Benchmark

This directory is the production workspace contract for the first integrated deterministic animation benchmark.

## Objective

Rebuild Storm as one complete four-to-eight-frame animation in which the source artwork, body response, lighting, and VFX form one temporally coherent sequence. A static Storm image with an independently animated overlay does not pass V1.

## Current state

**Contract scaffold only.** The source image and its measured production values have not been committed here, so the JSON files intentionally remain `draft` and contain unresolved values. Do not change them to `locked` by guessing.

## Inputs required to lock Gate 0

- canonical Storm source file and source identifier;
- source rights/provenance statement;
- measured canvas width and height;
- fixed anchor coordinate;
- selected animation state and gameplay trigger;
- frame count from four through eight;
- FPS and loop behavior;
- anticipation, action, impact, peak-effect, and recovery frame indexes;
- approved base and VFX palette policy;
- representative gameplay background;
- exact Godot 4.x target version.

## Expected final layout

```text
storm-v1/
├── animation-brief.json
├── manifest.json
├── provenance.json
├── qa-config.json
├── qa-report.json
├── integration-guide.md
├── source/
├── frames/
├── previews/
├── godot/
└── evidence/
```

## Gate commands

```bash
python tools/validate_animation.py benchmarks/storm-v1 --stage contract
python tools/validate_animation.py benchmarks/storm-v1 --stage frames
python tools/validate_animation.py benchmarks/storm-v1 --stage delivery --report benchmarks/storm-v1/qa-report.json
```

The first command is expected to fail while the brief remains a draft. That failure is evidence that production assumptions have not been silently invented.
