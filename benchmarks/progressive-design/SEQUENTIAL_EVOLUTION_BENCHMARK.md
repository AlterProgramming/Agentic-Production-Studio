# Sequential Design Evolution Benchmark

Status: separate research track; not part of the independent one-shot validation sequence

## Purpose

This benchmark studies whether a single design improves when the Progressive Design System is applied as an explicit sequence of inherited passes.

It does not compare independently generated alternatives. Every stage receives the complete artifact, evidence, and reasoning record from the prior stage.

The central question is:

> Does deliberately ordered design evolution improve one artifact, or do later turns merely introduce novelty because another pass has been requested?

## Separation from the one-shot benchmark

The two benchmark families answer different questions.

### Independent one-shot benchmark

Each condition begins from the same frozen brief and an empty source directory. Conditions cannot inspect one another. The test asks whether different instruction stacks change first-pass design behavior.

### Sequential evolution benchmark

One artifact is intentionally inherited and revised across declared stages. The test asks whether staged application produces cumulative improvement, useful persistence, or regression.

A run cannot serve both purposes. Sequential inheritance must never be described as condition independence.

## Proposed stages

Use one frozen brief and one initial implementation budget.

### Stage 0 — Baseline intent

Translate the product problem into a complete, functional first implementation. Record the chosen product intent, audience priority, information architecture, and primary visitor journey.

### Stage 1 — Composition

Revise hierarchy, scale, proportion, density, negative space, sequence, and responsive pacing. Do not introduce a new visual identity merely to prove that the stage occurred.

### Stage 2 — System and identity

Resolve typography, spacing, color, imagery, components, responsive rules, and subject-specific character. Preserve strong compositional decisions from Stage 1 unless evidence supports replacement.

### Stage 3 — Spatial intelligence

Introduce private spatial analysis and revise relationships, alignment, rhythm, orientation, and responsive transformations. Public geometry must earn its presence.

### Stage 4 — Visitor-facing reconciliation

Remove or translate construction aids, diagnostic vocabulary, exposed reasoning, and sophistication signals. Preserve useful structure while improving the public surface.

### Stage 5 — Critique and restraint

Compare the current artifact with all prior snapshots. Repair regressions, remove change-for-change's-sake, and retain only decisions that strengthen the visitor experience.

## Stage contract

Every stage must:

- begin from the exact committed output of the previous stage;
- state what it is allowed to change;
- state what it should preserve;
- receive a bounded and equal revision budget where comparable;
- produce desktop and mobile evidence before and after the pass;
- record added, removed, retained, and reverted design decisions;
- explain regressions without exposing that explanation in the public interface;
- avoid changing the frozen product problem or inventing new content;
- stop when its assigned design problem is resolved rather than forcing visible novelty.

## Required measurements

For every transition, record:

- visitor clarity;
- hierarchy;
- composition;
- surface coherence;
- subject identity;
- interaction and mobile behavior;
- visible scaffolding;
- generic model vocabulary;
- accessibility and legibility;
- overall preference;
- number of prior decisions preserved;
- number of prior decisions reverted;
- number of new visible devices introduced;
- whether the stage would still be judged useful if its changes were visually subtle.

## Critical diagnostics

Ask after every stage:

1. Did the pass solve its assigned problem?
2. Did it preserve strong earlier decisions?
3. Did it create a regression elsewhere?
4. Did it add visible novelty primarily because a new turn began?
5. Could the same improvement have been achieved with fewer changes?
6. Is the artifact becoming more specific to the product or merely more styled?
7. Does the public surface reveal the sequence of internal design work?
8. Would an evaluator prefer the new stage without knowing it is later?

## Evaluation design

Retain a snapshot after every stage.

Use two evaluation modes:

1. **Adjacent blind comparison:** compare Stage N against Stage N-1 without revealing order.
2. **Full-sequence blind ranking:** randomize all stage snapshots and rank them together.

The final stage is not assumed to win. A prior snapshot may be the best result.

## Failure conditions

The staged method is challenged when:

- every pass forces a conspicuous new visual idea;
- later stages overwrite rather than refine strong earlier work;
- the design converges on the system's vocabulary instead of the subject;
- reconciliation merely makes the result safer or more minimal;
- evaluators prefer an earlier stage;
- improvements depend on evaluator knowledge of the stage order;
- repeated turns increase complexity without improving comprehension;
- no stage can preserve intent because the initial intent was not recorded clearly enough.

## Initial experiment recommendation

Do not reuse `content-led-001` as a valid sequential run. It was framed and prompted as independent conditions, so its inheritance and leakage were uncontrolled.

Use it only as an audit example when preparing a new, explicitly sequential experiment. The new experiment should begin from a new frozen brief and record Stage 0 intent before any progressive pass begins.
