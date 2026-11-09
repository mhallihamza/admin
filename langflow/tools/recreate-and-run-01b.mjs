// Deletes the old flow, creates a FRESH one from the current local build
// (the platform builds at creation time — PATCH does not refresh the build),
// then runs it and prints the result incl. raw_debug if present.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const OLD_ID = process.argv[2] || "3d7d331e-f398-414f-b424-c35469cfed5f";

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

console.log("delete old:", curl("DELETE", `/api/v1/flows/${OLD_ID}`).slice(0, 40));

const flow = JSON.parse(readFileSync("../flows/01b-security-gate-layer-1.json", "utf8"));
flow.name = `${flow.name} r${Date.now()}`; // unique name
writeFileSync("C:/Users/PC/AppData/Local/Temp/create01b.json", JSON.stringify(flow));

const created = JSON.parse(curl("POST", "/api/v1/flows/", "C:/Users/PC/AppData/Local/Temp/create01b.json"));
console.log("created:", created.id, "|", created.name);

const body = JSON.stringify({
  output_type: "chat",
  input_type: "chat",
  input_value: JSON.stringify({
    text: "Comment renouveler ma carte ?",
    request_type: "chat",
    user_id: "u-1",
    roles: ["VISITOR"],
    disabled: false,
    filename: null,
    source_user_id: null,
    agent: null,
    tool: null,
    agent_tool_allowed: false,
  }),
  session_id: "recreate-" + Date.now(),
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-body.json", body);

const runRaw = curl("POST", `/api/v1/run/${created.id}`, "C:/Users/PC/AppData/Local/Temp/run-body.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-last.json", runRaw);
const run = JSON.parse(runRaw);
const text = findText(run) || runRaw.slice(0, 400);

const match = text.match(/"raw_debug":\s*("(?:[^"\\]|\\.)*")/);
if (match) {
  const raw = JSON.parse(match[1]);
  console.log("=== raw_debug EXACT (what merge received) ===");
  console.log(JSON.stringify(raw.slice(0, 250)));
} else {
  console.log("RESULT:", text.slice(0, 900));
}

// persist the new id for future steps
const ids = JSON.parse(readFileSync("C:/Users/PC/AppData/Local/Temp/ids.json", "utf8"));
ids.id01b = created.id;
writeFileSync("C:/Users/PC/AppData/Local/Temp/ids.json", JSON.stringify(ids));
