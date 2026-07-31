# ObjectForge

ObjectForge creates retained, runtime-ready 3D objects through first-party procedural construction. The canonical output is a standalone GLB with embedded PBR materials and textures, semantic parts, behavior and physics contracts, recovery evidence, and a separate showcase model plus inspection viewer.

It does not call an external finished-model generator or replace the construction history with a downloaded mesh.

## Scope 0 — Detailed standalone task lamp

Scope 0 established the geometry kernel, retained behavior, PBR delivery, recovery, and standalone-viewer contract.

```bash
python -m objectforge.task_lamp --output ./objectforge-task-lamp
```

## Scope 1 — Reusable construction grammars

Scope 1 introduced reusable support, shell, articulation, repetition, joinery, detail, and material grammars across nine assets in three bounded families.

```bash
python -m objectforge.scope1 --output ./objectforge-scope1
```

## Scope 2 Revision 2 — Goal-directed functional construction

Scope 2 accepts functional goals and constraints without a named object class, compares eight bounded architecture alternatives, and constructs the selected architecture from shared grammars.

Revision 2 adds an independent close-inspection gate. Functional coverage alone no longer qualifies an object: proportions, joinery, controls, secondary detail, material differentiation, and underside or back completion must also pass.

```bash
python -m objectforge.scope2 --output ./objectforge-scope2
```

## Scope 3 — Procedural design language

Scope 3 keeps the functional architecture fixed while applying persistent product DNA across multiple object purposes. Design languages control material roles, proportion and detail scale, seam and fastener strategy, handles, controls, labels, vents, interaction signaling, and modeled signature motifs.

The fixed benchmark applies two languages—Field Service and Precision Lab—to the same four functional briefs, producing eight canonical GLBs.

```bash
python -m objectforge.scope3 --output ./objectforge-scope3
```

Render retained-model comparison previews:

```bash
pip install -e '.[preview]'
python -m objectforge.preview_scope3 \
  --input ./objectforge-scope3 \
  --output ./objectforge-scope3-previews
```

See `SCOPE_3_PROCEDURAL_DESIGN_LANGUAGE.md`.

## Test

```bash
pip install -e '.[test]'
pytest -q
```
