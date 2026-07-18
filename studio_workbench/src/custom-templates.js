import { parseStudioGlyph } from "./core.js";
import { matchStrokeTemplates } from "./template.js";

export function parseStudioGlyphWithTemplates(strokes, options = {}) {
  const ast = parseStudioGlyph(strokes, options);
  const templates = options.templates ?? [];
  if (!templates.length || !ast.unknowns.length) return ast;
  const promoted = [];
  const remaining = [];
  const candidateById = new Map(ast.candidates.map(candidate => [candidate.candidateId, candidate]));
  for (const unknown of ast.unknowns) {
    const match = matchStrokeTemplates(unknown.strokeIds.map(index => strokes[index]), templates, options.templateOptions);
    if (!match?.recognized) {
      remaining.push({ ...unknown, bestTemplateGuess: match });
      continue;
    }
    const recognition = { ...unknown, id: match.id, kind: match.kind, confidence: match.confidence, semantic: match.semantic, recognitionMode: "template" };
    promoted.push(recognition);
    const candidate = candidateById.get(unknown.candidateId);
    if (candidate) Object.assign(candidate, recognition);
  }
  ast.symbols = [...ast.symbols, ...promoted];
  ast.unknowns = remaining;
  ast.metrics.symbolCount = ast.symbols.length;
  ast.metrics.unknownCount = remaining.length;
  ast.warnings = ast.warnings.filter(warning => warning !== "unknown_symbols" || remaining.length);
  const qualityParts = [ast.scope.roundness ?? 0, ...ast.symbols.map(item => item.confidence)];
  ast.metrics.quality = Number((qualityParts.reduce((sum, value) => sum + value, 0) / Math.max(1, qualityParts.length)).toFixed(3));
  return ast;
}
