# ObjectForge

ObjectForge develops complete runtime-ready objects from declared constructive matter and reusable functional grammars. It does not call an external 3D-generation provider or replace construction state with downloaded finished meshes.

The canonical deliverable is a standalone GLB with embedded procedural PBR textures, semantic parts, retained behavior, physics contracts, recovery evidence, and a separate showcase GLB plus inspection viewer.

## Scope 0 — Detailed task lamp

Scope 0 established the geometry kernel and delivery contract with one close-inspectable articulated task lamp:

```bash
python -m objectforge.task_lamp --output ./objectforge-task-lamp
```

See `SCOPE_0_TASK_LAMP.md`.

## Scope 1 — Grammar-driven detailed assets

Scope 1 introduces shared support, shell, articulation, repetition, joinery, surface-detail, and material grammars. It builds nine assets across three families:

- lamps: compact, domestic, industrial;
- cases: electronics, presentation, tool;
- tables: four-leg, metal-frame, pedestal.

```bash
python -m objectforge.scope1 --output ./objectforge-scope1
```

Build one variant:

```bash
python -m objectforge.scope1 --output ./tool-case --family case --variant tool
```

## Scope 2 Revision 2 — Goal-directed functional construction

Scope 2 accepts functional goals and constraints without a named object class, compares eight bounded architecture alternatives, and composes the selected result from shared construction grammars.

Revision 2 supersedes the first Scope 2 visual benchmark. Functional coverage alone no longer qualifies an object. Proportions, joinery, controls, secondary detail, material differentiation, and underside or back completion must pass an independent close-inspection gate.

```bash
python -m objectforge.scope2 --output ./objectforge-scope2
```

Each asset package contains:

```text
object/
  object.glb
  semantic-parts.json
  materials.json
behavior/
  physics.json
  animations.json
  interactions.json
showcase/
  object-showcase.glb
  viewer/index.html
construction/
  functional-brief.json
  functional-plan.json
  candidate-comparison.json
  operations.jsonl
evaluation/
  requirement-coverage.json
recovery/
  receipt.json
validation.json
manifest.json
```

See `SCOPE_2_FUNCTIONAL_CONSTRUCTION.md`.

## Test

```bash
pip install -e '.[test]'
pytest -q
```
