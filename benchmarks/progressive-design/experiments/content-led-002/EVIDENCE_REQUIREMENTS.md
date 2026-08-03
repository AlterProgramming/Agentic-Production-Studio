# Evidence Requirements

Place evidence inside the assigned condition’s `evidence/` directory.

## Required files

1. `README.md` — evidence index, run commands, environment, and limitations.
2. `desktop-primary.png` — overview route at 1440 × 1000.
3. `desktop-secondary.png` — mission route or another required secondary route at 1440 × 1000.
4. `mobile-primary.png` — overview route at 390 × 844.
5. `mobile-interaction.png` — selected learning path or opened detail state at 390 × 844.
6. `route-validation.json` — all required routes, direct-load behavior, status, titles, and top-level headings.
7. `link-validation.json` — internal and external link results, with offline limitations distinguished.
8. `application-state-validation.json` — the required selection, clearing, and detail states.
9. `responsive-overflow.json` — results for 1440 × 1000, 1024 × 768, 390 × 844, and 320 × 700.
10. `keyboard-focus.md` — keyboard path, focus visibility, focus return, and any limitation.
11. `contrast-legibility.md` — method, reviewed surfaces, results, and limitations.
12. `reduced-motion.md` — behavior with reduced motion requested.
13. `content-fidelity.md` — confirmation that required content, dates, roles, vehicles, artifacts, and sources match the frozen fixtures.
14. `isolation-receipt.json` — frozen ancestor, branch, initial source entries, read paths, changed paths, implementation sharing, prior-output exposure, and actual validation limits.
15. `hashes.json` — SHA-256 values for the implementation source and evidence files.

## Screenshot requirements

- Capture the complete viewport, not a cropped component.
- Use the built application, not a design mockup.
- Do not add benchmark labels, evaluator notes, debug guides, or condition identifiers to the public surface.
- If browser capture is impossible, record the blocker. Do not substitute a fabricated screenshot.

## Validation language

Use one of these boundaries for each check:

- `browser-engine`;
- `static`;
- `manual inspection`;
- `not run`.

A passing build or static lint does not establish route behavior, keyboard behavior, responsive behavior, or screenshot fidelity.

## Completion gate

The condition is not complete until the source is runnable, the required evidence exists, the isolation receipt is truthful, all changed paths are inside the assigned condition root, and the implementation commit has been pushed.
