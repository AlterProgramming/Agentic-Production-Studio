# Retained-scene character performance benchmark

This benchmark closes the camera-only-motion failure mode.

A moving camera is not accepted as evidence that a retained scene supports movement. The benchmark requires independent transforms on named character nodes, an authored action/reaction sequence, and measured displacement in the completion receipt.

## Performance sequence

1. Both figures hold attention with subtle body motion.
2. Character B shifts weight and advances.
3. Character B turns the head and raises the near arm.
4. Character A yields half a step, lifts the chin, and answers with a guarded arm movement.
5. Both figures lower their arms and settle at a changed distance.

## Accepted runtime evidence

The local benchmark produced a 13-second retained-scene performance derivative at 18 fps. Its receipt measured the following world-space spans:

- `Characters/Character_A/Hand_R`: 0.879466 m
- `Characters/Character_A/Head`: 0.135814 m
- `Characters/Character_B/Hand_L`: 1.216327 m
- `Characters/Character_B/Head`: 0.078377 m

The retained GLB contained 103 geometry nodes. The performance renderer moved separate body roots, heads, upper arms, forearms, hands, and legs while the environment remained static. Camera changes provided coverage of the action but were not used as the motion acceptance signal.

## Fail-closed rules

The benchmark fails when any of the following is true:

- only the camera changes;
- fewer than four performance beats are authored;
- either character lacks measured body-node displacement;
- head and hand displacement remain below 0.05 m;
- the receipt merely asserts movement without measurements;
- the environment is moved to simulate character action.

## Entrypoint

```bash
python3 tools/retained_scene_performance.py emit-contract /tmp/performance-contract.json
python3 tools/retained_scene_performance.py verify-receipt <performance-receipt.json>
```

The renderer and generated visual evidence remain benchmark artifacts rather than repository source. The repository stores the deterministic performance contract and its negative tests so future runtimes can reproduce or reject the same behavior.
