import { OPERATOR_DICTIONARY } from "./dictionary.js";
export const WORKBENCH_VERSION = "1.0";

const TAU = Math.PI * 2;
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const degrees = radians => radians * 180 / Math.PI;

export function cleanStroke(stroke, minDistance = 2) {
  if (!Array.isArray(stroke)) return [];
  const cleaned = [];
  for (const point of stroke) {
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) continue;
    const next = { x: Number(point.x), y: Number(point.y), t: Number.isFinite(point.t) ? Number(point.t) : null };
    if (!cleaned.length || distance(cleaned.at(-1), next) >= minDistance) cleaned.push(next);
  }
  return cleaned;
}

export function boundsOf(points) {
  if (!points.length) return { x: 0, y: 0, width: 0, height: 0, right: 0, bottom: 0 };
  const xs = points.map(point => point.x);
  const ys = points.map(point => point.y);
  const x = Math.min(...xs), y = Math.min(...ys), right = Math.max(...xs), bottom = Math.max(...ys);
  return { x, y, right, bottom, width: right - x, height: bottom - y };
}

function polylineLength(points) {
  let value = 0;
  for (let index = 1; index < points.length; index += 1) value += distance(points[index - 1], points[index]);
  return value;
}

function signedArea(points) {
  let area = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index], next = points[(index + 1) % points.length];
    area += current.x * next.y - next.x * current.y;
  }
  return area / 2;
}

function centroid(points) {
  if (!points.length) return { x: 0, y: 0 };
  return {
    x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
    y: points.reduce((sum, point) => sum + point.y, 0) / points.length,
  };
}

function angleDelta(first, second) {
  let value = second - first;
  while (value > Math.PI) value -= TAU;
  while (value < -Math.PI) value += TAU;
  return value;
}

function simplify(points, thresholdDeg = 32) {
  if (points.length < 3) return points;
  const output = [points[0]];
  for (let index = 1; index < points.length - 1; index += 1) {
    const before = Math.atan2(points[index].y - points[index - 1].y, points[index].x - points[index - 1].x);
    const after = Math.atan2(points[index + 1].y - points[index].y, points[index + 1].x - points[index].x);
    if (Math.abs(degrees(angleDelta(before, after))) >= thresholdDeg) output.push(points[index]);
  }
  output.push(points.at(-1));
  return output;
}

function strokeDescriptor(points) {
  const bounds = boundsOf(points);
  const diagonal = Math.max(1, Math.hypot(bounds.width, bounds.height));
  const length = polylineLength(points);
  const closure = points.length > 2 ? distance(points[0], points.at(-1)) / diagonal : 1;
  const closed = closure <= 0.24;
  const simple = simplify(points);
  const cornerCount = Math.max(0, simple.length - (closed ? 1 : 2));
  const center = centroid(points);
  const radii = points.map(point => distance(point, center));
  const meanRadius = radii.reduce((sum, value) => sum + value, 0) / Math.max(1, radii.length);
  const radiusStd = Math.sqrt(radii.reduce((sum, value) => sum + (value - meanRadius) ** 2, 0) / Math.max(1, radii.length));
  return {
    bounds,
    center,
    length,
    closure,
    closed,
    cornerCount,
    straightness: length ? distance(points[0], points.at(-1)) / length : 0,
    aspect: bounds.height ? bounds.width / bounds.height : bounds.width ? Infinity : 1,
    area: Math.abs(signedArea(points)),
    roundness: meanRadius ? clamp(1 - radiusStd / meanRadius) : 0,
    simple,
  };
}

export function detectScopeRing(strokes) {
  const candidates = strokes
    .map((stroke, index) => ({ index, stroke, descriptor: strokeDescriptor(stroke) }))
    .filter(item => item.stroke.length >= 8 && item.descriptor.closure <= 0.75 && item.descriptor.area > 400)
    .sort((a, b) => b.descriptor.area - a.descriptor.area);
  if (!candidates.length) return { found: false, complete: false, strokeIndex: null, center: null, radius: 0, roundness: 0 };
  const chosen = candidates[0];
  const center = chosen.descriptor.center;
  const radius = chosen.stroke.reduce((sum, point) => sum + distance(point, center), 0) / chosen.stroke.length;
  return {
    found: true,
    complete: chosen.descriptor.closure <= 0.18 && chosen.descriptor.roundness >= 0.45,
    strokeIndex: chosen.index,
    center,
    radius,
    closure: chosen.descriptor.closure,
    roundness: chosen.descriptor.roundness,
    bounds: chosen.descriptor.bounds,
  };
}

function expandedOverlap(first, second, margin = 14) {
  return !(first.right + margin < second.x || second.right + margin < first.x || first.bottom + margin < second.y || second.bottom + margin < first.y);
}

function groupCandidateStrokes(strokes, ignoredIndex) {
  const entries = strokes
    .map((stroke, index) => ({ index, stroke, descriptor: strokeDescriptor(stroke) }))
    .filter(item => item.index !== ignoredIndex && item.stroke.length >= 2);
  const groups = [];
  const used = new Set();
  for (const entry of entries) {
    if (used.has(entry.index)) continue;
    const group = [entry];
    used.add(entry.index);
    let changed = true;
    while (changed) {
      changed = false;
      for (const candidate of entries) {
        if (used.has(candidate.index)) continue;
        if (group.some(item => expandedOverlap(item.descriptor.bounds, candidate.descriptor.bounds))) {
          group.push(candidate);
          used.add(candidate.index);
          changed = true;
        }
      }
    }
    groups.push(group);
  }
  return groups;
}

function lineAngle(points) {
  const first = points[0], last = points.at(-1);
  return Math.atan2(last.y - first.y, last.x - first.x);
}

function angleDistanceToAxes(angle, diagonal = false) {
  const base = diagonal ? Math.PI / 4 : 0;
  let best = Infinity;
  for (let index = -4; index <= 4; index += 1) best = Math.min(best, Math.abs(angleDelta(base + index * Math.PI / 2, angle)));
  return best;
}

function segmentsIntersect(a, b, c, d) {
  const cross = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  const abC = cross(a, b, c), abD = cross(a, b, d), cdA = cross(c, d, a), cdB = cross(c, d, b);
  return abC * abD <= 0 && cdA * cdB <= 0;
}

function recognizeGroup(group, ring) {
  const allPoints = group.flatMap(item => item.stroke);
  const descriptor = strokeDescriptor(allPoints);
  const center = descriptor.center;
  const radiusNorm = ring.found ? distance(center, ring.center) / Math.max(1, ring.radius) : 0;
  const angleDeg = ring.found ? (degrees(Math.atan2(center.y - ring.center.y, center.x - ring.center.x)) + 360) % 360 : 0;
  const common = { strokeIds: group.map(item => item.index), center, bounds: descriptor.bounds, radiusNorm, angleDeg };

  if (group.length === 2 && group.every(item => item.descriptor.straightness > 0.9)) {
    const [first, second] = group;
    const delta = Math.abs(degrees(angleDelta(lineAngle(first.stroke), lineAngle(second.stroke)))) % 180;
    const perpendicular = Math.abs(delta - 90) < 28;
    const crossing = segmentsIntersect(first.stroke[0], first.stroke.at(-1), second.stroke[0], second.stroke.at(-1));
    if (perpendicular && crossing) return { ...common, id: "strict", kind: "modifier", confidence: 0.92 };
    if (Math.min(delta, 180 - delta) < 20) return { ...common, id: "parallel", kind: "modifier", confidence: 0.88 };
  }

  if (group.length >= 3) {
    const sorted = [...group].sort((a, b) => b.descriptor.length - a.descriptor.length);
    if (sorted[0].descriptor.straightness > 0.85 && sorted.slice(1, 3).every(item => item.descriptor.straightness > 0.75)) {
      return { ...common, id: "godot", kind: "operator", confidence: 0.82 };
    }
  }

  if (group.length === 1) {
    const item = group[0], feature = item.descriptor;
    if (feature.closed) {
      if (feature.cornerCount <= 2 && feature.roundness > 0.62) return { ...common, id: "input", kind: "operator", confidence: clamp(0.62 + feature.roundness * 0.34) };
      if (feature.cornerCount === 3) return { ...common, id: "normalize", kind: "operator", confidence: 0.86 };
      if (feature.cornerCount >= 4 && feature.cornerCount <= 6) {
        const edges = feature.simple.slice(1).map((point, index) => Math.atan2(point.y - feature.simple[index].y, point.x - feature.simple[index].x));
        const cardinal = edges.reduce((sum, angle) => sum + angleDistanceToAxes(angle, false), 0) / Math.max(1, edges.length);
        const diagonal = edges.reduce((sum, angle) => sum + angleDistanceToAxes(angle, true), 0) / Math.max(1, edges.length);
        return { ...common, id: cardinal <= diagonal ? "palette" : "contact-sheet", kind: "operator", confidence: 0.84 };
      }
    }
    if (!feature.closed && feature.cornerCount === 1 && feature.simple.length >= 3) {
      const firstLength = distance(feature.simple[0], feature.simple[1]);
      const secondLength = distance(feature.simple[1], feature.simple[2]);
      if (secondLength > firstLength * 1.2) return { ...common, id: "evidence", kind: "modifier", confidence: 0.84 };
    }
    if (!feature.closed && feature.cornerCount >= 2) return { ...common, id: "package", kind: "operator", confidence: 0.78 };
  }
  return { ...common, id: null, kind: "unknown", confidence: 0, descriptor: { strokeCount: group.length, closed: descriptor.closed, corners: descriptor.cornerCount } };
}

export function parseStudioGlyph(strokes, options = {}) {
  const cleanedStrokes = (strokes ?? []).map(stroke => cleanStroke(stroke, options.minDistance ?? 2)).filter(stroke => stroke.length >= 2);
  const scope = detectScopeRing(cleanedStrokes);
  const groups = groupCandidateStrokes(cleanedStrokes, scope.strokeIndex);
  const recognitions = groups.map(group => recognizeGroup(group, scope));
  const symbols = recognitions.filter(item => item.id);
  const unknowns = recognitions.filter(item => !item.id);
  const warnings = [];
  if (!scope.found) warnings.push("no_scope_ring");
  else if (!scope.complete) warnings.push("scope_ring_incomplete");
  if (unknowns.length) warnings.push("unknown_symbols");
  const duplicateInputs = symbols.filter(item => item.id === "input");
  if (duplicateInputs.length > 1) warnings.push("multiple_inputs");
  const qualityParts = [scope.roundness ?? 0, ...symbols.map(item => item.confidence)];
  const quality = qualityParts.length ? qualityParts.reduce((sum, value) => sum + value, 0) / qualityParts.length : 0;
  return {
    type: "StudioGlyphAST",
    version: WORKBENCH_VERSION,
    scope,
    candidates: recognitions.map((item, index) => ({ candidateId: `c${index + 1}`, ...item })),
    symbols,
    unknowns,
    metrics: { quality: Number(quality.toFixed(3)), symbolCount: symbols.length, unknownCount: unknowns.length },
    warnings,
  };
}

const OPERATOR_ORDER = OPERATOR_DICTIONARY.slice().sort((a, b) => a.order - b.order).map(item => item.id);

export function compileStudioIR(ast) {
  const symbols = [...(ast?.symbols ?? [])];
  const operators = symbols.filter(item => item.kind === "operator");
  const modifiers = symbols.filter(item => item.kind === "modifier");
  const ordered = operators.sort((a, b) => ((a.angleDeg + 90) % 360) - ((b.angleDeg + 90) % 360));
  const warnings = [...(ast?.warnings ?? [])];
  if (!ordered.some(item => item.id === "input")) warnings.push("missing_input");
  const duplicates = OPERATOR_ORDER.filter(id => ordered.filter(item => item.id === id).length > 1);
  if (duplicates.length) warnings.push(...duplicates.map(id => `duplicate_${id}`));
  const stages = ordered.map((symbol, index) => ({
    id: `stage-${index + 1}`,
    operator: symbol.id,
    confidence: symbol.confidence,
    dependsOn: index ? [`stage-${index}`] : [],
    angleDeg: symbol.angleDeg,
  }));
  const valid = Boolean(ast?.scope?.complete) && warnings.every(item => !["no_scope_ring", "scope_ring_incomplete", "multiple_inputs", "missing_input", "unknown_symbols"].includes(item));
  return {
    type: "StudioIR",
    version: WORKBENCH_VERSION,
    valid,
    prepared: Boolean(ast?.scope?.found) && !ast?.scope?.complete,
    status: valid ? "Executable composition" : ast?.scope?.found ? "Composition requires correction" : "Draw a scope ring",
    stages,
    policy: {
      strict: modifiers.some(item => item.id === "strict"),
      evidenceRequired: modifiers.some(item => item.id === "evidence"),
      parallelRequested: modifiers.some(item => item.id === "parallel"),
    },
    quality: ast?.metrics?.quality ?? 0,
    warnings: [...new Set(warnings)],
    signature: stages.map(stage => stage.operator).join(">") + `:${modifiers.map(item => item.id).sort().join(",")}`,
  };
}

function requireBinding(bindings, key, diagnostics) {
  const value = bindings?.[key];
  if (value === undefined || value === null || value === "") diagnostics.push({ severity: "blocking", code: `missing_binding.${key}`, message: `Binding ${key} is required.` });
  return value;
}

export function compileBuilderPlan(ir, bindings = {}) {
  const diagnostics = [];
  const operations = [];
  const preconditions = [];
  const postconditions = [];
  const allowed = new Set(bindings.allowed_paths ?? ["build/**", "godot/**", "delivery/**"]);
  let current = bindings.source_path;
  const frames = bindings.frame_paths ?? [];
  const outputs = [];

  for (const stage of ir?.stages ?? []) {
    if (stage.operator === "input") {
      current = requireBinding(bindings, "source_path", diagnostics);
      if (current) preconditions.push({ id: "source-exists", type: "exists", path: current, value: true });
    } else if (stage.operator === "normalize") {
      const target = requireBinding(bindings, "normalized_path", diagnostics);
      const canvas = requireBinding(bindings, "canvas", diagnostics);
      const sourceAnchor = requireBinding(bindings, "source_anchor", diagnostics);
      const targetAnchor = requireBinding(bindings, "target_anchor", diagnostics);
      if (current && target && canvas && sourceAnchor && targetAnchor) {
        operations.push({ id: stage.id, type: "image_normalize", source: current, target, canvas, source_anchor: sourceAnchor, target_anchor: targetAnchor, overwrite: true });
        current = target; outputs.push(target);
      }
    } else if (stage.operator === "palette") {
      const target = requireBinding(bindings, "palette_path", diagnostics);
      const palette = requireBinding(bindings, "palette", diagnostics);
      if (current && target && palette) {
        operations.push({ id: stage.id, type: "palette_enforce", source: current, target, palette, overwrite: true });
        current = target; outputs.push(target);
      }
    } else if (stage.operator === "contact-sheet") {
      const target = requireBinding(bindings, "contact_sheet_path", diagnostics);
      const sources = frames.length ? frames : current ? [current] : [];
      if (target && sources.length) {
        operations.push({ id: stage.id, type: "contact_sheet", sources, target, columns: bindings.contact_sheet_columns ?? sources.length, scale: bindings.preview_scale ?? 4, padding: bindings.preview_padding ?? 2, overwrite: true });
        outputs.push(target);
      }
    } else if (stage.operator === "godot") {
      const target = requireBinding(bindings, "godot_target", diagnostics);
      const animationName = requireBinding(bindings, "animation_name", diagnostics);
      const fps = requireBinding(bindings, "fps", diagnostics);
      const loop = requireBinding(bindings, "loop", diagnostics);
      if (!frames.length) diagnostics.push({ severity: "blocking", code: "missing_binding.frame_paths", message: "Godot compilation requires frame_paths." });
      if (target && animationName && fps && typeof loop === "boolean" && frames.length) {
        operations.push({ id: stage.id, type: "godot_spriteframes_compile", frame_paths: frames, target, metadata_target: bindings.godot_metadata_target, animation_name: animationName, fps, loop, anchor: bindings.anchor, events: bindings.events ?? [], overwrite: true });
        outputs.push(target); if (bindings.godot_metadata_target) outputs.push(bindings.godot_metadata_target);
      }
    } else if (stage.operator === "package") {
      const target = requireBinding(bindings, "package_target", diagnostics);
      const sources = bindings.package_sources ?? [...new Set([...frames, ...outputs])];
      if (target && sources.length) {
        operations.push({ id: stage.id, type: "package_zip", sources, target, prefix: bindings.package_prefix ?? "studio-delivery", overwrite: true });
        outputs.push(target);
      } else if (!sources.length) diagnostics.push({ severity: "blocking", code: "missing_binding.package_sources", message: "Packaging requires package_sources or prior outputs." });
    }
  }

  for (const path of outputs) postconditions.push({ id: `exists-${path.replaceAll("/", "-")}`, type: "exists", path, value: true });
  if (ir?.policy?.evidenceRequired) postconditions.push(...outputs.map(path => ({ id: `bounded-${path.replaceAll("/", "-")}`, type: "max_bytes", path, value: bindings.max_output_bytes ?? 20_000_000 })));
  if (ir?.policy?.strict && diagnostics.some(item => item.severity !== "info")) diagnostics.push({ severity: "blocking", code: "strict_policy", message: "Strict policy blocks plans with unresolved diagnostics." });
  if (!operations.length) diagnostics.push({ severity: "blocking", code: "no_operations", message: "The composition did not produce executable operations." });

  return {
    plan: {
      schema_version: "1.0",
      plan_id: bindings.plan_id ?? `workbench-${Date.now()}`,
      description: bindings.description ?? `Compiled from StudioIR ${ir?.signature ?? "unknown"}`,
      allowed_paths: [...allowed],
      preconditions,
      operations,
      postconditions,
    },
    diagnostics,
    executable: Boolean(ir?.valid) && !diagnostics.some(item => item.severity === "blocking"),
  };
}

export const SAMPLE_STROKES = (() => {
  const circle = (cx, cy, radius, count = 64, phase = 0) => Array.from({ length: count + 1 }, (_, index) => {
    const angle = phase + TAU * index / count;
    return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
  });
  const polygon = points => [...points, points[0]];
  return [
    circle(360, 260, 205),
    circle(360, 95, 22),
    polygon([{ x: 485, y: 145 }, { x: 520, y: 205 }, { x: 450, y: 205 }]),
    polygon([{ x: 490, y: 305 }, { x: 535, y: 305 }, { x: 535, y: 350 }, { x: 490, y: 350 }]),
    polygon([{ x: 315, y: 420 }, { x: 355, y: 380 }, { x: 395, y: 420 }, { x: 355, y: 460 }]),
    [{ x: 165, y: 320 }, { x: 190, y: 290 }, { x: 215, y: 330 }, { x: 245, y: 290 }],
    [{ x: 322, y: 245 }, { x: 398, y: 245 }],
    [{ x: 360, y: 207 }, { x: 360, y: 283 }],
    [{ x: 290, y: 338 }, { x: 307, y: 355 }, { x: 340, y: 315 }],
  ];
})();
