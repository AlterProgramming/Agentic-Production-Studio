# ObjectForge Scope 0 — Detailed Standalone Task Lamp

ObjectForge starts from declared constructive matter and develops a complete runtime asset through explicit geometry operations. It does not call an external 3D-generation provider and does not replace the construction state with a downloaded finished mesh.

The first bounded benchmark builds an articulated task lamp because it requires support, reach, cavities, close-view manufacturing detail, embedded PBR textures, light emission, joint limits, collision proxies, and recovery from a structurally bad edit.

## Outputs

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
  initial-field.json
  operations.jsonl
recovery/
  receipt.json
validation.json
manifest.json
```

`object.glb` is the canonical reusable asset. `object-showcase.glb` contains the same asset with an inspection stage, camera, and lights. The GLB contains embedded procedural textures, PBR materials, three articulated pivots, an animation clip, a punctual emitter, semantic metadata, and physics references.

## Run

```bash
python -m objectforge.task_lamp --output ./objectforge-task-lamp
```

## Test

```bash
pip install -e '.[test]'
pytest -q
```
