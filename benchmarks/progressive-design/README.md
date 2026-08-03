# Progressive Design Benchmark

Status: scoped, ready for fresh-session runs

This benchmark evaluates whether the Progressive Design System transfers across unrelated interface tasks without converging on a new house style.

The benchmark is deliberately evidence-producing. A run is not complete because four implementations exist; it is complete when the frozen brief, condition isolation, rendered artifacts, functional checks, blind evaluation, and decision record are all present.

## Hypothesis

Structural intelligence should be developed internally and translated through a mandatory visitor-facing reconciliation pass.

The expected pattern is not that every later condition is automatically prettier. The expected pattern is:

- Condition B changes structural judgment relative to ordinary polish.
- Condition C increases spatial control but may expose or overuse that control.
- Condition D preserves useful structure while presenting a more coherent, specific, and visitor-centered surface.

## Four Conditions

### A — Control

Use an ordinary high-quality design instruction.

Ask for a polished, responsive, credible implementation without providing the Progressive Design System.

### B — Progressive Design

Apply:

- integrity;
- composition;
- system;
- identity;
- interaction;
- authorship;
- critique and elevation.

Begin at the first unresolved level rather than automatically performing baseline polish.

### C — Progressive Design + Spatial Intelligence

Apply Condition B and the Spatial Intelligence layer.

Private construction geometry is permitted. Public geometry must improve orientation, comparison, sequence, causality, scale, or spatial understanding.

### D — Reconciled Visitor Surface

Apply Conditions B and C internally, followed by Visitor-Facing Reconciliation.

Preserve the strongest structural decisions while removing or transforming:

- visible construction aids;
- diagnostic language;
- design rationale;
- implementation terminology;
- unexplained numbering;
- technical status treatments;
- authoring geometry;
- generalized system diagrams;
- motion that advertises itself;
- visual devices whose main purpose is to signal sophistication.

The visitor must encounter meaning before mechanism.

## Isolation Contract

Each condition must:

- begin from the same frozen content and functional requirements;
- use a separate source directory;
- share no CSS, components, scripts, generated design assets, or layout templates;
- receive no information about the appearance of other conditions;
- preserve the same required content, routes, actions, and states;
- receive the same implementation budget;
- be independently runnable.

Later conditions must not be source-code revisions of earlier conditions.

Shared material is limited to immutable fixtures under `fixtures/`:

- frozen brief;
- approved copy/data;
- approved source imagery;
- required route/state contract;
- evaluation rubric.

## Repository Layout

Each experiment lives under:

```text
benchmarks/progressive-design/runs/<experiment-id>/
  experiment.json
  FROZEN_BRIEF.md
  fixtures/
    content/
    images/
    route-contract.json
  conditions/
    A-control/
      source/
      evidence/
    B-progressive/
      source/
      evidence/
    C-spatial/
      source/
      evidence/
    D-reconciled/
      source/
      evidence/
  comparisons/
  evaluation/
    blind-order.json
    scores.json
    observations.md
    decision.md
  receipts/
    validation.json
    hashes.json
```

Generated run folders may be retained outside Git when large. The manifest, frozen brief, hashes, evaluation, decision, and a representative comparison set must be committed.

## Task Selection

Use one unrelated task per fresh session.

Required task qualities:

- at least three distinct page or state types;
- one meaningful user decision;
- one mobile-sensitive interaction;
- enough content or imagery to support composition;
- no required visual style;
- no dependency on a previously tested subject.

Test families:

1. `content-led` — archive, report, publication, collection, documentary, or knowledge experience.
2. `transactional` — enrollment, booking, intake, support, account, preparation, or eligibility flow.
3. `expressive` — festival, release, performance, installation, cultural program, or launch.

Avoid another student showcase or municipal permit product during the first three fresh-session tests.

## Fresh-Session Anti-Contamination Rule

A new session may receive:

- the frozen brief;
- this protocol;
- the canonical doctrine;
- the condition assignment;
- the artifact contract.

It must not receive:

- screenshots from previous experiments;
- descriptions of previous winning aesthetics;
- source code from earlier conditions;
- implementation-specific corrections learned from a prior condition;
- the blind evaluator's condition mapping.

The session may know the hypothesis but not the appearance of prior outputs.

## Required Evidence Per Condition

Each condition must produce:

- complete runnable source;
- desktop primary-page render;
- desktop secondary-page render;
- mobile primary-page render;
- mobile interaction-state render;
- route and link validation;
- JavaScript or application-state validation;
- responsive overflow check;
- keyboard/focus check;
- contrast and legibility review;
- reduced-motion review;
- notes on intentionally preserved content and functionality.

Do not claim browser validation when only static or Node-level validation ran. Record the actual validation boundary.

## Blind Evaluation

Randomize condition labels before evaluation. Evaluators should see artifacts, not prompts or source condition names.

Score 1–10:

- immediate clarity;
- hierarchy;
- composition;
- surface coherence;
- subject-specific identity;
- visitor rhythm;
- typography;
- imagery;
- interaction;
- mobile behavior;
- perceived authorship;
- absence of visible scaffolding;
- absence of generic model vocabulary;
- accessibility and legibility;
- overall preference.

Record overall preference separately. Do not derive it automatically from category averages.

## Diagnostic Questions

For each implementation:

1. What does the visitor understand in five seconds?
2. What is the strongest design decision?
3. What exists mainly to demonstrate sophistication?
4. What appears to be an authoring aid left on the surface?
5. Could this treatment move unchanged to an unrelated product?
6. Does removing grids, glow, gradients, badges, and animation collapse the composition?
7. Does mobile preserve intent or merely stack the desktop?
8. Is internal reasoning, system vocabulary, or implementation logic visible?
9. Does the visitor encounter the subject before the design system?
10. Which implementation would an exceptional human design team be most likely to release?

## Theory-Support Criteria

The hypothesis receives support when Condition D:

- wins overall preference;
- preserves or improves the structural clarity of B and C;
- contains fewer visible construction artifacts;
- does not lose usability, accessibility, or responsive integrity;
- does not simply become visually minimal;
- develops an identity appropriate to the task;
- avoids reproducing the same aesthetic used in earlier D runs.

## Failure Conditions

Treat the theory as challenged when:

- D removes useful structure and becomes bland;
- C consistently communicates better to visitors;
- D wins only through safer styling;
- D outputs converge on one editorial aesthetic;
- reconciliation reduces expressive range;
- preference depends heavily on knowing which condition is advanced;
- later conditions accumulate complexity without improving comprehension.

Document failures before attempting repairs.

## Test Sequence and Stopping Rule

Run three fresh task families:

1. content-led;
2. transactional;
3. expressive.

After these three sessions, stop and synthesize.

The system is provisionally validated when D is decisively preferred in at least two of three sessions and remains competitive in the third, while showing materially different surface identities across all three.

If D loses two sessions, revise the reconciliation layer before running more tests.

Do not continue testing merely to obtain a preferred result.

## Completion Receipt

Every run ends with `evaluation/decision.md` containing:

- task family and experiment ID;
- winner and blind ranking;
- which layer changed structure;
- which layer changed surface quality;
- where spatial intelligence helped;
- where it leaked;
- whether reconciliation preserved expressive range;
- recurring model defaults observed;
- new anti-convergence rules;
- instructions that should be removed or weakened;
- smallest stable default stack supported by the evidence;
- validation limitations.

See `experiment.schema.json` for the machine-readable run contract and `FRESH_SESSION_PROMPT.md` for the handoff prompt.