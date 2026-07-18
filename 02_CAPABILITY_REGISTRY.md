# Capability Registry

## Readiness definitions

- **Active:** Can be sold after one internal benchmark passes.
- **Conditional:** Sell only when the client provides specific inputs or the scope is restricted.
- **Development:** Build evidence before external sale.

| Capability | Readiness | Sellable outcome | Required evidence | Main constraint |
|---|---|---|---|---|
| Original pixel-art generation | Active | Characters, props, icons, tiles, effects | Style-match benchmark and palette QA | Requires approved style and complexity cap |
| Original raster asset generation | Active | Illustrated production assets and variants | Layered-source and export benchmark | Avoid open-ended art direction |
| Godot-ready packaging | Active | Tested scenes, SpriteFrames, imports, pivots, TileSets | Clean-project import test | Must define supported Godot version |
| Sprite animation | Active | Looping and one-shot frame sequences | Timing, drift, silhouette, and playback QA | Frame count and complexity must be capped |
| Multi-frame VFX overlays | Active | Impact, glow, particle, transition, and ambient effects | Alpha, blend, loop, and readability tests | Effects must fit target background and palette |
| Static-plus-effect workflows | Active | Reusable motion from approved static artwork | Before/after and layer-reuse benchmark | Base art must be high enough quality |
| AI-assisted animation polishing | Conditional | Cleanup, interpolation support, consistency correction | Side-by-side quality evaluation | Human correction remains required |
| Compositing and final-frame assembly | Active | Complete rendered animation sequences | No flicker, drift, broken arcs, or alpha artifacts | Target color and export rules required |
| Provenance and asset manifests | Active | Traceable source, process, license, and delivery records | Complete sample manifest | Client must disclose source ownership |
| Rapid one-week prototypes | Active | Visual or interactive proof | Three timed internal sprints | Scope lock is mandatory |
| Hugging Face model evaluation | Conditional | Reproducible model comparison | Test suite, rubric, cost and latency report | Client dataset and evaluation criteria required |
| Adapter configuration | Development | Configured style or task adapter experiment | Successful controlled benchmark | Rights and training data must be verified |
| Managed model deployment | Conditional | Private endpoint or repeatable job workflow | Deployment and rollback test | Infrastructure and security scope must be explicit |
| Agentic research-to-deliverable workflows | Active | Sourced brief, production plan, package, and evidence ledger | End-to-end case study | Research boundaries and source quality required |
| Lightweight technical integration | Active | Import, scene assembly, export automation, handoff | Target-platform integration test | Not a substitute for full product engineering |
| White-label agency production | Development | Confidential overflow sprint | NDA-ready process and partner benchmark | Requires trust, responsiveness, and consistent capacity |

## Capability groupings

### A. Visual Creation
- Pixel art
- Raster illustration
- Icons and props
- Backgrounds and layered scenes
- Palette and silhouette control

### B. Motion and Effects
- Frame-by-frame animation
- Loop design
- Impact and transition effects
- Ambient overlays
- Static-to-motion treatments
- Compositing and temporal cleanup

### C. Technical Packaging
- Godot imports
- SpriteFrames and animation libraries
- TileSets and layered scenes
- Naming, pivots, anchors, dimensions, and optimization
- Runtime and source-folder separation

### D. Production Intelligence
- Research and reference analysis
- Model and workflow evaluation
- Brief generation
- Acceptance-criteria design
- Evidence and decision logs

### E. Delivery Governance
- Asset manifests
- Provenance
- Revision history
- Rights declarations
- QA evidence
- Handoff documentation
