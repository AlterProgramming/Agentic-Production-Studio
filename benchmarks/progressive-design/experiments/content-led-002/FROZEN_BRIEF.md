# Frozen Brief — Apollo 11 Learning Paths

Experiment: `content-led-002`  
Task family: `content-led`  
Setup status: frozen input

## Product problem

Create a public educational web experience that helps a curious visitor understand Apollo 11 without requiring prior spaceflight knowledge.

The material is rich enough to support several kinds of inquiry. A visitor may want a concise orientation, a chronological account of the mission, or an explanation of how the people and spacecraft worked together. The product must help the visitor choose one of those learning paths and then follow it without losing access to the wider archive.

## Audience

Primary visitors are general readers, students, educators, and museum or science-center visitors using desktop or mobile devices.

Assume no specialist vocabulary. Define necessary terms in ordinary language. Preserve factual precision without presenting the experience as an engineering manual.

## Required visitor decision

The primary meaningful decision is the selection of one learning path:

- **Quick orientation** — a concise account of what happened and why the mission mattered.
- **Mission sequence** — a chronological route from launch through lunar operations and return.
- **People and systems** — an explanation of crew roles, spacecraft modules, and how responsibilities changed through the mission.

The visitor must be able to change or clear the selection. The selection must alter the recommended sequence or emphasis of content rather than act as a decorative preference.

## Required content

Use the frozen copy and data fixtures without changing their factual meaning.

The public experience must include:

- a concise Apollo 11 overview;
- the three crew members and their mission roles;
- the Saturn V launch vehicle;
- the Command and Service Module `Columbia`;
- the Lunar Module `Eagle`;
- a chronological mission sequence;
- lunar surface activities;
- return and recovery;
- a collection of evidence or artifacts that connects records to mission events;
- source acknowledgements and image provenance.

Do not invent quotations, mission records, measurements, artifacts, or personal testimony.

## Required routes

The route contract is authoritative. The product must provide distinct, directly addressable views for:

- overview and learning-path selection;
- mission sequence;
- people;
- spacecraft;
- artifacts and sources.

Routes may share navigation, but each must be meaningful when opened directly.

## Required states and interaction

The experience must support:

- no learning path selected;
- one learning path selected;
- selected path changed;
- selected path cleared;
- mission milestone detail opened and closed;
- artifact detail opened and closed;
- keyboard focus visible;
- reduced-motion preference;
- a narrow mobile viewport in which the learning-path decision and detail interactions remain usable.

State may be retained during the current visit. Accounts, authentication, analytics, forms, external APIs, and server persistence are not required.

## Content and implementation boundaries

- Use only the frozen copy, data, diagrams, and sources supplied with this experiment.
- All required content must remain available without a network connection after installation.
- Do not add a shared starter site, component library, CSS system, layout template, visual identity, or generated reference implementation.
- Do not expose benchmark terminology, implementation notes, agent reasoning, verification labels, or condition names in the visitor-facing product.
- Do not treat external source pages as required runtime dependencies.
- The product must be independently runnable from its assigned `source/` directory.
- The product may use a framework or a dependency-light implementation, provided its dependency and build instructions are committed.
- The experience must not imply NASA endorsement.

## Approved imagery

Six setup-authored factual diagrams are supplied in `fixtures/images/`. They are immutable benchmark inputs and may be displayed at any suitable size or crop that preserves their meaning. Each has approved alternative text and provenance in `fixtures/images/provenance.json`.

The diagrams are informational assets, not a required visual system. They do not prescribe the page composition, component structure, typography, palette, grid, visual metaphor, layout, motion, or editorial treatment.

## Accessibility and responsive requirements

The binding requirements are in `ACCESSIBILITY_RESPONSIVE.md`.

## Implementation and evidence

Every condition receives the same implementation budget in `IMPLEMENTATION_BUDGET.md` and the same evidence contract in `EVIDENCE_REQUIREMENTS.md`.

## Deliberately unspecified design decisions

This brief does not prescribe:

- composition;
- components;
- typography;
- palette;
- grid;
- visual metaphor;
- page layout;
- motion style;
- historical aesthetic;
- editorial aesthetic;
- card treatment;
- border radius;
- illustration placement;
- navigation pattern beyond route and state obligations.

Those decisions belong to the assigned implementation session.
