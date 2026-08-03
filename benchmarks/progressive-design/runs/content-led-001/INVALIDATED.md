# INVALIDATED — DO NOT USE AS BENCHMARK EVIDENCE

This entire `content-led-001` run is invalidated.

It must not be used to:

- support or reject the Progressive Design hypothesis;
- rank Conditions A, B, C, or D;
- count toward the three-run validation sequence;
- seed, guide, or visually influence a replacement run;
- provide source, screenshots, implementation patterns, corrections, or design references to future condition sessions;
- continue an experiment from the current A–D implementations.

## Reason

All four conditions were implemented sequentially inside one shared reasoning context. This created material cross-condition leakage and made it impossible to believe that the implementations were independently generated under their assigned instructions. No independent blind evaluator was used.

The resulting artifacts are contaminated. Treating them as a valid comparison would overstate the evidence and undermine the purpose of the benchmark.

## Required replacement

A replacement benchmark must begin from a newly frozen setup state and use the manual multi-session relay defined in PR #21:

1. one setup session;
2. one fresh session for Condition A;
3. one fresh session for Condition B;
4. one fresh session for Condition C;
5. one fresh session for Condition D;
6. one integration and anonymization session;
7. one blind evaluator session;
8. one synthesis session after the condition mapping is revealed.

Each condition session must receive only its sealed packet and must not inspect this run.

## Repository status

- Experiment ID: `content-led-001`
- Branch: `agent/progressive-design-content-led-001`
- Pull request: `#22`
- Disposition: invalidated and excluded
- Replacement starting point: the current Progressive Design doctrine branch or its merged successor, not this benchmark branch

The files remain only as an audit trail showing why the execution model was changed. Their presence does not make them admissible evidence.
