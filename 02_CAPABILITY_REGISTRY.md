# Capability Registry

## Readiness definitions

- **Active:** Can be sold after one internal benchmark passes.
- **Conditional:** Sell only when the client provides specific inputs or the scope is restricted.
- **Development:** Build evidence before external sale.
- **Foundation:** Implemented as internal infrastructure; must be exercised by package benchmarks before it is treated as a sellable outcome.

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
| Model-first scene generation | Foundation | Persistent modeled scene, hero render, render passes, motion or interactive derivatives | Reproducible brief-to-scene benchmark with reopen validation, recovery receipt, and packaged handoff | Doctrine is canonical, but the complete runtime is not yet injected into arbitrary assistant sessions; availability must be discovered and proven per session |
| Retained-scene character performance | Foundation | Independent character action, reaction, gesture, gaze, and positional change inside a persistent scene | Named-node displacement measurements, authored performance beats, camera-only negative test, and motion receipt | Current benchmark uses articulated proxy rigs; hero deformation, facial acting, and cloth simulation remain later gates |
| White-label agency production | Development | Confidential overflow sprint | NDA-ready process and partner benchmark | Requires trust, responsiveness, and consistent capacity |
| Surgical builder planning | Foundation | Exact write-set preview with preconditions and postconditions | Builder regression suite and one real benchmark receipt | Plans must remain narrow and inspectable |
| Guarded metadata mutation | Foundation | Exact text and JSON changes without broad rewrites | Stale-state rejection tests | Requires explicit expected current values |
| Transactional workspace application | Foundation | Multi-file changes applied only after full simulation | Rollback and failed-postcondition tests | Filesystem transactions are emulated through backup and restore |
| Builder evidence receipts | Foundation | Plan hash, operation list, and before/after artifact hashes | Apply-and-verify benchmark | Receipts prove file state, not artistic quality |
| Anchor-aware image normalization | Foundation | Exact RGBA canvas and anchor placement | Real Storm normalization receipt and visual inspection | Does not yet enforce palette or silhouette rules |

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

### F. Surgical Builder Infrastructure
- Workspace path confinement and output allowlists
- Dry-run write sets and unified text diffs
- Guarded exact text replacement
- Guarded JSON pointer updates
- Checksummed copy and deletion
- Transactional apply and rollback
- Plan and artifact hash receipts
- Drift verification
- Registered domain-specific operations
- Anchor-aware deterministic image normalization

### G. Model-First Visual Systems
- Prompt or brief to structured scene specification
- Persistent scene and reusable model creation before final rendering
- AvatarForge character, rig, pose, movement, and speech integration
- SceneForge environment, prop, camera, and lighting assembly
- Independent character performance with measured body-node displacement
- Beauty, depth, normal, mask, and object-ID render passes
- Motion, alternate-view, relighting, and interactive derivatives
- Geometry, texture, rig, scene, and render recovery gates
- Hash-linked provenance from modeled scene to every derivative

## Executable availability is separate from doctrine

`visual-generation.model-first.v1` is a canonical production doctrine. That does not make its runtime globally available to every assistant session.

A session may claim the capability only after it:

1. retrieves `capabilities/model-first-visual-generation/capability.json`;
2. materializes a listed first-party entrypoint;
3. executes it successfully;
4. writes the retained model before the accepted render;
5. reopens and validates the retained asset; and
6. records a completion receipt.

A session that only calls a flat-image generator has not executed Model-first scene generation. See `capabilities/model-first-visual-generation/SESSION_BOOTSTRAP.md`.
