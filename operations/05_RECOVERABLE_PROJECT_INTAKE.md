# Recoverable Project Intake

## Purpose

Intake is a project compiler, not a questionnaire. It turns partial project reality into the smallest defensible next action for a release program. Recovery is a normal intake mode, not an exception path.

## Governing rule

**Ignore what is not known unless the next justified action requires it. Act only on what the evidence supports.**

An intake record may contain unresolved history without blocking progress. Unknowns are explicitly marked `required_for_next_action: true|false`. Only required unknowns may stop the next transition.

## State model

`DISCOVERED -> TRIAGED -> SPECIFIED -> READY -> ACTIVE -> VERIFYING -> RELEASED`

Escape states: `BLOCKED`, `ARCHIVED`.

`RECOVERING` may be entered from any non-archived state, including `RELEASED`. Recovery never erases earlier states or failed claims.

## Recovery chronology

Recovery is append-only and evidence-led. Build a chronological texture from available artifacts rather than forcing a complete narrative:

1. order observations by when the underlying evidence was created or observed;
2. distinguish artifact presence, implementation state, test evidence, runtime evidence, deployment evidence, and human claims;
3. record contradictions instead of resolving them by assumption;
4. identify the **last defensible state**: the newest state directly supported by surviving evidence;
5. list failed or overstated claims separately;
6. mark unresolved holes;
7. choose the **smallest repair** that can move the project forward from the last defensible state;
8. require an unknown only when that repair cannot be performed safely or meaningfully without it.

The recovery process may conclude that a project is already releasable, needs one narrow repair, needs a fresh implementation, is blocked on an external dependency, or should be archived.

## Intake cost ladder

Pass 0 — inventory: identity, repository, target period, intended outcome.

Pass 1 — mechanical evidence: branches, commits, PRs, files, builds, deployments, manifests, tests.

Pass 2 — recovery/qualification: only for projects whose state cannot be established cheaply.

Pass 3 — work packet: emit bounded reads/writes, authority, next action, acceptance evidence, and release verification requirements.

Expensive reasoning is spent only after cheap evidence has narrowed the problem.

## Queue dispositions

- `ACTIONABLE`: next action is justified and required unknowns are absent.
- `RECOVER`: chronology/recovery is required before ordinary execution.
- `BLOCKED_ON_REQUIRED_UNKNOWN`: the next action genuinely depends on missing information.
- `VERIFY_RELEASE`: project claims release and should be tested from the recipient path.
- `TRIAGE`: state exists but is not yet execution-ready.
- `NO_ACTION`: archived.
- `INVALID`: intake contract itself is malformed.

## Execution boundary

Downstream workers receive the intake/work packet, not the entire project mythology. A packet contains the evidence-backed current state, explicit unknowns, bounded authority, next action, and completion evidence required. Workers must not silently expand authority or convert unsupported historical claims into current truth.
