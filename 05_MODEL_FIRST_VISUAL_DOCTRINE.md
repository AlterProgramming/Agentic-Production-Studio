# Model-First Visual Doctrine

## Canonical rule

> A generated image is a view of a retained scene, not the terminal artifact.

Meaningful visual generation defaults to a model-first workflow:

```text
intent
  -> structured scene specification
  -> reusable model and scene graph
  -> validation and recovery
  -> persisted scene package
  -> still render
  -> motion, speech, alternate views, relighting, and interaction
```

A flat image-only path is a deliberate lightweight exception. It may be chosen when continuity, alternate views, motion, speech, relighting, simulation, or interaction are not expected and the retained-scene cost is not justified.

## Required retained state

For meaningful visual work, preserve as applicable:

- named scene and object structure;
- reusable geometry and materials;
- cameras and lighting definitions;
- semantic object labels and transforms;
- character rigs, poses, facial controls, and visemes;
- beauty, depth, normal, object-ID, and mask passes;
- validation, recovery, and quarantine results;
- provenance tying every render and derivative to the modeled scene.

## Product boundary

### AvatarForge

AvatarForge is the reusable character foundation. It provides rigged character assets, named skeletons, body controls, facial morphs, visemes, poses, movement, speech coordination, and character-level recovery.

### SceneForge

SceneForge is the scene layer. It turns intent into a structured scene, assembles characters, environments, props, cameras, and lights, persists the modeled scene before rendering, validates the reopened model, and produces still and experiential derivatives.

### Agentic Production Studio

The studio packages the combined capability as bounded production work. It owns scope, acceptance criteria, visual quality, evidence, packaging, and handoff. It must not sell a still-image claim when the accepted deliverable requires retained scene continuity.

## Minimum delivery contract

A model-first scene delivery should contain:

```text
scene/
  scene.glb
  scene.json
  graph.json
  manifest.json
  recovery.json
assets/
  characters/
  props/
  environments/
renders/
  hero.png
  depth.png
  object_mask.png
motion/
  orbit.mp4
  animations.json
preview/
  index.html
```

Not every package requires every optional asset, but the manifest must state what was retained, rendered, omitted, recovered, or quarantined.

## Quality gates

The still render is accepted only after the persisted model or scene has passed the relevant gates:

1. **Geometry:** finite positions, valid indices, sane bounds, usable normals and UVs.
2. **Textures and materials:** resolved maps, sane dimensions, contamination and seam checks, compatible alpha modes.
3. **Rig and morphs:** valid bind state, finite skinning, named controls, stable pose and speech deformation.
4. **Scene:** visible subject, usable framing, camera outside geometry, coherent light rig, no empty or occluded hero view.
5. **Recovery:** known corruption repaired where possible; unresolved output quarantined rather than silently delivered.
6. **Provenance:** render and derivative hashes resolve to the retained modeled scene.

## Readiness rule

Model-first visual generation is a **Foundation** capability until the studio retains a reproducible benchmark demonstrating:

- prompt or brief to structured scene;
- persistent scene model written before rendering;
- successful reopen and validation;
- hero, depth, and object-ID outputs;
- at least one motion or interactive derivative;
- a recovery receipt for a deliberately corrupted input;
- a complete packaged handoff.

After that benchmark passes under a bounded service definition, the capability may be promoted to **Active**.

## Canonical reference

This doctrine implements `visual-generation.model-first.v1` from the Agent Command Center canonical-state registry. Repository code, benchmarks, and packages are implementation evidence; the active canonical entry governs the durable direction.
