# GarmentForge

`GarmentForge.clothing_construction.v1` adds retained, detachable textile assets to the model-first construction stack.

The runtime builds one dressed-character GLB and four independently reusable textile GLBs:

- a panel-built tunic with separate sleeves;
- a pleated wrap skirt;
- a draped mantle that can also be reused as scene textile decoration;
- a hanging architectural textile.

Each asset includes geometry, normals, UVs, embedded procedural weave and normal maps, a glTF skin, attachment/collision metadata, panel and seam metadata, and secondary textile joints. The system GLB preserves three scene states: dressed, body-only, and detached garment gallery.

## Build

```bash
python -m garmentforge.cli --output build/garmentforge
python -m garmentforge.validate build/garmentforge
```

Serve the package and open `viewer/index.html`, or choose a generated GLB directly in the viewer file picker.

## Evidence boundary

This is a bounded retained-garment runtime, not a painted clothing layer. It proves detachable assets, skinned fit, material response, independent secondary motion, re-dressing, and reuse as decor. It does not claim continuum cloth simulation, tailoring-grade 2D patterns, manufacturing fit certification, or a proprietary CLO/Marvelous Designer project file.
