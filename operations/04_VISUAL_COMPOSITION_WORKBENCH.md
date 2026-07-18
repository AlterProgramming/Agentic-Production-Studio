# Visual Composition Workbench

## Purpose

The workbench is a visual front end for the surgical builder. It allows an operator to express a bounded production recipe as a drawing while preserving deterministic contracts beneath the interface.

## Operating sequence

1. Draw one enclosing scope ring.
2. Place production operators clockwise inside it.
3. Add policy modifiers near the center.
4. Inspect recognition and compilation diagnostics.
5. Supply exact execution bindings.
6. Export the generated Surgical Builder Plan v1 JSON.
7. Run `studio_builder plan` to preview the write set.
8. Apply only after review and retain the receipt.

## Contracts

### StudioGlyphAST

Owns detected scope geometry, recognized symbols, unknown candidates, quality metrics, and parser warnings.

### StudioIR

Owns ordered stages, dependency intent, strictness, evidence requirements, validity, quality, warnings, and composition signature.

### Builder plan

Owns exact paths, preconditions, deterministic operations, and postconditions. The visual workbench does not bypass builder confinement or receipts.

## Current operator grammar

| Mark | Operator | Builder capability |
|---|---|---|
| Circle | Input | Source precondition |
| Triangle | Normalize | `image_normalize` |
| Square | Palette | `palette_enforce` |
| Diamond | Contact sheet | `contact_sheet` |
| Arrow | Godot | `godot_spriteframes_compile` |
| Zigzag | Package | `package_zip` |
| Plus | Strict modifier | Blocks unresolved diagnostics |
| Check | Evidence modifier | Adds output postconditions |
| Parallel lines | Parallel modifier | Records scheduling intent |

## Review boundary

The workbench can suggest and compile operations, but it cannot invent missing source paths, anchors, dimensions, palettes, frames, event timing, or delivery contents. Missing bindings remain blocking diagnostics.
