# INVALIDATED — DO NOT USE AS ONE-SHOT BENCHMARK EVIDENCE

This entire `content-led-001` run is invalidated for the independent one-shot Progressive Design benchmark.

It must not be used to:

- support or reject the one-shot Progressive Design hypothesis;
- rank Conditions A, B, C, or D as independently generated alternatives;
- count toward the three-run validation sequence;
- seed, guide, or visually influence a replacement one-shot run;
- provide source, screenshots, implementation patterns, corrections, or design references to future isolated condition sessions;
- continue an independent-condition experiment from the current A–D implementations.

## Reason

All four conditions were implemented sequentially inside one shared reasoning context while the experiment was framed as four separate conditions. This created material cross-condition leakage and made it impossible to believe that the implementations were independently generated under their assigned instructions. No independent blind evaluator was used.

The resulting artifacts are contaminated for the stated experiment. Treating them as a valid independent comparison would overstate the evidence and undermine the purpose of the benchmark.

## What this does not invalidate

Sequential design evolution is a legitimate separate research question.

A design may intentionally progress through staged passes such as:

1. product intent and content interpretation;
2. composition and hierarchy;
3. system formation;
4. spatial control;
5. visitor-facing reconciliation;
6. critique and refinement.

That benchmark must explicitly declare that each stage inherits the previous artifact and reasoning state. It should evaluate whether the order of passes improves the same design over time, which decisions persist, where regressions occur, and whether later stages merely force novelty because another turn has begun.

This run cannot be retroactively relabeled as that benchmark because its prompts, isolation claims, comparison framing, and evidence contract were designed around independent alternatives rather than declared inheritance.

## Required replacement for the one-shot benchmark

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
- Disposition: invalidated and excluded from the one-shot benchmark
- Possible future use: audit input when designing a separately declared sequential-evolution protocol; not evidence within that future benchmark
- Replacement starting point: the current Progressive Design doctrine branch or its merged successor, not this benchmark branch

The files remain only as an audit trail showing why the execution model was changed. Their presence does not make them admissible evidence.
