// Deletes the old flow and creates a FRESH one via POST (preserves ALL fields
// including global_imports, unlike PATCH which strips them).
// Usage: node recreate-flow.mjs <old-flow-id>
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const OLD_ID = process.argv[2] || "0a1e09ad-150e-47d5-839d-e8f373048cbd";

function curl(method, path, bodyFile) {
  const args = ["-s", "--max-time", "90", "-X", method, `${BASE}${path}`, "-H", `Authorization: Bearer ${KEY}`];
  if (bodyFile) args.push("-H", "Content-Type: application/json", "--data-binary", `@${bodyFile}`);
  try {
    return execFileSync(CURL, args, { encoding: "utf8" });
  } catch (error) {
    return (error.stdout || "") + " ERR:" + (error.stderr || error.message).slice(0, 200);
  }
}

function findText(node, depth = 0) {
  if (depth > 10 || typeof node !== "object" || node === null) return null;
  if (typeof node.text === "string" && node.text.length > 5) return node.text;
  for (const value of Object.values(node)) {
    const found = findText(value, depth + 1);
    if (found) return found;
  }
  return null;
}

console.log("delete old:", curl("DELETE", `/api/v1/flows/${OLD_ID}`).slice(0, 50));

// POST creates with full data — all template fields preserved
const flow = JSON.parse(readFileSync("../flows/central-security-gate.json", "utf8"));
writeFileSync("C:/Users/PC/AppData/Local/Temp/create-flow.json", JSON.stringify(flow));
const created = JSON.parse(curl("POST", "/api/v1/flows/", "C:/Users/PC/AppData/Local/Temp/create-flow.json"));
console.log("created:", created.id, "|", created.name);

// verify global_imports survived
const check = JSON.parse(curl("GET", `/api/v1/flows/${created.id}`));
const interp = check.data.nodes.find((n) => n.data.type === "PythonREPLComponent" && (n.data.node.display_name || "").includes("Central Decision"));
console.log("stored global_imports:", JSON.stringify(interp?.data?.node?.template?.global_imports?.value));
console.log("stored api_key:", interp === undefined ? "?" : "(checking detector...)");
const det = check.data.nodes.find((n) => (n.data.node.display_name || "").includes("Detector"));
console.log("detector api_key:", det?.data?.node?.template?.api_key?.value ? "(present)" : "(EMPTY)");
console.log("detector model:", det?.data?.node?.template?.model_name?.value);

writeFileSync("C:/Users/PC/AppData/Local/Temp/new-flow-id.txt", created.id);
