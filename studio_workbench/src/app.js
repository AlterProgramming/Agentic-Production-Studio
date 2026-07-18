import { SAMPLE_STROKES, compileBuilderPlan, compileStudioIR, parseStudioGlyph } from "./core.js";

const drawCanvas = document.querySelector("#drawCanvas");
const flowCanvas = document.querySelector("#flowCanvas");
const drawContext = drawCanvas.getContext("2d");
const flowContext = flowCanvas.getContext("2d");
const bindingsInput = document.querySelector("#bindingsInput");
const defaultBindings = {
  plan_id: "storm-visual-pipeline",
  description: "Compiled by the Studio Composition Workbench",
  allowed_paths: ["build/**", "godot/**", "delivery/**"],
  source_path: "source/storm.png",
  normalized_path: "build/storm-normalized.png",
  palette_path: "build/storm-palette.png",
  contact_sheet_path: "build/storm-contact-sheet.png",
  godot_target: "godot/storm.tres",
  godot_metadata_target: "godot/storm.events.json",
  package_target: "delivery/storm-v1.zip",
  canvas: { width: 128, height: 128 },
  source_anchor: { x: 32, y: 60 },
  target_anchor: { x: 64, y: 110 },
  anchor: { x: 64, y: 110 },
  palette: ["#11151c", "#2e3b55", "#6d75a8", "#b8c4e8", "#f4f1df", "#f2bd4e"],
  frame_paths: ["frames/storm_000.png", "frames/storm_001.png", "frames/storm_002.png", "frames/storm_003.png"],
  animation_name: "storm_integrated_v1",
  fps: 8,
  loop: false,
  events: [{ event: "impact", frame: 2 }],
  preview_scale: 4,
  package_sources: ["build/storm-palette.png", "build/storm-contact-sheet.png", "godot/storm.tres", "godot/storm.events.json"]
};
bindingsInput.value = JSON.stringify(defaultBindings, null, 2);

let strokes = [];
let currentStroke = null;
let ast = null;
let ir = null;
let compiled = null;
let pointerId = null;

function canvasPoint(event) {
  const bounds = drawCanvas.getBoundingClientRect();
  return {
    x: (event.clientX - bounds.left) * drawCanvas.width / bounds.width,
    y: (event.clientY - bounds.top) * drawCanvas.height / bounds.height,
    t: performance.now(),
  };
}

function drawStroke(context, stroke, color = "#4d3a25", width = 4) {
  if (!stroke?.length) return;
  context.beginPath();
  context.moveTo(stroke[0].x, stroke[0].y);
  for (const point of stroke.slice(1)) context.lineTo(point.x, point.y);
  context.strokeStyle = color;
  context.lineWidth = width;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.stroke();
}

function renderDrawing() {
  drawContext.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  for (const stroke of strokes) drawStroke(drawContext, stroke);
  if (currentStroke) drawStroke(drawContext, currentStroke, "#806342", 3.5);
  if (ast?.scope?.found) {
    drawContext.beginPath();
    drawContext.arc(ast.scope.center.x, ast.scope.center.y, 5, 0, Math.PI * 2);
    drawContext.fillStyle = ast.scope.complete ? "#247f73" : "#b65e45";
    drawContext.fill();
  }
  for (const candidate of ast?.candidates ?? []) {
    if (!candidate.id) continue;
    drawContext.fillStyle = "rgba(21,26,33,.84)";
    drawContext.fillRect(candidate.center.x - 5, candidate.center.y - 5, 10, 10);
    drawContext.font = "12px ui-monospace";
    drawContext.fillText(candidate.id, candidate.center.x + 9, candidate.center.y + 4);
  }
}

function parseBindings() {
  try {
    const value = JSON.parse(bindingsInput.value);
    return { value, error: null };
  } catch (error) {
    return { value: {}, error: error.message };
  }
}

function recompute() {
  ast = parseStudioGlyph(strokes);
  ir = compileStudioIR(ast);
  const bindingState = parseBindings();
  compiled = compileBuilderPlan(ir, bindingState.value);
  if (bindingState.error) compiled.diagnostics.unshift({ severity: "blocking", code: "bindings.invalid_json", message: bindingState.error });
  updateInspector();
  renderDrawing();
}

function updateInspector() {
  document.querySelector("#astOutput").textContent = JSON.stringify(ast, null, 2);
  document.querySelector("#irOutput").textContent = JSON.stringify(ir, null, 2);
  document.querySelector("#planOutput").textContent = JSON.stringify(compiled, null, 2);
  const status = document.querySelector("#statusBadge");
  status.textContent = compiled.executable ? "Executable composition" : ir.status;
  status.className = `badge ${compiled.executable ? "valid" : ast.scope.found ? "invalid" : ""}`;
  document.querySelector("#qualityBadge").textContent = `Quality ${Math.round((ir.quality ?? 0) * 100)}%`;
  const stages = document.querySelector("#stageList");
  stages.replaceChildren(...(ir.stages.length ? ir.stages.map(stage => {
    const item = document.createElement("li");
    item.textContent = `${stage.operator} · ${Math.round(stage.confidence * 100)}%`;
    return item;
  }) : [Object.assign(document.createElement("li"), { textContent: "No stages recognized" })]));
  const diagnostics = [
    ...ir.warnings.map(code => ({ severity: "warning", code, message: code.replaceAll("_", " ") })),
    ...compiled.diagnostics,
  ];
  const list = document.querySelector("#diagnosticList");
  if (!diagnostics.length) {
    const item = document.createElement("li");
    item.textContent = "All parser and compiler gates pass.";
    item.className = "pass";
    list.replaceChildren(item);
  } else {
    list.replaceChildren(...diagnostics.map(diagnostic => {
      const item = document.createElement("li");
      item.className = diagnostic.severity ?? "warning";
      item.textContent = `${diagnostic.code}: ${diagnostic.message ?? ""}`;
      return item;
    }));
  }
}

function animate(timestamp) {
  flowContext.clearRect(0, 0, flowCanvas.width, flowCanvas.height);
  const symbols = ast?.symbols ?? [];
  if (ast?.scope?.found) {
    const pulse = .35 + Math.sin(timestamp / 350) * .12;
    flowContext.beginPath();
    flowContext.arc(ast.scope.center.x, ast.scope.center.y, ast.scope.radius, 0, Math.PI * 2);
    flowContext.strokeStyle = compiled?.executable ? `rgba(31,146,130,${pulse})` : `rgba(186,94,69,${pulse})`;
    flowContext.lineWidth = 7;
    flowContext.stroke();
  }
  if (symbols.length > 1) {
    const ordered = [...symbols].filter(symbol => symbol.kind === "operator").sort((a, b) => ((a.angleDeg + 90) % 360) - ((b.angleDeg + 90) % 360));
    for (let index = 0; index < ordered.length; index += 1) {
      const from = ordered[index].center, to = ordered[(index + 1) % ordered.length].center;
      const phase = ((timestamp / 1200) + index / ordered.length) % 1;
      const x = from.x + (to.x - from.x) * phase;
      const y = from.y + (to.y - from.y) * phase;
      flowContext.beginPath();
      flowContext.arc(x, y, 5, 0, Math.PI * 2);
      flowContext.fillStyle = "rgba(241,183,75,.75)";
      flowContext.fill();
    }
  }
  requestAnimationFrame(animate);
}

function downloadJson(name, value) {
  const blob = new Blob([JSON.stringify(value, null, 2) + "\n"], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 0);
}

drawCanvas.addEventListener("pointerdown", event => {
  if (pointerId !== null) return;
  pointerId = event.pointerId;
  drawCanvas.setPointerCapture(pointerId);
  currentStroke = [canvasPoint(event)];
});
drawCanvas.addEventListener("pointermove", event => {
  if (event.pointerId !== pointerId || !currentStroke) return;
  currentStroke.push(canvasPoint(event));
  renderDrawing();
});
function finishStroke(event) {
  if (event.pointerId !== pointerId || !currentStroke) return;
  currentStroke.push(canvasPoint(event));
  if (currentStroke.length >= 2) strokes.push(currentStroke);
  currentStroke = null;
  pointerId = null;
  recompute();
}
drawCanvas.addEventListener("pointerup", finishStroke);
drawCanvas.addEventListener("pointercancel", finishStroke);

document.querySelector("#undoButton").addEventListener("click", () => { strokes.pop(); recompute(); });
document.querySelector("#clearButton").addEventListener("click", () => { strokes = []; recompute(); });
document.querySelector("#sampleButton").addEventListener("click", () => { strokes = structuredClone(SAMPLE_STROKES); recompute(); });
document.querySelector("#exportDrawingButton").addEventListener("click", () => downloadJson("studio-composition.json", { schema_version: "1.0", strokes }));
document.querySelector("#exportPlanButton").addEventListener("click", () => downloadJson("studio-builder-plan.json", compiled));
document.querySelector("#importDrawingInput").addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    if (!Array.isArray(parsed.strokes)) throw new Error("Drawing JSON requires strokes");
    strokes = parsed.strokes;
    recompute();
  } catch (error) {
    alert(`Cannot import drawing: ${error.message}`);
  } finally {
    event.target.value = "";
  }
});
bindingsInput.addEventListener("input", recompute);

document.querySelectorAll("[data-tab]").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll("[data-tab]").forEach(item => item.classList.toggle("active", item === button));
  document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
  document.querySelector(`#${button.dataset.tab}Tab`).classList.add("active");
}));

recompute();
requestAnimationFrame(animate);
