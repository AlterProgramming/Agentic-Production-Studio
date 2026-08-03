# Progressive Design System

Status: experimental canonical doctrine

## Purpose

The Progressive Design System is a production doctrine for moving model-generated interfaces beyond generic correctness without exposing the machinery used to construct them.

It does not define a house style. It defines a sequence of design capabilities and a final public-surface gate.

The working hypothesis is:

> Strong visitor-facing design emerges when structural intelligence is developed internally, tested against the material, and then translated through a mandatory reconciliation pass that conceals construction aids, implementation vocabulary, and model-default visual habits.

The system contains four layers:

1. Progressive Design
2. Spatial Intelligence
3. Private Construction Layer
4. Visitor-Facing Reconciliation

The layers are not four increasingly decorated styles. The first three develop and control design intelligence. The fourth determines what the audience is allowed to see.

---

## Operating Model

Before changing an artifact, determine the highest design level it sustains consistently. Validate lower levels quickly, then begin substantive work at the first unresolved level.

Do not distribute effort evenly across all levels. Spend most effort at the highest level the existing material can honestly support.

Every later level inherits the requirements beneath it. Advancement must not weaken content integrity, usability, accessibility, responsive behavior, performance, or strong existing decisions.

The minimum public-production sequence is:

```text
preserve substance
  -> resolve composition
  -> build coherent systems
  -> derive identity from material
  -> use interaction structurally
  -> introduce authored judgment
  -> critique against the artifact's strongest moments
  -> reconcile for the visitor
```

Spatial Intelligence is optional as a visible public language, but available as an internal capability. Visitor-Facing Reconciliation is mandatory for public release.

---

# Layer 1 — Progressive Design

## Level 1: Integrity

Confirm that the work is real, functional, legible, and internally truthful.

Preserve meaningful content, functionality, data, and existing strengths. Remove filler, fabricated material, exposed implementation rationale, accidental repetition, broken states, and elements that imitate product value without providing it.

This level is a gate, not the destination.

## Level 2: Composition

Transform arrangement into composition.

Resolve hierarchy, scale, proportion, density, negative space, alignment, sequence, focal movement, section relationships, and responsive pacing. Each page or state must have a clear visual argument rather than a stack of individually acceptable components.

Do not solve weak composition with decoration.

## Level 3: System

Create a coherent visual language without flattening the work into sameness.

Resolve typography, spacing, image treatment, color behavior, component relationships, responsive rules, interaction states, and recurring structural patterns. Repetition should establish confidence; variation should preserve vitality.

Avoid mechanically uniform cards, repeated section formulas, arbitrary alternation, dashboard aesthetics, and visible template logic.

This is the minimum default design level.

## Level 4: Identity

Allow subjects, products, projects, or sections to develop distinct identities inside the shared system.

Derive variation from actual content, imagery, function, tone, and structure. Do not assign arbitrary themes merely to make items appear different.

The system should make each subject clearer, not make every subject resemble the system.

## Level 5: Interaction

Use interaction and motion as structural instruments.

Motion may reveal hierarchy, connect states, establish rhythm, maintain orientation, or strengthen a transition. It must not delay access, compensate for weak composition, advertise technical effort, or become the primary spectacle.

Interaction should feel inevitable once experienced and largely invisible when functioning well.

## Level 6: Authorship

Move beyond correct system application.

Identify where deliberate exceptions, asymmetric decisions, unusual crops, restrained tension, selective density, silence, or a singular visual moment would make the work more memorable and truthful.

Do not pursue novelty everywhere. Authorship is judgment about where the system should hold and where it should yield.

A small number of consequential decisions is stronger than continuous expressiveness.

## Level 7: Critique and Elevation

Judge the work against its own strongest moments, not against generic adequacy.

Locate components or pages that are functional but less resolved than the best existing work. Determine whether the weakness comes from composition, hierarchy, identity, imagery, interaction, typography, or excessive conformity.

Continue until quality variation feels intentional rather than accidental.

## Stable Defaults

Assume the following unless the material proves otherwise:

- Real content is more valuable than added content.
- Composition should be solved before ornament.
- Typography and spacing carry more weight than effects.
- Responsive behavior is part of composition, not a later adaptation.
- Motion must communicate structure.
- Variation must arise from meaning.
- Strong existing decisions should be preserved.
- Decorative complexity requires stronger justification than removal.
- Familiar patterns may be used, but familiar outcomes are insufficient.
- A design is unfinished when it is merely consistent, clean, or technically impressive.

## Anti-Regression Rules

- Do not replace a distinctive existing solution with a safer generic one.
- Do not normalize every section into the same component grammar.
- Do not equate increased polish with more gradients, animation, layers, copy, rounded containers, glow, or visual effects.
- Do not expose design process, implementation status, verification logic, or internal rationale unless it is genuinely the subject.
- Do not declare completion from code quality or verbal reasoning alone. Review the rendered artifact across representative viewport sizes and interaction states.

---

# Layer 2 — Spatial Intelligence

## Purpose

Do not confuse visible construction devices with spatial design.

Grids, lines, dots, coordinate fields, technical diagrams, and repeated geometric textures may be useful during composition, but they are not automatically appropriate as visitor-facing aesthetics.

The progression is:

```text
visible scaffold
  -> disciplined scaffold
  -> latent structure
  -> semantic geometry
  -> adaptive spatial field
  -> authored deviation
```

The grid should gradually disappear as an object while remaining present as intelligence.

## Level 1: Explicit Scaffold

Use a visible grid or construction field to establish basic alignment, scale, spacing, and proportion.

At this level, the scaffold is an authoring instrument. It is not the finished visual identity.

A design that depends on visible background geometry to feel organized has not advanced beyond this level.

## Level 2: Disciplined Scaffold

Resolve the underlying column system, baseline rhythm, focal axes, spacing intervals, and responsive boundaries.

Reduce visible geometry to portions that perform a clear visual or informational role.

Do not repeat the same grid treatment across unrelated products merely because it produces an immediate impression of structure.

## Level 3: Latent Structure

The spatial system should remain legible after visible construction lines are removed.

Alignment, hierarchy, image scale, negative space, sectional pacing, and repeated proportions should communicate the underlying geometry without drawing it.

Verification question:

> Would the composition still feel deliberate if every decorative grid line, dot field, and technical background texture were removed?

If not, continue resolving the structure.

## Level 4: Semantic Geometry

Derive spatial behavior from the subject rather than from a default layout effect.

Examples:

- chronological material may produce sequential movement;
- relational material may produce connected or clustered structures;
- comparative material may produce parallel or opposing arrangements;
- exploratory material may produce branching navigation;
- cinematic material may produce framing, reveal, and controlled depth;
- archival material may produce indexing, sequencing, and documentary rhythm.

Do not use a geometric metaphor merely because it is attractive. It must improve understanding.

## Level 5: Adaptive Spatial Field

Allow the spatial system to respond meaningfully to viewport, interaction, content density, and user state.

Responsive design should not merely collapse the desktop grid. It should preserve hierarchy and intent through a composition appropriate to the available space.

Motion should follow the same structural field. Elements should move along meaningful relationships rather than entering independently through generalized reveals.

## Level 6: Authored Deviation

Once the spatial system is stable, introduce deliberate exceptions.

A section may break alignment, expand beyond the established measure, interrupt rhythm, change density, or suspend the dominant geometry when doing so creates meaningful emphasis.

Deviation is recognizable as intentional because the surrounding system is coherent. Random asymmetry is not authorship.

## Geometry Budget

Public geometry must improve at least one of:

- orientation;
- comparison;
- sequence;
- causality;
- scale;
- spatial understanding.

If it does not, keep it private.

## Anti-Convergence Rules

Do not default publicly to:

- graph-paper backgrounds;
- chalkboard line systems;
- technical dot matrices;
- blueprint overlays;
- arbitrary orbital paths;
- coordinate labels;
- glowing node networks;
- repeated perspective grids.

When the same treatment can move unchanged to an unrelated product, it is probably a model default rather than an authored decision.

---

# Layer 3 — Private Construction Layer

## Purpose

Maintain an authoring representation that can be rich, explicit, diagnostic, and machine-readable without leaking onto the public surface.

The agent may use:

- columns and gutters;
- baseline and spacing rhythm;
- focal and alignment axes;
- density and silence zones;
- section boundaries;
- image crop guides;
- responsive transformation points;
- interaction and motion paths;
- hierarchy maps;
- repeated-pattern detection;
- component classifications;
- breakpoint diagnostics;
- verification notes.

This layer may be visible during authoring, rendering, and evaluation. It must remain disabled in production unless a particular part has earned a real visitor-facing function.

Recommended implementation boundary:

```html
<html data-design-debug="false">
```

Debug geometry may be activated locally through a development-only flag, query parameter, or non-production stylesheet. Production builds must default to `false` and must not require the debug layer to feel composed.

## Private/Public Split

Internal:

- construction grids;
- alignment guides;
- breakpoint indicators;
- component names;
- design-level assessments;
- density maps;
- motion paths;
- verification status;
- agent instructions;
- publishing notes;
- implementation terminology.

Potentially public:

- meaningful content;
- navigation;
- imagery;
- actions;
- useful status information;
- understandable relationships;
- intentional divisions;
- interaction feedback;
- necessary context.

Anything created primarily to help the agent understand, construct, verify, or explain the design remains internal.

---

# Layer 4 — Visitor-Facing Reconciliation

## Purpose

Reconcile structural intelligence with the final public surface.

Internal complexity should produce external clarity. The visitor should experience the consequences of good reasoning, not the reasoning itself.

This is not a decorative polish pass. It is the translation stage where composition, systems, spatial logic, identity, and interaction become a coherent human experience.

## Level 1: Public Boundary

Separate every element into internal or public categories.

No internal reasoning, diagnostic labels, authoring geometry, implementation status, design rationale, or agent vocabulary may remain merely because it helped build the artifact.

## Level 2: Surface Coherence

Translate the skeleton into a coherent surface through typography, image treatment, color relationships, contrast, edge behavior, material qualities, spacing, density, transitions, interactive states, and responsive continuity.

The surface must not resemble a generic skin placed over a sophisticated skeleton.

## Level 3: Perceptual Communication

Replace explanation with perception.

The visitor should understand what matters first, what belongs together, what is interactive, where they are, what changes between sections, and what action is available.

Do not add labels when hierarchy, composition, language, or interaction can communicate the same information more naturally.

## Level 4: Visitor Rhythm

Compose from the visitor's point of view:

- first visual impression;
- first readable statement;
- first meaningful action;
- transition into deeper content;
- alternation between density and rest;
- pacing of imagery, text, and interaction;
- emotional effect of the ending.

The page should not expose the order in which it was built. Sections should feel discovered in a deliberate sequence, not encountered as completed modules stacked together.

## Level 5: Surface Character

Give the public experience a specific character arising from the material.

Character may emerge through typography, scale, framing, cropping, rhythm, restraint, texture, contrast, motion, image sequencing, or an appropriate spatial decision.

Do not express character through a collection of fashionable effects. The surface should remain specific after decorative treatments are removed.

## Level 6: Finish and Sensitivity

Resolve the small decisions through which visitors perceive quality:

- text wrapping and line length;
- optical alignment;
- crop quality;
- icon weight;
- border and edge behavior;
- transition timing;
- hover, focus, loading, and empty states;
- mobile spacing and touch targets;
- reduced-motion behavior;
- contrast and legibility;
- sharpness and visual noise.

These are not secondary concerns. They determine whether the underlying design intelligence feels credible.

## Level 7: Concealment

Perform a final concealment pass.

Ask:

- Is any element explaining what the visitor should already perceive?
- Is any background primarily a construction aid?
- Is any label present mainly because the system generated it?
- Is any status visible because the agent verified it rather than because the visitor needs it?
- Is any motion demonstrating implementation effort?
- Is any section describing its own design role?
- Is any visual device signaling sophistication rather than contributing meaning?
- Does the page reveal the model's preferred design vocabulary?

Remove or transform these elements. The final artifact should not narrate its own competence.

## Level 8: Reconciliation

Compare the public surface against the internal design intention.

Translate internal representations as follows:

- grids become alignment and rhythm;
- hierarchy maps become perceptual priority;
- spatial models become meaningful relationships;
- motion paths become orientation and continuity;
- component systems become consistency;
- critique becomes resolved form;
- identity rules become distinctive character;
- accessibility requirements become effortless usability.

Do not expose the internal representation merely because public translation is difficult.

## Surface Contract

A public artifact must satisfy:

1. No internal reasoning is visible.
2. No implementation language is presented as content.
3. No construction aid remains unless it has a genuine public function.
4. No element exists mainly to demonstrate sophistication.
5. No visual treatment substitutes for unresolved hierarchy.
6. No section explains its own composition.
7. No interaction advertises the technology producing it.
8. No visitor must understand the system before understanding the subject.
9. Strong structural decisions remain perceptible after scaffolding is hidden.
10. The surface feels authored, finished, and natural.

## Visitor Tests

### Five-Second Test

Can a visitor identify what this is, what deserves attention, the emotional register, and where to go next without explanation?

### Removal Test

Remove grids, glow, gradients, animation, badges, labels, and decorative containers. Does the composition remain strong?

### Silence Test

Remove all text explaining design, process, status, or implementation. Does the experience become clearer?

### Transfer Test

Could the same surface treatment move nearly unchanged to an unrelated product? If so, identity is insufficiently derived from the material.

### Distance Test

At thumbnail scale, is hierarchy still visible through mass, rhythm, contrast, and proportion?

### Close-Range Test

Under inspection, do typography, crops, edges, states, and transitions remain credible?

---

# Completion Standard

A design is ready for public release when:

- substance remains intact;
- hierarchy is unmistakable;
- the system is coherent without appearing templated;
- subjects retain individual presence;
- interaction improves understanding;
- responsive states preserve intent;
- strong decisions feel intentional and difficult to replace;
- internal rigor is visible only through the quality of the result;
- meaning arrives before mechanism;
- structure works without visible scaffolding;
- character works without fashionable decoration;
- motion works without drawing attention to itself.

The final experience should conceal the labor without losing the intelligence.

---

# Current Evidence Status

The doctrine is provisionally supported by two same-model sandbox comparisons:

1. A student-exchange information experience showed that Progressive Design changed the decision structure beyond baseline polish.
2. A municipal permit pre-check showed that Spatial Intelligence increased control but did not improve the public surface by itself; a Visitor-Facing Reconciliation pass was decisively preferred while preserving the stronger skeleton.

This evidence is directional, not conclusive. Cross-domain, fresh-session testing is required. See `benchmarks/progressive-design/README.md`.