# Video-native shot runtime

The video runtime executes a dependency-ordered shot graph rather than treating a handful of frames as a video. Every shot has an explicit reference image, prompt, hard-preserve semantics, motion intent, avoidance constraints, candidate budget, repair budget, and target score.

Production Studio owns orchestration, compute budgeting, lineage, evaluation, repair decisions, and resumable state. A JSON-over-stdio adapter owns one generation or repair operation.

## Local runtime compute — default path

The default path requires no account, API key, remote provider, or billed generation service. It uses the current machine's runtime compute through FFmpeg:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --video-output-directory /path/to/video-runs \
  --video-generator-command 'python3 tools/local_video_shot_adapter.py'
```

Or run the retained project directly:

```bash
python3 tools/video_project.py examples/ff7-intermission-video-project.json \
  --generator-command 'python3 tools/local_video_shot_adapter.py'
```

The local adapter generates exact dense frame counts, continuous camera motion, temporal filtering, H.264 delivery artifacts, and targeted local repair passes. It returns `account_required: false` and does not inspect credentials.

## Runtime guarantees

- dependency graph validation and cycle rejection
- explicit candidate and repair budgets
- compute pacing and bounded retries
- adapter output containment inside the assigned candidate directory
- weighted temporal and semantic scoring when an evaluator is configured
- repair targeting based on the weakest available metrics
- append-only candidate and repair lineage
- per-shot manifests and project-level resumable `state.json`
- semantic progress events over the existing intent-event contract

## Evaluation contract

A configured evaluator receives the video candidate, reference image, prompt, and semantic constraints. It returns values from zero to one for:

- `identity_stability`
- `temporal_consistency`
- `motion_quality`
- `camera_intent`
- `composition`
- `world_continuity`
- `orb_hand_continuity`
- `artifact_penalty`

The runtime promotes only candidates that improve the weighted score. When a shot remains below target, the repair queue focuses on its weakest metrics and retains the prior candidate as evidence.

## Optional external adapters

Remote or account-backed adapters may be installed behind the same command contract, but they are optional extensions and are not the assumed execution path. Credentials, when an operator deliberately chooses such an adapter, remain outside the project plan and browser surface.

## Evidence boundary

Local runtime output is genuine dense video compute, but it is not misrepresented as learned video diffusion. Semantic identity and world-continuity claims still require a capable evaluator. The runtime records that boundary instead of treating provider access as completion.
