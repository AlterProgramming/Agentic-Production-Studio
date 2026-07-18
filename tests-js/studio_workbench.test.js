import test from "node:test";
import assert from "node:assert/strict";
import { SAMPLE_STROKES, compileBuilderPlan, compileStudioIR, parseStudioGlyph } from "../studio_workbench/src/core.js";

function circle(cx, cy, radius, count = 64) {
  return Array.from({ length: count + 1 }, (_, index) => {
    const angle = Math.PI * 2 * index / count;
    return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
  });
}

function polygon(points) { return [...points, points[0]]; }

test("sample composition parses to a bounded AST and StudioIR", () => {
  const ast = parseStudioGlyph(SAMPLE_STROKES);
  const ir = compileStudioIR(ast);
  assert.equal(ast.scope.found, true);
  assert.equal(ast.scope.complete, true);
  assert.ok(ast.symbols.some(symbol => symbol.id === "input"));
  assert.ok(ast.symbols.some(symbol => symbol.id === "normalize"));
  assert.ok(ast.symbols.some(symbol => symbol.id === "package"));
  assert.equal(ir.valid, true);
  assert.equal(ir.policy.strict, true);
  assert.equal(ir.policy.evidenceRequired, true);
});

test("open scope produces a prepared but invalid composition", () => {
  const openRing = circle(200, 200, 150).slice(0, 50);
  const ast = parseStudioGlyph([openRing, circle(200, 100, 20)]);
  const ir = compileStudioIR(ast);
  assert.equal(ir.valid, false);
  assert.ok(ast.warnings.includes("no_scope_ring") || ast.warnings.includes("scope_ring_incomplete"));
});

test("square and diamond compile to different operators", () => {
  const ring = circle(200, 200, 170);
  const square = polygon([{ x: 120, y: 180 }, { x: 150, y: 180 }, { x: 150, y: 210 }, { x: 120, y: 210 }]);
  const diamond = polygon([{ x: 250, y: 180 }, { x: 280, y: 210 }, { x: 250, y: 240 }, { x: 220, y: 210 }]);
  const input = circle(200, 100, 20);
  const ast = parseStudioGlyph([ring, input, square, diamond]);
  assert.ok(ast.symbols.some(symbol => symbol.id === "palette"));
  assert.ok(ast.symbols.some(symbol => symbol.id === "contact-sheet"));
});

test("builder plan maps visual operators to executable builder operations", () => {
  const ast = parseStudioGlyph(SAMPLE_STROKES);
  const ir = compileStudioIR(ast);
  const compiled = compileBuilderPlan(ir, {
    plan_id: "visual-pipeline",
    allowed_paths: ["build/**", "godot/**", "delivery/**"],
    source_path: "source/storm.png",
    normalized_path: "build/storm-normalized.png",
    palette_path: "build/storm-palette.png",
    contact_sheet_path: "build/contact.png",
    package_target: "delivery/storm.zip",
    canvas: { width: 128, height: 128 },
    source_anchor: { x: 32, y: 60 },
    target_anchor: { x: 64, y: 110 },
    palette: ["#000000", "#ffffff"],
    package_sources: ["build/storm-palette.png", "build/contact.png"],
  });
  assert.equal(compiled.executable, true);
  assert.ok(compiled.plan.operations.some(operation => operation.type === "image_normalize"));
  assert.ok(compiled.plan.operations.some(operation => operation.type === "palette_enforce"));
  assert.ok(compiled.plan.operations.some(operation => operation.type === "contact_sheet"));
  assert.ok(compiled.plan.operations.some(operation => operation.type === "package_zip"));
});

test("missing bindings are exposed as blocking diagnostics", () => {
  const ast = parseStudioGlyph(SAMPLE_STROKES);
  const ir = compileStudioIR(ast);
  const compiled = compileBuilderPlan(ir, { source_path: "source/storm.png" });
  assert.equal(compiled.executable, false);
  assert.ok(compiled.diagnostics.some(item => item.severity === "blocking"));
});
