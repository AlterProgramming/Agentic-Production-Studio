import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

function parseArguments(argv) {
  const values = new Map();
  for (let index = 2; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) throw new Error("Arguments must use --name value pairs.");
    values.set(key.slice(2), value);
  }
  for (const required of ["request", "token-file", "out"]) if (!values.has(required)) throw new Error(`--${required} is required.`);
  return values;
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function safeArtifactPath(value) {
  if (typeof value !== "string") throw new Error("Invalid artifact path.");
  const normalized = value.replaceAll("\\", "/").replace(/^\/+/, "");
  if (!normalized || normalized.includes("..") || path.isAbsolute(normalized)) throw new Error("Unsafe artifact path.");
  return normalized;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let body;
  try { body = JSON.parse(text); } catch { body = null; }
  if (!response.ok) throw new Error(`${response.status} ${body?.code || body?.title || text.slice(0, 200)}`);
  return body;
}

export async function invokeModelFirst({ requestPath, tokenPath, outputDirectory, baseUrl = "https://api.brightengine.live" }) {
  const requestBytes = await readFile(path.resolve(requestPath));
  const request = JSON.parse(requestBytes.toString("utf8"));
  if (!request || typeof request !== "object" || Array.isArray(request) || typeof request.prompt !== "string" || !request.prompt.trim()) throw new Error("Request must be a JSON object with a non-empty prompt.");
  const token = (await readFile(path.resolve(tokenPath), "utf8")).trim();
  if (!token.startsWith("forgecap1.")) throw new Error("Token file does not contain a Forge capability.");
  const descriptor = await fetchJson(`${baseUrl}/v1/capabilities/model-first`);
  if (descriptor.capability_id !== "visual-generation.model-first.v1" || descriptor.execution !== "first_party_local" || descriptor.external_providers !== false) {
    throw new Error("The discovered endpoint is not the required provider-free model-first runtime.");
  }
  const idempotencyKey = `model-first-${randomUUID()}`;
  const execution = await fetchJson(`${baseUrl}/v1/capabilities/model-first/execute`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: requestBytes,
  });
  if (execution.status !== "completed" || execution.persistent_scene_written_before_render !== true || execution.reopened !== true || execution.validation !== "pass") {
    throw new Error("The runtime did not return a valid model-first completion receipt.");
  }
  const outputRoot = path.resolve(outputDirectory);
  await mkdir(outputRoot, { recursive: true });
  const downloaded = [];
  for (const artifactPath of execution.artifact_paths || []) {
    const relative = safeArtifactPath(artifactPath);
    const response = await fetch(`${baseUrl}/v1/capabilities/model-first/runs/${encodeURIComponent(execution.run_id)}/artifacts/${relative.split("/").map(encodeURIComponent).join("/")}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(`Artifact download failed: ${relative} (${response.status}).`);
    const bytes = Buffer.from(await response.arrayBuffer());
    const destination = path.join(outputRoot, ...relative.split("/"));
    await mkdir(path.dirname(destination), { recursive: true });
    await writeFile(destination, bytes);
    downloaded.push({ path: relative, bytes: bytes.length, sha256: sha256(bytes) });
  }
  const receipt = JSON.parse(await readFile(path.join(outputRoot, "receipt.json"), "utf8"));
  const sceneBytes = await readFile(path.join(outputRoot, "scene", "scene.glb"));
  if (sha256(sceneBytes) !== execution.scene_sha256 || receipt.scene_sha256 !== execution.scene_sha256 || receipt.persistent_scene_written_before_render !== true || receipt.reopened !== true) {
    throw new Error("Downloaded artifacts do not satisfy the model-first receipt.");
  }
  const sessionReceipt = {
    schema_version: "1.0",
    kind: "model-first-session-materialization-receipt",
    capability_id: execution.capability_id,
    run_id: execution.run_id,
    endpoint: baseUrl,
    request_sha256: sha256(requestBytes),
    scene_sha256: execution.scene_sha256,
    downloaded,
    external_providers: false,
    verified_at: new Date().toISOString(),
  };
  await writeFile(path.join(outputRoot, "session-receipt.json"), `${JSON.stringify(sessionReceipt, null, 2)}\n`);
  return sessionReceipt;
}

async function main() {
  const args = parseArguments(process.argv);
  const receipt = await invokeModelFirst({
    requestPath: args.get("request"),
    tokenPath: args.get("token-file"),
    outputDirectory: args.get("out"),
    baseUrl: args.get("base-url") || process.env.BRIGHTENGINE_MODEL_FIRST_BASE_URL || "https://api.brightengine.live",
  });
  process.stdout.write(`${JSON.stringify(receipt)}\n`);
}

if (import.meta.url === new URL(`file://${process.argv[1]}`).href) main().catch((error) => { console.error(error.message); process.exitCode = 1; });
