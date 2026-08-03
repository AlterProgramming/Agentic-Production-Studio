# Single-Condition Fresh-Session Prompt

Use this prompt only for one condition implementation session.

This session owns exactly one condition. It does not coordinate, launch, summon, simulate, implement, inspect, integrate, or evaluate any other condition.

The user manually launches the other benchmark sessions. See `MANUAL_SESSION_ORCHESTRATION.md` for the complete relay.

---

You are implementing one isolated Progressive Design benchmark condition from a blank state.

## Assigned Role

You will receive one assigned condition: A, B, C, or D.

Complete only that condition. Do not create work for another condition in this session. Do not claim that you launched or delegated to independent agents or sessions.

## Inputs

You will receive:

1. One frozen product brief and immutable content fixtures.
2. One sealed condition prompt.
3. A route, state, evidence, and implementation-budget contract.
4. The exact frozen base commit.
5. One assigned branch, source directory, and evidence directory.

You will not receive an existing site, starter design, component library, visual reference implementation, prior condition source, or another condition's renders.

The sealed condition prompt is the only design instruction for this session. Condition A must not read the Progressive Design doctrine. Conditions B–D may read only the doctrine layers explicitly assigned by their packet.

## Objective

Create the strongest complete product experience supported by the frozen material under the assigned condition.

The frozen brief—not a prior interface—is the foundation. Preserve all required facts, copy, data, functionality, routes, states, constraints, and approved assets. Do not invent sections, filler, fake data, decorative complexity, or explanatory design rationale.

Originate the information architecture, composition, interaction model, responsive behavior, and visual expression from the blank state.

## Blank-State Contract

Begin from the exact frozen base commit on the assigned branch.

Confirm that the assigned source directory is empty before writing implementation code.

Do not:

- reconstruct or imitate a prior implementation;
- inspect another condition branch or directory;
- assume an existing hierarchy, grid, page composition, component system, or visual identity;
- treat another condition as a draft to improve;
- inherit CSS, components, scripts, generated assets, layout templates, tokens, or starter code;
- change the frozen brief or shared fixtures;
- preserve arbitrary visual decisions that are not present in the frozen inputs.

What remains constant across conditions is the product problem and evidence contract—not the design solution.

## Write Boundary

Write only inside the assigned condition directory:

```text
benchmarks/progressive-design/runs/<experiment-id>/conditions/<assigned-condition>/
```

Implementation belongs in `source/`. Evidence and receipts belong in `evidence/` or the assigned condition root when required by the manifest.

Do not modify:

- `FROZEN_BRIEF.md`;
- shared fixtures;
- the doctrine;
- another condition directory;
- comparisons;
- evaluation files;
- candidate mappings;
- coordinator receipts outside the assigned boundary.

Before committing, inspect the changed paths and reject any write outside the assigned boundary.

## Isolation Receipt

Record:

- frozen base commit;
- assigned branch;
- assigned condition;
- whether the source directory was empty at initialization;
- initial source-directory entries;
- whether any implementation code was shared;
- whether any prior condition output was seen;
- whether another condition directory was inspected;
- actual implementation budget used;
- unavoidable environmental differences;
- changed-path list;
- real validation limitations.

## Condition Behavior

Use only the assigned sealed packet. The summary below identifies the intended boundary but does not replace that packet.

### Condition A — Control

Use ordinary strong product-design judgment. Produce a polished, responsive, credible implementation. Do not read or use the Progressive Design doctrine.

### Condition B — Progressive

Apply only Progressive Design: integrity, composition, system, identity, interaction, authorship, and critique/elevation.

### Condition C — Spatial

Apply Progressive Design plus Spatial Intelligence and the private construction layer. Do not use Visitor-Facing Reconciliation.

### Condition D — Reconciled

Apply the complete assigned stack from a blank state. Condition D is not a revision of C and must not inspect C.

## Required Process

1. Verify the frozen base commit and assigned branch.
2. Read and hash the frozen brief.
3. Confirm the assigned source directory begins empty.
4. Confirm the write boundary.
5. Extract the required facts, actions, routes, states, constraints, and assets.
6. Originate and implement only the assigned condition.
7. Render the required desktop and mobile evidence.
8. Validate routes, links, state, overflow, keyboard focus, contrast, legibility, and reduced motion.
9. State the actual validation boundary. Do not imply browser-engine coverage when only static or script-level checks ran.
10. Produce the evidence index and isolation receipt.
11. Inspect changed paths and commit only the assigned condition files.
12. Stop at the handoff boundary.

## Required Evidence

Produce:

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
- frozen-content fidelity note;
- blank-state and isolation receipt;
- actual validation limitations.

## Public-Surface Restrictions

Do not expose benchmark language, condition names, internal reasoning, agent instructions, verification notes, hierarchy labels, design-system terminology, alignment guides, breakpoint indicators, debug controls, publishing notes, implementation status, or evaluator information in the production interface.

A private debug layer may exist only when the assigned condition permits it. It must default off and must not be required for the public composition to feel complete.

## Completion

This session is complete only when one assigned implementation, its evidence, validations, limitations, fidelity note, isolation receipt, and commit exist.

Do not compare conditions. Do not prepare blind evaluation. Do not declare a winner.

End by providing:

- assigned condition;
- branch;
- commit SHA;
- frozen brief hash;
- changed paths;
- validation coverage and limitations;
- confirmation that no other condition was inspected or implemented;
- a copyable instruction telling the user which role to launch next, without attempting to launch it yourself.

---

## Session Launch Fields

```text
Experiment ID:
Task family: content-led | transactional | expressive
Assigned condition: A | B | C | D
Frozen base commit:
Assigned branch:
Frozen brief path:
Frozen brief SHA-256:
Condition source path:
Condition evidence path:
Source directory confirmed empty: yes | no
Implementation budget:
Required routes/states:
Required evidence:
Known environment limitations:
```
