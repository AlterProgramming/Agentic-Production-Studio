# Progressive Design Benchmark

Status: scoped for manual multi-session execution

This benchmark evaluates whether the Progressive Design System transfers across unrelated interface tasks without converging on a new house style.

The benchmark is evidence-producing. Four implementations are not sufficient by themselves. A valid run requires frozen inputs, separate condition sessions, equivalent rendered evidence, blind evaluation, and a mapped decision record.

## Execution Reality

One ChatGPT session can reliably own only one benchmark role. It cannot spawn independent external sessions, implement several conditions in one reasoning context without contamination, or remain blind after seeing condition identities.

The user therefore launches a manual chain of fresh sessions.

Required roles:

1. setup and freeze;
2. Condition A;
3. Condition B;
4. Condition C;
5. Condition D;
6. integration and blind packaging;
7. blind evaluation;
8. mapping and synthesis.

See `MANUAL_SESSION_ORCHESTRATION.md` for the binding execution contract.

A coordinator session must never implement more than one condition or claim that it launched independent agents. A run produced by one shared reasoning context is labeled `calibration_only`, not a causal benchmark.

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

### C — Progressive Design + Spatial Intelligence

Apply Condition B and the Spatial Intelligence layer.

Private construction geometry is permitted. Public geometry must improve orientation, comparison, sequence, causality, scale, or spatial understanding.

### D — Reconciled Visitor Surface

Apply Conditions B and C internally, followed by Visitor-Facing Reconciliation.

Preserve useful structural decisions while removing or translating visible construction aids, diagnostic language, design rationale, implementation terminology, unexplained numbering, technical status treatments, authoring geometry, generalized system diagrams, and motion that advertises itself.

The visitor must encounter meaning before mechanism.

## Blank-State Isolation Contract

Every condition must:

- begin in a separate fresh session;
- begin from the identical frozen setup commit;
- begin with an empty assigned source directory;
- receive the same frozen content, assets, route contract, evidence contract, and implementation budget;
- receive only its assigned condition instructions;
- use a separate branch and source directory;
- share no CSS, components, scripts, generated design assets, tokens, or templates;
- receive no information about another condition's appearance;
- be independently runnable.

Condition D is not a revision of C. Later conditions must not inspect or inherit earlier source or screenshots.

The user is the session scheduler. Each completed session provides a copyable prompt for the next role and then stops.

## Branch Contract

The setup session freezes one base commit.

Recommended branches:

```text
agent/<experiment-id>-A-control
agent/<experiment-id>-B-progressive
agent/<experiment-id>-C-spatial
agent/<experiment-id>-D-reconciled
agent/<experiment-id>-integration
```

Each condition branch may modify only its own condition directory and evidence directory.

The integration session verifies that:

- all four branches descend from the same frozen commit;
- changed paths remain inside the assigned write boundary;
- shared fixtures were not changed;
- condition evidence is equivalent enough for blind evaluation.

## Shared Inputs

Shared material is limited to immutable fixtures:

- frozen brief;
- approved copy and data;
- approved source imagery;
- required route and state contract;
- evidence contract.

No shared starter implementation or visual system is allowed.

## Repository Layout

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
    condition-map.sealed.json
    scores.json
    observations.md
    decision.md
  receipts/
    validation.json
    hashes.json
```

Large generated payloads may remain outside Git. The durable record must retain the frozen inputs, hashes, condition receipts, representative evidence, blind evaluation, mapping, decision, and validation limitations.

## Task Selection

Use one unrelated product problem per benchmark run.

Required qualities:

- at least three distinct pages or states;
- one meaningful visitor decision;
- one mobile-sensitive interaction;
- enough real content or imagery to support composition;
- no prescribed visual style;
- no dependency on a prior tested product.

Task families:

1. `content-led` — archive, report, publication, collection, documentary, or knowledge experience;
2. `transactional` — enrollment, booking, intake, support, account, preparation, or eligibility flow;
3. `expressive` — festival, release, performance, installation, cultural program, or launch.

## Anti-Contamination Rule

A condition session may receive:

- the frozen brief;
- immutable fixtures;
- its own sealed prompt;
- the artifact contract;
- the frozen base commit and assigned branch.

It must not receive:

- screenshots from another condition or previous experiment;
- descriptions of a winning aesthetic;
- source from another condition;
- implementation-specific corrections learned from another condition;
- coordinator predictions;
- evaluator materials or candidate mapping.

## Required Evidence Per Condition

Each condition produces:

- complete runnable source;
- desktop primary-page render;
- desktop secondary-page render;
- mobile primary-page render;
- mobile interaction-state render;
- route and link validation;
- application-state validation;
- responsive overflow check;
- keyboard and focus check;
- contrast and legibility review;
- reduced-motion review;
- content-fidelity note;
- isolation receipt;
- actual validation limitations.

Do not claim browser validation when only static or script-level checks ran.

## Integration and Blind Packaging

Integration is a separate non-evaluating session.

It assigns randomized candidate labels, creates evaluator-facing evidence packets, and seals the candidate-to-condition mapping. It must not rank or describe a preferred design.

## Blind Evaluation

Blind evaluation is another fresh session. The evaluator sees candidate artifacts, a neutral product brief, the rubric, and relevant validation limitations. It does not see prompts, doctrine, source branches, condition identities, prior commentary, or expected results.

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
- accessibility and legibility.

Record overall preference separately rather than deriving it from category averages.

## Diagnostic Questions

For every candidate, ask:

1. What does the visitor understand in five seconds?
2. What is the strongest design decision?
3. What exists mainly to demonstrate sophistication?
4. What appears to be an authoring aid left on the surface?
5. Could this treatment move unchanged to an unrelated product?
6. Does removing grids, glow, gradients, badges, and animation collapse the composition?
7. Does mobile preserve intent or merely stack desktop?
8. Is internal reasoning or implementation vocabulary visible?
9. Does the visitor encounter the subject before the design system?
10. Which candidate would an exceptional human design team be most likely to release?

## Validity and Result Labels

- `setup_complete`: frozen inputs and condition packets exist;
- `condition_complete`: one condition and its evidence exist;
- `integration_complete`: candidate packets and sealed mapping exist;
- `evaluation_complete`: blind scores and observations exist;
- `benchmark_complete`: identities are mapped and synthesis is committed;
- `calibration_only`: two or more conditions shared a reasoning context, or evaluation was not blind;
- `causal_isolation_valid`: A–D ran in separate fresh sessions from the same frozen commit.

Do not claim a completed causal benchmark unless both `causal_isolation_valid` and `evaluation_complete` are true.

## Theory-Support Criteria

The hypothesis receives support when Condition D:

- wins overall blind preference;
- preserves or improves structural clarity;
- contains fewer visible construction artifacts;
- retains usability, accessibility, and responsive integrity;
- does not win merely by becoming minimal or safe;
- develops an identity appropriate to the task;
- avoids reproducing the same house style as prior D runs.

## Failure Conditions

Treat the theory as challenged when:

- D removes useful structure and becomes bland;
- C communicates better to visitors;
- D wins only through safer styling;
- D outputs converge on one editorial mannerism;
- reconciliation reduces expressive range;
- later conditions accumulate complexity without improving comprehension.

Document failure before repair.

## Test Sequence and Stopping Rule

Complete three causally isolated benchmark runs:

1. content-led;
2. transactional;
3. expressive.

After the third, stop and synthesize.

The system is provisionally validated when D is decisively preferred in at least two of three runs and remains competitive in the third, while exhibiting materially different surface identities.

A calibration run does not count toward this stopping rule.

## Completion Record

Every completed run ends with `evaluation/decision.md` recording:

- task family and experiment ID;
- blind ranking and mapped conditions;
- whether causal isolation was valid;
- which layer changed structure;
- which layer changed surface quality;
- where spatial intelligence helped or leaked;
- whether reconciliation preserved expressive range;
- recurring model defaults;
- new anti-convergence rules;
- instructions that should be removed or weakened;
- smallest stable default stack supported by evidence;
- validation limitations.

See:

- `MANUAL_SESSION_ORCHESTRATION.md` for the role-by-role relay;
- `FRESH_SESSION_PROMPT.md` for a single-condition session;
- `experiment.schema.json` for the machine-readable run contract.
