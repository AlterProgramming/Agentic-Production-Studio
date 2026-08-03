# Progressive Design Benchmark — Manual Session Relay

## Environment Constraint

A valid independent one-shot run is a chain of sealed fresh sessions. The user launches each role manually. No session may implement more than one condition or claim that it launched another session.

## Session Chain

1. Setup and Freeze
2. One fresh implementation session per sealed condition
3. Integration and Blind Packaging
4. Blind Evaluation
5. Mapping and Synthesis

Every implementation branch descends from the same full 40-character frozen setup commit SHA.

## Setup and Freeze Gate

Setup is complete only after all of the following are true:

- the experiment files exist on a repository branch;
- the setup branch is ahead of its doctrine base;
- the frozen brief, fixtures, image binaries, provenance, contracts, packets, and receipts are committed;
- every packet has an adjacent machine-readable contract and minimal launch prompt;
- `tools/validate_progressive_design_packet.py` passes for every packet;
- every assigned source directory contains only a zero-byte `.gitkeep`;
- all frozen-input hashes verify;
- the final setup commit SHA is recorded in the setup PR and completion report;
- a setup PR is open or updated.

A branch that is identical to its doctrine base is not setup-complete.

Use the commit SHA itself as the immutable anchor. Do not invent or require a tag unless that tag has actually been created and independently verified.

## Sealed Packet Contract

Each implementation session receives only:

- one frozen setup commit SHA;
- one assigned branch;
- one assigned packet path;
- the content of its minimal launch prompt.

The packet contract contains the complete read allowlist and write boundary. Launch prompts must not enumerate unassigned conditions, summarize their doctrine, reproduce their packet paths, or list their branch names.

## Contamination Semantics

Actual contamination means the session received operative material outside its assignment:

- another packet's contents;
- another implementation's source, renders, evidence, comparison, ranking, or conclusion;
- instructions assigning multiple implementation roles;
- corrections derived from another implementation.

Exclusion-only references are not operative exposure. Generic phrases such as “do not inspect unassigned material,” machine allowlists, and repository directory names do not invalidate a session.

When a preflight fails, report the failed repository fact—missing packet, unresolved commit, nonempty source, invalid hash, or write-boundary mismatch. Do not call a repository setup failure “conversation contamination.”

## Implementation Session Boundary

An implementation session:

- reads its packet and only the allowed paths;
- confirms its source state is blank;
- creates exactly one implementation;
- writes only to its assigned condition directory;
- builds, tests, and produces equivalent evidence;
- commits, pushes, opens or updates its PR, reports, and stops.

It must not compare candidates, infer likely results, inspect unassigned branches, or prepare evaluation material.

## Integration Boundary

A separate integration session verifies:

- identical frozen ancestor;
- changed-path isolation;
- immutable shared inputs;
- evidence equivalence;
- randomized candidate labels;
- sealed candidate mapping.

It does not score or rank.

## Evaluation Boundary

A fresh blind evaluator receives randomized candidate artifacts, a neutral task summary, the rubric, and validation limitations. It does not receive condition identities, packets, branches, doctrine summaries, expected hypotheses, or prior commentary.

## Validity Labels

- `setup_complete`: all setup gates above passed;
- `condition_complete`: one isolated implementation and evidence committed;
- `integration_complete`: candidate packets and sealed mapping committed;
- `evaluation_complete`: blind scores and observations committed;
- `benchmark_complete`: mapping and synthesis committed;
- `calibration_only`: implementation roles shared operative reasoning context or evaluation was not blind;
- `causal_isolation_valid`: all implementation roles ran in separate fresh sessions from the same frozen commit.

## Recovery

If one implementation fails, rerun only that role from the original frozen commit in a new session.

If any shared fixture changes, create a new frozen setup commit and invalidate implementations based on the prior commit. Never silently mutate frozen inputs.
