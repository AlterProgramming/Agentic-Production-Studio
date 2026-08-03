# Reference recreation runtime

The reference-recreation runtime repeatedly edits a retained parent image, evaluates each candidate against explicit semantic anchors, and promotes only candidates that improve by the configured minimum score.

It is intentionally provider-neutral. Production Studio owns the bounded search, rate policy, lineage, state, events, and artifact serving. A configured command owns one generation or evaluation call.

## Launch with the OpenAI adapter

Install the optional SDK dependency and expose an API key in the environment:

```bash
python3 -m pip install openai
export OPENAI_API_KEY=...
```

Run the console with the same adapter configured for generation and evaluation:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --recreation-output-directory /path/to/recreation-runs \
  --image-generator-command 'python3 tools/openai_reference_recreation_adapter.py' \
  --image-evaluator-command 'python3 tools/openai_reference_recreation_adapter.py'
```

Open `http://127.0.0.1:8765`, choose **Reference recreation pipeline**, and enter a reference image path inside an allowed root.

The adapter defaults to `gpt-image-2` for image editing and `gpt-5.6-luna` for semantic evaluation. Override them without changing repository code:

```bash
export OPENAI_IMAGE_MODEL=gpt-image-2
export OPENAI_IMAGE_SIZE=1536x1024
export OPENAI_IMAGE_QUALITY=high
export OPENAI_IMAGE_INPUT_FIDELITY=high
export OPENAI_EVALUATOR_MODEL=gpt-5.6-luna
```

## Search behavior

Each run has an explicit maximum request budget:

```text
maximum iterations × candidates per iteration
```

For every candidate, the runtime:

1. selects a bounded mutation axis;
2. waits for token-bucket capacity;
3. asks the generator to edit the current parent;
4. retries provider throttles with bounded exponential backoff and jitter;
5. evaluates semantic retention, environmental match, aesthetics, composition, and drift;
6. promotes the candidate only when it clears the minimum-improvement threshold;
7. persists the complete state and candidate lineage.

The run stops when it reaches the target score, exhausts its budget, or reaches the configured number of non-improving iterations.

The default request pace is four image requests per minute with a burst of one. This is deliberately conservative; set it to the limit appropriate for the configured provider account rather than treating it as a universal provider limit.

## Resuming

Every run writes:

```text
<recreation-output-directory>/<job-id>/state.json
```

Enter a prior job ID in the console's **Resume job ID** field. The new run loads the previous best candidate and lineage, then continues from the next iteration while retaining a new run boundary.

## Generator command contract

The command reads one JSON object from stdin. A generation request includes:

```json
{
  "schema_version": "1.0",
  "operation": "generate",
  "job_id": "studio-…",
  "candidate_id": "i001-c01",
  "iteration": 1,
  "candidate_index": 1,
  "goal": "…",
  "prompt": "…",
  "variant": "identity-preservation",
  "reference_image": "/absolute/reference.png",
  "parent_image": "/absolute/current-parent.png",
  "output_directory": "/absolute/job/iterations/001/candidate-01",
  "anchors": [],
  "preserve": [],
  "avoid": []
}
```

It must write the candidate inside `output_directory` and return one JSON object:

```json
{
  "status": "completed",
  "image_path": "/absolute/job/iterations/001/candidate-01/candidate.png",
  "metrics": {
    "subject_retention": 0.9,
    "anchor_retention": 0.88,
    "environment_match": 0.83,
    "aesthetic_quality": 0.86,
    "composition_stability": 0.91,
    "drift_penalty": 0.04
  },
  "notes": ["optional provider notes"]
}
```

Metrics may instead come from a separately configured evaluator command.

A provider throttle must use exit code `75`, a `rate_limited` response, or both:

```json
{
  "status": "rate_limited",
  "retry_after": 12.5,
  "error": "provider throttle"
}
```

## Evaluator command contract

The evaluator receives `operation: evaluate` plus the reference, current parent, candidate, goal, and semantic constraints. It returns the same `metrics` and `notes` fields shown above.

The weighted score is:

```text
0.35 subject retention
+ 0.20 anchor retention
+ 0.20 environment match
+ 0.15 aesthetic quality
+ 0.10 composition stability
- drift penalty
```

Missing metrics are scored as zero and recorded in the candidate notes. This prevents a generator from winning by omitting evidence.

## Boundaries

- Reference images must remain inside an explicit `--allow-root` path.
- Provider output must remain inside its assigned candidate directory.
- Retained artifacts are served only from the configured recreation output directory.
- The server remains loopback-only.
- The runtime never sends a request without first acquiring rate budget.
- Retries and total candidate requests are bounded.
- API credentials remain in the adapter process environment and are not accepted through the browser request body.
