# Agentic Production Studio

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
- Visually composed production circuits that compile into guarded builder plans

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

The repository includes an executable builder foundation for controlled production changes:

```bash
python3 tools/studio_builder.py plan <plan.json>
python3 tools/studio_builder.py apply <plan.json> --yes
python3 tools/studio_builder.py verify <receipt.json>
```

A builder plan declares its exact write boundary, current-state preconditions, deterministic operations, and postconditions. Dry runs show the write set and text diffs. Successful application produces a receipt with the plan hash and before/after file hashes.

Implemented domain operations now include:

- exact anchor-aware image normalization;
- deterministic nearest-color palette enforcement;
- nearest-neighbor contact-sheet generation;
- Godot `SpriteFrames` and event-metadata compilation;
- byte-reproducible ZIP delivery packaging.

## Studio Composition Workbench

`studio_workbench/` is a browser-based visual compiler layered above the surgical builder. An operator draws one bounded production circuit, inspects recognition and compilation diagnostics, supplies exact execution bindings, and exports a Surgical Builder Plan v1 document.

```text
freehand strokes
  → cleaned geometry
  → scope and operator recognition
  → StudioGlyphAST
  → StudioIR
  → guarded builder plan
  → preview, apply, receipt, verify
```

The first visual grammar includes source input, normalization, palette enforcement, contact sheets, Godot compilation, deterministic packaging, strict diagnostics, evidence requirements, and parallel scheduling intent. The workbench never writes directly and never guesses paths, anchors, dimensions, palettes, timing, or delivery contents.

Serve the repository root and open `/studio_workbench/`:

```bash
python3 -m http.server 8000
```

The architecture was informed by the MIT-licensed `ytnrvdf/wha-spell-simulator`; attribution and the independent-IP boundary are recorded in `THIRD_PARTY_NOTICES.md` and `research/05_WHA_SPELL_SIMULATOR_ABSORPTION.md`.

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
- `builder/` — machine-readable builder capability, AST, IR, and plan contracts
- `studio_builder/` — deterministic builder engine and registered domain operations
- `studio_workbench/` — browser-based drawing, diagnostics, visual compiler, and plan export
- `tools/` — command-line validation and builder entrypoints
- `benchmarks/` — internal production reference workspaces
- `packages/` — complete one-week package definitions
- `operations/` — intake, production, delivery, builder, workbench, and change-control procedures
- `templates/` — reusable briefs, manifests, proposals, and acceptance forms
- `sales/` — qualification, pricing, and outreach positioning
- `qa/` — quality gates and validation checklists
- `tracking/` — readiness ledgers and evidence scorecards
- `research/` — capability absorption records and source boundaries
- `model_ops/` — model-evaluation and deployment workflow

## Current initialization status

The studio is initialized at **Operating Model v0.3 — Visual Compiler Foundation**. Commercial packages remain in internal proof, but the repository now has both a guarded mutation substrate and a visual composition layer that translates creative intent into reviewable execution plans. The next evidence gate is a complete Storm run through visual composition, builder preview, deterministic production operators, Godot import, package assembly, and retained receipts.
