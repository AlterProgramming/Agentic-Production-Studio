# Progressive Design Benchmark — Manual Session Relay

## Environment Constraint

A ChatGPT session can execute only one benchmark role reliably. It cannot spawn independent external sessions, preserve causal isolation while implementing several conditions sequentially, or perform a blind evaluation after seeing condition identities.

The benchmark therefore uses a manual relay. The user launches each fresh session and gives it only the packet required for that role.

A run is not one session. A run is a chain of sealed sessions.

## Required Session Chain

### Session 0 — Setup and Freeze

Purpose: define and freeze the product problem.

This session may:

- select the bounded task;
- collect lawful source material;
- create `FROZEN_BRIEF.md` and immutable fixtures;
- initialize the experiment workspace;
- verify that all four condition source directories are empty;
- create four sealed condition packets;
- commit the setup record.

This session must not:

- implement any condition;
- inspect or predict a condition's future design;
- create a shared starter implementation;
- evaluate likely winners.

Output:

- a frozen benchmark branch or commit SHA;
- four launch prompts;
- the exact branch name for each condition session.

### Session 1 — Condition A

Purpose: implement the ordinary high-quality control.

Input is limited to:

- the frozen benchmark commit;
- Condition A packet;
- immutable fixtures;
- its assigned branch and directory.

This session must not read the doctrine or any other condition directory.

Recommended branch:

`agent/<experiment-id>-A-control`

### Session 2 — Condition B

Purpose: implement Progressive Design.

Input is limited to:

- the same frozen benchmark commit;
- Condition B packet;
- immutable fixtures;
- its assigned branch and directory.

This session must not inspect Conditions A, C, or D.

Recommended branch:

`agent/<experiment-id>-B-progressive`

### Session 3 — Condition C

Purpose: implement Progressive Design plus Spatial Intelligence.

Input is limited to its sealed packet and the same frozen inputs.

Recommended branch:

`agent/<experiment-id>-C-spatial`

### Session 4 — Condition D

Purpose: implement the complete reconciled stack from a blank state.

Condition D is not a revision of C. It receives no C source or renders.

Recommended branch:

`agent/<experiment-id>-D-reconciled`

### Session 5 — Integration and Blind Packaging

Purpose: combine completed condition artifacts without judging them.

This session may:

- verify each condition branch descended from the same frozen commit;
- verify write-boundary isolation;
- integrate the four condition directories;
- collect equivalent evidence;
- assign randomized candidate labels;
- create evaluator-facing comparison packets;
- seal the candidate-to-condition mapping.

This session must not score, rank, or describe a preferred design.

Recommended integration branch:

`agent/<experiment-id>-integration`

### Session 6 — Blind Evaluation

Purpose: evaluate candidate artifacts without condition knowledge.

This fresh session receives only:

- randomized candidate artifacts;
- the frozen product brief or a neutral task summary;
- the evaluation rubric;
- validation limitations that affect interpretation.

It must not receive:

- condition prompts;
- source branches or directories;
- candidate mapping;
- doctrine descriptions;
- prior commentary;
- expected hypotheses.

It returns scores, observations, and overall preference using candidate labels only.

### Session 7 — Mapping and Synthesis

Purpose: combine the sealed mapping with the blind evaluation.

This session may:

- reveal candidate identities after evaluation is complete;
- record the ranking by condition;
- analyze which layer changed structure and surface quality;
- update the experiment decision record;
- compare the result with prior experiments;
- determine the next test under the stopping rule.

It must not alter condition implementations after seeing the evaluation.

## Branch Contract

All four condition branches must start from the identical frozen setup commit.

Each condition branch may write only inside:

`benchmarks/progressive-design/runs/<experiment-id>/conditions/<assigned-condition>/`

Evidence may also be written within that condition's evidence directory.

No condition branch may modify:

- `FROZEN_BRIEF.md`;
- shared fixtures;
- another condition directory;
- the doctrine;
- evaluation files;
- sealed mappings.

The integration session must verify changed paths before accepting each condition branch.

## Manual Launch Contract

The user is the scheduler. After one session finishes, it must provide a single copyable launch prompt for the next required session.

A session must never claim that it launched, summoned, delegated to, or ran another independent session.

When its role is complete, it stops at the handoff boundary.

## Validity Labels

Use these labels consistently:

- `setup_complete`: frozen inputs and sealed packets exist;
- `condition_complete`: one assigned implementation and its evidence exist;
- `integration_complete`: all conditions are combined and blinded;
- `evaluation_complete`: blind candidate scores exist;
- `benchmark_complete`: mapping and synthesis are recorded;
- `calibration_only`: conditions shared a reasoning context or evaluation was not blind;
- `causal_isolation_valid`: all four conditions ran in separate fresh sessions from the same frozen commit.

Do not call a run a completed causal benchmark before the final two conditions are true:

- `causal_isolation_valid: true`;
- `evaluation_complete: true`.

## Recovery

If one condition fails, rerun only that condition from the original frozen commit in a fresh session. Do not expose it to successful sibling outputs.

If shared fixtures change, invalidate all completed conditions and create a new experiment version. Do not silently update the brief beneath existing implementations.
