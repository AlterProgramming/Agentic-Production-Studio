# Agentic Production Studio — Initialization Pack

## Studio position

A small, specialist production studio that converts approved concepts, style references, static assets, or technical requirements into **finished, packageable visual deliverables within one production week**.

The studio does not sell generic "AI art." It sells bounded production outcomes:

- Original raster and pixel assets
- Sprite animation and multi-frame effects
- Static-image-plus-effect motion systems
- Model-first scenes with retained geometry, cameras, lighting, render passes, and experiential derivatives
- Godot-ready delivery packages
- Interactive visual prototypes
- Creative-model evaluation and deployment packs
- Provenance, manifests, QA, and technical handoff
- Surgical, evidence-producing build plans for narrow asset and metadata changes

## Canonical visual-generation doctrine

Meaningful visual generation defaults to a retained model or scene before the final image is rendered:

```text
intent -> structured scene -> reusable model -> validation/recovery -> rendered image -> motion and interaction
```

A generated image is therefore a view of a retained scene, not the terminal artifact. Flat image-only generation is an explicit lightweight exception when continuity, alternate views, movement, speech, relighting, simulation, and interaction are not expected. See `05_MODEL_FIRST_VISUAL_DOCTRINE.md`.

## Initial market focus

### Primary market
Small mobile and Godot studios with an existing visual style and a recurring need for production-ready content.

### Secondary markets
- Brand mascot and social-content teams
- Educational and training products
- Exhibit and interactive agencies
- E-commerce performance-creative teams
- Game outsourcing and co-development partners
- Creative teams evaluating Hugging Face models

## Launch rule

Only sell packages that meet all five conditions:

1. Inputs can be defined before production begins.
2. Output quantity and complexity can be capped.
3. Acceptance tests can be written in advance.
4. Delivery can be completed in five production days.
5. Source files, runtime files, QA evidence, and manifests can be packaged together.

For a model-first package, the retained scene/model and its recovery state are part of the source deliverable, not optional implementation debris.

## Surgical production substrate

The repository includes an executable builder foundation for controlled production changes:

```bash
python3 tools/studio_builder.py plan <plan.json>
python3 tools/studio_builder.py apply <plan.json> --yes
python3 tools/studio_builder.py verify <receipt.json>
```

A builder plan declares its exact write boundary, current-state preconditions, deterministic operations, and postconditions. Dry runs show the write set and text diffs. Successful application produces a receipt with the plan hash and before/after file hashes. Domain operators use the same contract; the first implemented asset operator normalizes an image onto an exact transparent canvas using explicit source and target anchors.

This substrate is intentionally below individual service packages. Future palette, animation alignment, preview, Godot, model-first scene, and package builders should register as operations rather than becoming isolated scripts.

## Live intent studio

Run the loopback studio surface against the real builder preview path:

```bash
python3 tools/studio_console.py --allow-root /path/to/workspace
```

To make the same surface execute the BrightEngine retained-scene runtime, also supply the matching SceneForge runner and its local data directory:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/workspace \
  --sceneforge-runner /path/to/BrightEngine-Forge/agent-api/sceneforge-studio-runner.mjs \
  --sceneforge-data-directory /path/to/local-data
```

To run bounded iterative image recreation against a real provider adapter:

```bash
python3 tools/studio_console.py \
  --allow-root /path/to/references \
  --recreation-output-directory /path/to/recreation-runs \
  --image-generator-command 'python3 tools/openai_reference_recreation_adapter.py' \
  --image-evaluator-command 'python3 tools/openai_reference_recreation_adapter.py'
```

Open `http://127.0.0.1:8765`. The console streams semantic intent events over Server-Sent Events while the actual runtime works, then exposes retained artifacts. Reference recreation adds request-budget enforcement, token-bucket pacing, bounded provider retries, semantic scoring, best-parent promotion, and resumable state. See `docs/live-intent-studio.md` and `docs/reference-recreation.md`.

## Initial service packages

1. LiveOps Asset Drop
2. Godot Vertical-Slice Art Pack
3. Mascot Motion Expansion Pack
4. Static-to-Motion Product Batch
5. Interactive Story Prototype
6. Creative Model Evaluation Pack
7. White-Label Production Sprint

Model-first scene generation remains a Foundation capability until its bounded package benchmark and recovery evidence pass.

## Studio structure

### Creative Production Pod
Owns visual design, raster production, animation, VFX, compositing, cleanup, and final visual quality.

### Technical Integration Pod
Owns Godot packaging, imports, pivots, sprite resources, scene/model packaging, file optimization, delivery validation, and handoff.

### Research and Model Operations Pod
Owns research, model comparison, adapter configuration, evaluation, deployment recommendations, and provenance capture.

### Production Control
Owns scope, schedule, checkpoints, approvals, manifests, change control, model-first acceptance evidence, and final package completeness.

## Default one-week cadence

- **Day 0:** Intake, qualification, source audit, scope lock
- **Day 1:** Brief, motion design, technical specification, first style proof
- **Day 2:** Core asset and retained-scene production
- **Day 3:** Animation, effects, variants, first integrated build
- **Day 4:** Cleanup, integration, revision, packaging
- **Day 5:** QA, capture, manifest, handoff, acceptance review

## Commercial defaults

- Fixed scope and fixed price
- One primary decision-maker
- One consolidated revision round
- Client supplies approved references and confirms rights
- Rush work requires premium pricing
- Additional assets become a change order or follow-on sprint
- No production starts without written acceptance criteria

## Folder guide

- `01_STUDIO_CHARTER.md` — positioning, market, boundaries, and principles
- `02_CAPABILITY_REGISTRY.md` — capabilities, readiness, evidence, and constraints
- `03_SERVICE_CATALOG.md` — commercial service menu
- `04_LAUNCH_ROADMAP.md` — sequence for proving and launching packages
- `05_MODEL_FIRST_VISUAL_DOCTRINE.md` — retained-scene default, boundaries, delivery contract, and quality gates
- `builder/` — machine-readable builder capability and plan contracts
- `studio_builder/` — deterministic builder engine and registered domain operations
- `studio_runtime/` — semantic event stream, reference-recreation orchestration, and local execution service
- `studio_console/` — human-facing live work surface
- `tools/` — command-line validation, builder entrypoints, and provider adapters
- `benchmarks/` — internal production reference workspaces
- `packages/` — complete one-week package definitions
- `operations/` — intake, production, delivery, builder, and change-control procedures
- `templates/` — reusable briefs, manifests, proposals, and acceptance forms
- `sales/` — qualification, pricing, and outreach positioning
- `qa/` — quality gates and validation checklists
- `tracking/` — readiness ledgers and evidence scorecards
- `model_ops/` — model-evaluation and deployment workflow

## Current initialization status

The studio is initialized at **Operating Model v0.3 — Model-First Visual Foundation**. The surgical builder foundation remains available for previewable, guarded, transactionally applied changes with receipts and drift verification. Model-first scene generation is canonically registered as a Foundation capability. The live intent runtime now also supports bounded, retained reference-recreation experiments whose provider calls, semantic evaluations, rate waits, retries, lineage, and stopping decisions are inspectable and reproducible.
