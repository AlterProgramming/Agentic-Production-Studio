# Builder Readiness Scorecard

This scorecard does not claim to reproduce an external evaluator's exact 28/100 result. It records the internal capabilities that were previously absent and the evidence required before promoting them.

| Dimension | Weight | Current evidence |
|---|---:|---|
| Workspace and path safety | 15 | Confinement and allowlist tests |
| Exact mutation controls | 15 | Guarded text, JSON, copy, and delete operations |
| Preview and change visibility | 15 | Dry-run write set and unified diffs |
| Transaction and rollback | 15 | Full-plan simulation plus restoration on write failure |
| Verification and provenance | 15 | Plan hashes, before/after hashes, receipts, drift check |
| Extensibility | 10 | Operation registry for domain-specific builders |
| Domain asset builders | 10 | Anchor-aware deterministic image normalization |
| Incremental orchestration and cache | 5 | Planned |

## Promotion rule

The surgical builder may be called **production foundation** after:

1. CI passes all builder regression tests.
2. One real Storm contract update is previewed and applied through a guarded plan.
3. The receipt is committed as benchmark evidence.
4. The `image_normalize` operator is exercised on a real Storm source and its receipt is retained.
5. A forced stale-plan test proves that changed source state blocks mutation.
