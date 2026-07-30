# Model-First Visual Generation — Session Bootstrap

Canonical memory and executable capability are separate. Loading `visual-generation.model-first.v1` establishes the governing rule; a session may claim the ability only after discovering and invoking the first-party runtime.

## Required startup sequence

When a request may require retained visual continuity:

1. Retrieve `capabilities/model-first-visual-generation/capability.json`.
2. Request `GET https://api.brightengine.live/v1/capabilities/model-first`.
3. Require all of the following descriptor values:
   - `capability_id = visual-generation.model-first.v1`
   - `status = active`
   - `execution = first_party_local`
   - `external_providers = false`
4. Resolve a request-bound Forge capability containing:
   - `forge:model-first:execute`
   - `forge:model-first:read`
5. Write the request as canonical JSON. The exact bytes must match the capability's `request_sha256` claim.
6. Invoke the runtime with the session client:

```bash
node capabilities/model-first-visual-generation/runtime/invoke.mjs \
  --request REQUEST.json \
  --token-file CAPABILITY.token \
  --out OUTPUT_DIR
```

7. Verify `OUTPUT_DIR/session-receipt.json` and the downloaded `receipt.json`.
8. Only claim completion when the receipt proves:
   - a retained GLB was written before the render;
   - the GLB reopened successfully;
   - validation passed;
   - the hero render hashes back to the same run;
   - recovery state was retained;
   - a motion or interactive derivative exists.

## Request contract

```json
{
  "prompt": "A presenter in a cool technology exhibit",
  "title": "Exhibit scene",
  "style": "cinematic studio",
  "source_image_base64": "optional PNG or JPEG bytes",
  "source_image_mime": "image/png",
  "metadata": {}
}
```

`source_image_base64` is optional. When omitted, BrightEngine creates a provider-free local concept texture. When supplied, the image may come from an allowed source stage, including a platform image generator, but it is embedded into a retained scene and is not treated as the terminal artifact.

## Output package

A successful run materializes:

```text
scene/scene.glb
scene/scene.json
scene/manifest.json
scene/recovery.json
renders/hero.png
renders/depth.png
renders/object_mask.png
motion/orbit.json
preview/index.html
receipt.json
session-receipt.json
```

## Fail-closed routing

A session must not silently fall back to a flat image when model-first completion was requested. It must disclose the narrower result when:

- capability discovery fails;
- the endpoint is not marked `first_party_local`;
- a request-bound token cannot be resolved;
- execution or artifact retrieval fails;
- the GLB was not written before rendering;
- reopen validation fails;
- the receipt or hashes do not reconcile.

The permitted fallback statement is:

> The model-first doctrine is loaded, but the deployed runtime could not be invoked in this session. Any flat image is only a labeled source or lightweight output, not a retained modeled scene.

## Completion boundary

The session client is a materialization and verification layer. BrightEngine owns signed execution and artifact access. Agentic Production Studio owns the capability contract and production doctrine. Agent Command Center owns startup routing. A memory entry, an `image_gen` result, or inaccessible state from another conversation cannot satisfy this boundary.
