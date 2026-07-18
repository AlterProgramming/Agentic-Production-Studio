import { normalizeStrokeTemplate } from "./template.js";

const canvas = document.querySelector("#templateCanvas");
const context = canvas.getContext("2d");
const viewer = document.querySelector("#viewerCanvas");
const viewerContext = viewer.getContext("2d");
const output = document.querySelector("#templateOutput");
let strokes = [], current = null, pointerId = null;

function point(event, target = canvas) {
  const bounds = target.getBoundingClientRect();
  return { x: (event.clientX - bounds.left) * target.width / bounds.width, y: (event.clientY - bounds.top) * target.height / bounds.height };
}
function drawStroke(ctx, stroke, width = 4) {
  if (!stroke?.length) return;
  ctx.beginPath(); ctx.moveTo(stroke[0].x, stroke[0].y);
  stroke.slice(1).forEach(item => ctx.lineTo(item.x, item.y));
  ctx.strokeStyle = "#4d3a25"; ctx.lineWidth = width; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke();
}
function render() {
  context.clearRect(0, 0, canvas.width, canvas.height);
  strokes.forEach(stroke => drawStroke(context, stroke));
  if (current) drawStroke(context, current, 3);
  updateOutput();
}
function entry() {
  return {
    id: document.querySelector("#entryId").value.trim(),
    displayName: document.querySelector("#entryName").value.trim(),
    kind: document.querySelector("#entryKind").value,
    recognitionRotationInvariant: document.querySelector("#rotationInvariant").checked,
    semantic: { builderOperation: document.querySelector("#builderOperation").value.trim() || null },
    strokeTemplate: normalizeStrokeTemplate(strokes),
  };
}
function updateOutput() {
  output.value = JSON.stringify(entry(), null, 2);
}
function renderTemplate(value) {
  const template = value?.strokeTemplate ?? value;
  if (!template?.strokes?.length) throw new Error("JSON does not contain strokeTemplate.strokes");
  viewerContext.clearRect(0, 0, viewer.width, viewer.height);
  const margin = 24, scale = Math.min(viewer.width - margin * 2, viewer.height - margin * 2);
  template.strokes.forEach(stroke => drawStroke(viewerContext, stroke.map(item => ({ x: margin + item.x * scale, y: margin + item.y * scale })), 4));
}
function download(value) {
  const blob = new Blob([JSON.stringify(value, null, 2) + "\n"], { type: "application/json" });
  const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `${value.id || "operator"}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 0);
}

canvas.addEventListener("pointerdown", event => { if (pointerId !== null) return; pointerId = event.pointerId; canvas.setPointerCapture(pointerId); current = [point(event)]; });
canvas.addEventListener("pointermove", event => { if (event.pointerId !== pointerId || !current) return; current.push(point(event)); render(); });
function finish(event) { if (event.pointerId !== pointerId || !current) return; current.push(point(event)); if (current.length > 1) strokes.push(current); current = null; pointerId = null; render(); }
canvas.addEventListener("pointerup", finish); canvas.addEventListener("pointercancel", finish);
document.querySelector("#undoTemplate").addEventListener("click", () => { strokes.pop(); render(); });
document.querySelector("#clearTemplate").addEventListener("click", () => { strokes = []; render(); });
document.querySelector("#sampleTemplate").addEventListener("click", () => { strokes = [[{ x: 250, y: 330 }, { x: 360, y: 160 }, { x: 470, y: 330 }, { x: 250, y: 330 }]]; render(); });
document.querySelector("#exportTemplate").addEventListener("click", () => download(entry()));
document.querySelector("#renderTemplate").addEventListener("click", () => { try { renderTemplate(JSON.parse(document.querySelector("#viewerInput").value)); } catch (error) { alert(error.message); } });
["#entryId", "#entryName", "#entryKind", "#builderOperation", "#rotationInvariant"].forEach(selector => document.querySelector(selector).addEventListener("input", updateOutput));
output.addEventListener("input", () => { document.querySelector("#viewerInput").value = output.value; });
render(); document.querySelector("#viewerInput").value = output.value; renderTemplate(entry());
