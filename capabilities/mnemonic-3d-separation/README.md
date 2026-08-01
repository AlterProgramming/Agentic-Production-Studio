# Mnemonic Body-Artifact 3D Separation

This capability extends the model-first visual doctrine with independent embodied, artifact, interaction, provenance, and hypothesis layers.

## Current implementation level

Implemented:

- machine-readable capability manifest;
- scene schema;
- dependency-free validator;
- valid benchmark fixture;
- regression tests and GitHub Actions gate.

Not yet implemented or claimed:

- production skinned-body generation;
- cloth or garment physics runtime;
- automatic reconstruction from memory evidence;
- deployed BrightEngine execution endpoint;
- recipient-tested interactive 3D delivery.

## Validate

```bash
python3 capabilities/mnemonic-3d-separation/validate_scene.py \
  benchmarks/mnemonic-separation-contract/example.scene.json

python3 -m unittest discover \
  -s capabilities/mnemonic-3d-separation/tests \
  -p 'test_*.py' -v
```

A later runtime may consume this contract, but it must preserve the separation and evidence rules rather than treating the schema as permission to claim completed 3D generation.
