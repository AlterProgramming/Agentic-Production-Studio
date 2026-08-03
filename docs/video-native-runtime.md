# Video-native shot runtime

The video runtime executes a dependency-ordered shot graph rather than treating a handful of frames as a video. Every shot has an explicit reference image, prompt, hard-preserve semantics, motion intent, avoidance constraints, candidate budget, repair budget, and target score.

Production Studio owns orchestration, rate control, lineage, evaluation, repair decisions, and resumable state. A JSON-over-stdio adapter owns one provider request. The included OpenAI adapter uses the asynchronous Videos API: it submits an image-referenced job, relays polling progress, downloads the completed MP4, and uses the remix endpoint for repair passes.

## Run

Place the retained reference image beside the project JSON, then run:

```bash
export OPENAI_API_KEY=...
python3 tools/video_project.py examples/ff7-intermission-video-project.json \
  --generator-command 'python3 tools/openai_video_shot_adapter.py' \
  --evaluator-command '/path/to/video-evaluator'
```

The generator adapter is concrete. The evaluator remains provider-neutral because industrial promotion needs project-specific identity, temporal, motion, camera, and artifact evidence rather than a universal aesthetic score.

## Runtime guarantees

- dependency graph validation and cycle rejection
- explicit candidate and repair budgets
- token-bucket request pacing
- provider `retry_after`, exponential cooldown, jitter, and bounded retries
- adapter output containment inside the assigned candidate directory
- weighted temporal and semantic scoring
- repair targeting based on the weakest metrics
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

## OpenAI adapter boundary

The adapter uses `POST /v1/videos` with `input_reference`, polls `GET /v1/videos/{id}`, downloads `GET /v1/videos/{id}/content`, and repairs a retained candidate with `POST /v1/videos/{id}/remix`. Credentials remain in the adapter environment and never enter the project plan or browser surface.

The API currently constrains generated clips to supported durations and dimensions, so project shots must use the values registered in `contracts/video-project.schema.json`. Provider availability and model lifecycle remain external operational dependencies.
