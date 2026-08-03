# Single-Condition Fresh-Session Contract

Use this contract for one implementation role only. The operative role is defined exclusively by the sealed packet named in the launch message.

## Launch Inputs

A valid launch message contains only:

- the repository;
- one full 40-character frozen setup commit SHA;
- one assigned branch;
- one sealed packet path.

It must not summarize unassigned instruction stacks, enumerate sibling packets, or reproduce material that the assigned session is forbidden to inspect.

## Contamination Test

Stop only when this conversation contains operative material outside the assigned packet, such as:

- the contents of another sealed packet;
- source, renders, evidence, evaluation, ranking, or conclusions from an unassigned implementation;
- instructions assigning this session more than one implementation role;
- implementation-specific corrections learned from an unassigned output.

The following do **not** constitute contamination:

- a generic statement that unassigned material is forbidden;
- an allowlist or write boundary;
- the existence of other directories in the repository;
- names appearing only in validation metadata or exclusion rules.

Do not infer contamination merely because the benchmark has multiple sealed roles. Judge only material actually supplied to the current conversation.

## Required Preflight

Before design work:

1. Resolve the supplied frozen setup commit SHA.
2. Create the assigned branch directly from that commit.
3. Read the assigned Markdown packet and its adjacent machine contract.
4. Run:

   ```bash
   python3 tools/validate_progressive_design_packet.py \
     --root . \
     --contract <assigned-packet-json>
   ```

5. Read only paths listed by the validated contract.
6. Confirm that the assigned source directory contains only a zero-byte `.gitkeep`.
7. Confirm that the changed-path boundary is the assigned condition directory.

If any preflight check fails, report that concrete failure. Do not substitute a speculative contamination claim.

## Implementation

Use only the assigned packet and its allowed shared inputs. Originate one complete implementation from the blank source state. Do not modify frozen inputs or inspect unassigned outputs.

Produce all evidence required by the assigned evidence contract. State the real validation boundary; do not claim browser coverage from static checks.

## Completion

Commit and push only assigned-condition paths. Open or update the assigned pull request.

Report:

- assigned role;
- branch;
- implementation commit SHA;
- frozen setup commit SHA;
- frozen brief hash;
- changed paths;
- tests and evidence paths;
- validation limitations;
- any genuine blocker.

Do not compare implementations, predict outcomes, prepare blind evaluation, or provide another implementation role's prompt.
