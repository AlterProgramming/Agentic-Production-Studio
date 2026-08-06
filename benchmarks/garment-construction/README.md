# GarmentForge v2 retained-clothing benchmark

The benchmark blocks the uniform-grid proxy architecture that v1 exposed.

## Required construction layers

- one embodied mannequin with a non-textile body material;
- one coarse simulation cage per textile family;
- one separately owned adaptive render surface per textile family;
- explicit ordered seam pairs for the tunic cage;
- typed overlap, fastener, or pinned-boundary constraints where welding would be incorrect;
- smooth skin fields and secondary textile joints;
- garment-specific base, normal, roughness, and sheen response;
- a UV coverage-mask construction reveal that never spawns topology.

## Retained states

- dressed character and textile decor;
- body-only verification;
- detached adaptive render surfaces;
- simulation cages and seam verification.

The benchmark fails on textile maps assigned to the body, uniform render-row density, missing cage/render separation, missing tunic seam pairs, fewer than ten distinct render-weight vectors, external texture URIs, or a construction animation that exposes partial geometry.
