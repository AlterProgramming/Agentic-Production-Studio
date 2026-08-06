# GarmentForge retained-clothing benchmark

The fixed benchmark exercises clothing as an actual model-first capability rather than an image treatment.

## Matrix

- one embodied mannequin with a reusable humanoid skin;
- tunic, wrap skirt, mantle, and hanging textile;
- one assembled GLB with dressed, body-only, and detached-gallery scenes;
- four standalone garment GLBs;
- ten embedded procedural fabric images;
- one body-motion clip with eight secondary textile joints.

## Blocking checks

The benchmark fails on fused body/garment ownership, missing UVs or skin weights, external texture URIs, absent garment construction metadata, absent independent textile motion, fewer than three retained scene states, or a missing standalone garment export.

The intended independent verification path is: Khronos glTF Validator for specification conformance, Babylon.js Sandbox for animation/material/node inspection, and Blender for direct rig, mesh, material, and weight manipulation.
