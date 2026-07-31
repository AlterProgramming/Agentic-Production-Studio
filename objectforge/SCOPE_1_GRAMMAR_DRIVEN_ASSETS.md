# ObjectForge Scope 1 — Grammar-Driven Detailed Assets

Scope 1 advances ObjectForge from one detailed task-lamp benchmark to a reusable object-construction language.

The system now plans and constructs nine standalone assets across three families:

- lamps: compact, industrial, domestic;
- cases: tool, electronics, presentation;
- tables: four-leg, pedestal, metal-frame.

Each asset is assembled from shared functional grammars rather than a downloaded or externally generated finished mesh:

- support and stability;
- shell and cavity;
- articulation;
- repetition;
- joinery;
- surface detail;
- procedural PBR material assignment.

Every variant produces a canonical GLB, a separate showcase GLB, embedded textures, semantic parts, construction operations, physics and interaction contracts, recovery evidence, validation, and an inspection viewer.

## Run

```bash
python -m objectforge.scope1 --output /tmp/objectforge-scope1
```

Build one asset:

```bash
python -m objectforge.scope1 --output /tmp/tool-case --family case --variant tool
```

## Acceptance

Scope 1 passes only when:

1. all nine assets reopen as standalone GLBs;
2. each family has three materially and structurally distinct variants;
3. shared grammar modules are reused across families;
4. movable objects retain animations and physics constraints;
5. each family demonstrates a targeted failed edit, rollback, and bounded recovery;
6. no asset uses an external finished-model generation provider;
7. Scope 0 remains green.
