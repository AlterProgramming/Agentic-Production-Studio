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

## Scope 4 — Multi-object coherent systems

Scope 4 advances from coherent individual products to bounded coordinated systems. It selects a system topology, builds multiple independently useful retained objects, and defines reusable physical interface standards, endpoint contracts, compatibility relationships, deployment/stowage workflows, and a combined retained system model.

The fixed benchmark is the six-object Modular Observation and Service Cell under the Field Service and Precision Lab design languages.

```bash
python -m objectforge.scope4 --output ./objectforge-scope4
```

The Scope 4 capability is registered as `objectforge.multi-object-coherent-systems.v1`. Its benchmark has passed the dedicated Scope 4 CI workflow.

See `SCOPE_4_MULTI_OBJECT_SYSTEMS.md`.

## Scope 5 — Manufacturing, assembly, and service planning

Scope 5 consumes the retained Scope 4 system plan and produces bounded manufacturing and service evidence: material/process plans for every system object, interface tolerance stacks, dependency-checked assembly and acceptance operations, service procedures for critical replaceable modules, and a low-volume cost envelope explicitly labeled as a planning estimate rather than a supplier quotation.

```bash
python -m objectforge.scope5 --output ./objectforge-scope5
```

The capability is registered as `objectforge.manufacturing-assembly-service-planning.v1`. It is planning infrastructure, not engineering certification or authorization to manufacture safety-critical hardware.

## Scope 6 — Embodied operational validation

Scope 6 adds bounded operational analysis over the Scope 4 system and Scope 5 manufacturing/service plan. It evaluates human, two-person, and mobile-manipulator capability envelopes against deploy, operate, stow, mating, and closure tasks; checks analytical load cases; injects deterministic faults with safe-state and recovery requirements; and retains the operational state machine.

```bash
python -m objectforge.scope6 --output ./objectforge-scope6
```

The capability is registered as `objectforge.embodied-operational-validation.v1`. It is bounded analytical validation only: it is not regulatory certification, a substitute for physical testing, or a claim of unrestricted robot autonomy.

## Capability manifests

Machine-readable capability manifests live in `objectforge/capability/`:

- `capability.json` — Scope 0 detailed procedural object generation
- `scope1.json` — grammar-driven detailed assets
- `scope2.json` — goal-directed functional construction
- `scope3.json` — procedural design language
- `scope4.json` — multi-object coherent systems
- `scope5.json` — manufacturing, assembly, and service planning
- `scope6.json` — embodied operational validation

## Test

```bash
pip install -e '.[test]'
pytest -q
```
