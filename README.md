# Agentic Production Studio — Initialization Pack

## Studio position

A small, specialist production studio that converts approved concepts, style references, static assets, or technical requirements into **finished, packageable visual deliverables within one production week**.

The studio does not sell generic "AI art." It sells bounded production outcomes:

- Original raster and pixel assets
- Sprite animation and multi-frame effects
- Static-image-plus-effect motion systems
- Godot-ready delivery packages
- Interactive visual prototypes
- Creative-model evaluation and deployment packs
- Provenance, manifests, QA, and technical handoff
- Surgical, evidence-producing build plans for narrow asset and metadata changes

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

## Surgical production substrate

The repository now includes an executable builder foundation for controlled production changes:

```bash
python3 tools/studio_builder.py plan <plan.json>
python3 tools/studio_builder.py apply <plan.json> --yes
python3 tools/studio_builder.py verify <receipt.json>
```

A builder plan declares its exact write boundary, current-state preconditions, deterministic operations, and postconditions. Dry runs show the write set and text diffs. Successful application produces a receipt with the plan hash and before/after file hashes. Domain operators use the same contract; the first implemented asset operator normalizes an image onto an exact transparent canvas using explicit source and target anchors.

This substrate is intentionally below individual service packages. Future palette, animation alignment, preview, Godot, and package builders should register as operations rather than becoming isolated scripts.

## Initial service packages

1. LiveOps Asset Drop
2. Godot Vertical-Slice Art Pack
3. Mascot Motion Expansion Pack
4. Static-to-Motion Product Batch
5. Interactive Story Prototype
6. Creative Model Evaluation Pack
7. White-Label Production Sprint

## Studio structure

### Creative Production Pod
Owns visual design, raster production, animation, VFX, compositing, cleanup, and final visual quality.

### Technical Integration Pod
Owns Godot packaging, imports, pivots, sprite resources, file optimization, delivery validation, and handoff.

### Research and Model Operations Pod
Owns research, model comparison, adapter configuration, evaluation, deployment recommendations, and provenance capture.

### Production Control
Owns scope, schedule, checkpoints, approvals, manifests, change control, and final package completeness.

## Default one-week cadence

- **Day 0:** Intake, qualification, source audit, scope lock
- **Day 1:** Brief, motion design, technical specification, first style proof
- **Day 2:** Core asset production
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
- `builder/` — machine-readable builder capability and plan contracts
- `studio_builder/` — deterministic builder engine and registered domain operations
- `tools/` — command-line validation and builder entrypoints
- `benchmarks/` — internal production reference workspaces
- `packages/` — complete one-week package definitions
- `operations/` — intake, production, delivery, builder, and change-control procedures
- `templates/` — reusable briefs, manifests, proposals, and acceptance forms
- `sales/` — qualification, pricing, and outreach positioning
- `qa/` — quality gates and validation checklists
- `tracking/` — readiness ledgers and evidence scorecards
- `model_ops/` — model-evaluation and deployment workflow

## Current initialization status

The studio is initialized at **Operating Model v0.2 — Builder Foundation**. Commercial package definitions and workflow documents remain in internal proof, but the repository now has an executable substrate for previewable, guarded, transactionally applied changes with receipts and drift verification. The next evidence gate is to run the builder against the real Storm source, retain the receipt, and add palette, sequence-alignment, Godot-resource, and deterministic package operators.
