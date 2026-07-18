# Studio Composition Workbench

A browser-based visual compiler for Agentic Production Studio workflows.

The workbench evolves the reusable architecture demonstrated by the MIT-licensed Witch Hat Atelier Spell Simulator:

```text
freehand strokes
  → cleaned geometry
  → scope and symbol recognition
  → StudioGlyphAST
  → StudioIR
  → surgical-builder plan
  → preview, apply, receipt, verify
```

It does **not** include Witch Hat Atelier names, artwork, sigils, signs, or effect assets. The visual vocabulary is an original generic production grammar.

## Run

Serve the repository root with any static server, then open:

```text
/studio_workbench/
```

For example:

```bash
python3 -m http.server 8000
```

## Grammar

One large closed loop defines the production scope. Place operators clockwise inside it:

- circle — input asset
- triangle — anchor-aware normalization
- square — palette enforcement
- diamond — contact-sheet generation
- arrow — Godot `SpriteFrames` compilation
- zigzag — deterministic packaging

Modifiers:

- plus — strict diagnostics policy
- check — evidence/postcondition policy
- parallel lines — parallelization intent for a future graph executor

## Operator Lab

Open `/studio_workbench/operator-lab.html` to author a new recognition template without editing parser code. The lab:

- captures one or more freehand strokes;
- resamples them to deterministic point counts;
- normalizes translation and scale while retaining aspect ratio;
- reconstructs saved templates for inspection;
- exports a dictionary entry with recognition and builder semantics.

The main workbench can import an array of these entries, or an object with an `entries` array. Optional rotation-invariant matching tries deterministic rotational samples. Multi-stroke entries tolerate stroke-order and stroke-direction differences for small templates. Low-confidence matches remain unknown diagnostics.

## Contracts

### `StudioGlyphAST`

Parser facts: scope geometry, recognized candidates, unknown marks, quality, and warnings.

### `StudioIR`

Compiled behavior: ordered stages, validity, policy modifiers, quality, warnings, and stable composition signature.

### Builder plan

The final compiler maps recognized stages plus explicit execution bindings into the existing Surgical Builder Plan v1 contract. Missing paths or technical values remain blocking diagnostics; they are never guessed.

## Boundaries

The recognizer is intentionally deterministic. It is now extensible through imported stroke templates and remains a foundation for:

- nested scopes and reusable subcircuits;
- graph dependency scheduling;
- recorded stroke replay;
- collaborative composition review;
- direct builder preview/apply through a local bridge;
- model-assisted suggestions that remain subordinate to deterministic compilation.
