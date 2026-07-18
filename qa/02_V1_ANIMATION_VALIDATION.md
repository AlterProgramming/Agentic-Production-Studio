# V1 Integrated Animation Validation

This gate turns the studio's animation acceptance language into a deterministic validation run. It applies to the first Storm benchmark and to later complete-frame animation packages.

## Validation stages

### `contract`

Use before frame production. It verifies that the brief is locked, the manifest agrees with it, timing and event frames are valid, provenance exists, and V1 remains bounded to four through eight frames.

### `frames`

Use after the integrated PNG sequence exists. It adds frame completeness, naming, dimensions, alpha mode, palette limits, transparent-border policy, file-size budgets, and optional drift or loop-seam heuristics.

### `delivery`

Use before packaging. It additionally requires the preview, contact sheet, Godot `SpriteFrames` resource, and integration guide declared by the manifest.

## Commands

```bash
python -m pip install -r requirements-dev.txt
python tools/validate_animation.py benchmarks/storm-v1 --stage contract
python tools/validate_animation.py path/to/completed-package --stage delivery --report path/to/completed-package/qa-report.json
pytest -q
```

A run exits nonzero when a blocking or major defect exists. Minor failures are reported without blocking unless `--fail-on-minor` is supplied.

## Automated versus human gates

The validator proves structural and technical facts. It does **not** claim that an animation is artistically convincing. Human review remains mandatory for:

- identity preservation;
- anticipation/action/impact/recovery readability;
- authored motion versus accidental silhouette mutation;
- whether VFX visibly interacts with the source;
- impact strength at gameplay speed;
- representative-background readability;
- acceptable transitions into and out of the animation.

## Drift policy

Whole-sprite drift cannot be inferred safely from alpha centroid alone because designed animation changes the silhouette. The centroid heuristic is disabled by default. Enable it only for packages whose stable region makes it meaningful, or replace it with a project-specific stable-region comparison.

## Acceptance rule

A V1 package is technically acceptable only when:

- the `delivery` stage exits zero;
- no blocking or major defect remains;
- the Godot fresh-import test has been performed;
- the human visual scorecard passes;
- the resulting `qa-report.json` is included in the delivery package.
