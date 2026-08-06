# GarmentForge v2

`GarmentForge.clothing_construction.v2` replaces the original uniform-grid proxy with a bounded retained garment pipeline.

Each garment now has two separately owned surfaces:

- a coarse simulation cage whose source representation is quad-oriented and whose GLB derivative is triangulated only for interchange;
- an adaptive visible surface with variable row density, smooth skin-weight fields, UVs, normals, and garment-specific base, normal, roughness, and sheen response.

The tunic cage retains ordered vertex-pair sewing constraints for its front, back, and sleeve boundaries. Wrap, mantle, and hanging-textile closures remain explicitly typed as overlap, fastener, or pinned-boundary constraints instead of being falsely welded. The body uses a plain skin material and no textile maps.

The system GLB preserves four verification states: dressed, body-only, detached render surfaces, and simulation cages with seams. `viewer/construction.html` reveals the already-continuous render surface with a shader-driven UV coverage mask; it never spawns partial geometry.

## Build

```bash
python -m garmentforge.cli --output build/garmentforge
python -m garmentforge.validate build/garmentforge
```

## Evidence boundary

Implemented: explicit seam mappings, cage/render separation, adaptive variable-row topology, smooth deformation fields, garment-specific macro/micro material variation, plain body shading, detached assets, and a coverage-based construction reveal.

Not claimed: a continuum cloth solver, production collision resolution, tailoring-grade patterns, manufacturing fit certification, or native CLO/Marvelous Designer project export.
