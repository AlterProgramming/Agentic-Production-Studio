const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

function strokeLength(stroke) {
  let total = 0;
  for (let index = 1; index < stroke.length; index += 1) total += distance(stroke[index - 1], stroke[index]);
  return total;
}

function resampleStroke(stroke, count = 24) {
  const clean = (stroke ?? []).filter(point => Number.isFinite(point?.x) && Number.isFinite(point?.y)).map(point => ({ x: Number(point.x), y: Number(point.y) }));
  if (!clean.length) return [];
  if (clean.length === 1 || strokeLength(clean) === 0) return Array.from({ length: count }, () => ({ ...clean[0] }));
  const segments = [];
  let total = 0;
  for (let index = 1; index < clean.length; index += 1) {
    const length = distance(clean[index - 1], clean[index]);
    segments.push({ from: clean[index - 1], to: clean[index], start: total, length });
    total += length;
  }
  return Array.from({ length: count }, (_, index) => {
    const target = total * index / Math.max(1, count - 1);
    const segment = segments.find(item => target <= item.start + item.length) ?? segments.at(-1);
    const ratio = segment.length ? (target - segment.start) / segment.length : 0;
    return {
      x: segment.from.x + (segment.to.x - segment.from.x) * ratio,
      y: segment.from.y + (segment.to.y - segment.from.y) * ratio,
    };
  });
}

export function normalizeStrokeTemplate(strokes, pointsPerStroke = 24) {
  const sampled = (strokes ?? []).map(stroke => resampleStroke(stroke, pointsPerStroke)).filter(stroke => stroke.length);
  const points = sampled.flat();
  if (!points.length) return { sourceAspectRatio: 1, pointsPerStroke, strokes: [] };
  const xs = points.map(point => point.x), ys = points.map(point => point.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const width = Math.max(1e-9, maxX - minX), height = Math.max(1e-9, maxY - minY);
  const scale = Math.max(width, height);
  const offsetX = (1 - width / scale) / 2;
  const offsetY = (1 - height / scale) / 2;
  return {
    sourceAspectRatio: Number((width / height).toFixed(6)),
    pointsPerStroke,
    strokes: sampled.map(stroke => stroke.map(point => ({
      x: Number((offsetX + (point.x - minX) / scale).toFixed(6)),
      y: Number((offsetY + (point.y - minY) / scale).toFixed(6)),
    }))),
  };
}

function rotateTemplate(template, radians) {
  const cosine = Math.cos(radians), sine = Math.sin(radians);
  return {
    ...template,
    strokes: template.strokes.map(stroke => stroke.map(point => {
      const x = point.x - .5, y = point.y - .5;
      return { x: .5 + x * cosine - y * sine, y: .5 + x * sine + y * cosine };
    })),
  };
}

function permutations(values) {
  if (values.length <= 1) return [values];
  const output = [];
  values.forEach((value, index) => {
    const remaining = values.filter((_, candidateIndex) => candidateIndex !== index);
    for (const suffix of permutations(remaining)) output.push([value, ...suffix]);
  });
  return output;
}

function strokeDistance(first, second) {
  if (!first.length || first.length !== second.length) return Infinity;
  const direct = first.reduce((sum, point, index) => sum + distance(point, second[index]), 0) / first.length;
  const reversed = first.reduce((sum, point, index) => sum + distance(point, second[second.length - 1 - index]), 0) / first.length;
  return Math.min(direct, reversed);
}

function templateDistance(first, second) {
  if (first.strokes.length !== second.strokes.length || !first.strokes.length) return Infinity;
  const indexes = first.strokes.map((_, index) => index);
  const orders = indexes.length <= 5 ? permutations(indexes) : [indexes];
  let best = Infinity;
  for (const order of orders) {
    const value = order.reduce((sum, sourceIndex, targetIndex) => sum + strokeDistance(first.strokes[sourceIndex], second.strokes[targetIndex]), 0) / order.length;
    best = Math.min(best, value);
  }
  return best;
}

export function matchStrokeTemplates(strokes, entries, options = {}) {
  const pointsPerStroke = options.pointsPerStroke ?? 24;
  const candidate = normalizeStrokeTemplate(strokes, pointsPerStroke);
  let best = null;
  for (const entry of entries ?? []) {
    if (!entry?.strokeTemplate?.strokes?.length) continue;
    const reference = normalizeStrokeTemplate(entry.strokeTemplate.strokes, pointsPerStroke);
    const rotations = entry.recognitionRotationInvariant ? Array.from({ length: options.rotationSteps ?? 16 }, (_, index) => Math.PI * 2 * index / (options.rotationSteps ?? 16)) : [0];
    for (const radians of rotations) {
      const score = templateDistance(candidate, radians ? rotateTemplate(reference, radians) : reference);
      if (!best || score < best.distance) best = { entry, distance: score, rotationRadians: radians };
    }
  }
  if (!best) return null;
  const confidence = clamp(1 - best.distance / (options.distanceBudget ?? .34));
  return {
    id: best.entry.id,
    kind: best.entry.kind ?? "operator",
    displayName: best.entry.displayName ?? best.entry.id,
    confidence: Number(confidence.toFixed(4)),
    distance: Number(best.distance.toFixed(6)),
    rotationRadians: Number(best.rotationRadians.toFixed(6)),
    semantic: best.entry.semantic ?? {},
    recognized: confidence >= (best.entry.minimumConfidence ?? options.minimumConfidence ?? .62),
  };
}
