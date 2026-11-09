// Deploys the current 01b build into the flow id provided by the user,
// runs it, and prints the raw_debug field (exact characters) the merge
// step received — ground truth for the parser fix.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const FLOW_ID = process.argv[2] || "44a2ce80-e53a-4c39-990e-e6ec1d0b5694";

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

// 1) GET the existing flow (see what is stored now)
const remoteRaw = curl("GET", `/api/v1/flows/${FLOW_ID}`);
try {
  const remote = JSON.parse(remoteRaw);
  console.log("existing flow:", remote.name, "| nodes:", remote.data?.nodes?.length);
} catch {
  console.log("GET failed:", remoteRaw.slice(0, 200));
}

// 2) PATCH it with the current local build (keep the same id). The platform
// enforces unique flow names — always PATCH with a fresh unique name.
const flow = JSON.parse(readFileSync("../flows/01b-security-gate-layer-1.json", "utf8"));
flow.id = FLOW_ID;
const uniqueName = `${flow.name} v${Date.now()}`;
writeFileSync("C:/Users/PC/AppData/Local/Temp/deploy01b.json", JSON.stringify({ name: uniqueName, description: flow.description, data: flow.data }));
console.log("patch:", curl("PATCH", `/api/v1/flows/${FLOW_ID}`, "C:/Users/PC/AppData/Local/Temp/deploy01b.json").slice(0, 60));

// 3) RUN with the VISITOR payload
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
  session_id: "dbg-" + Date.now(),
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-body.json", body);
const runRaw = curl("POST", `/api/v1/run/${FLOW_ID}`, "C:/Users/PC/AppData/Local/Temp/run-body.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-last.json", runRaw);

const run = JSON.parse(runRaw);
const text = findText(run) || runRaw.slice(0, 400);

// 4) read raw_debug cleanly
const match = text.match(/"raw_debug":\s*("(?:[^"\\]|\\.)*")/);
if (match) {
  const raw = JSON.parse(match[1]);
  console.log("=== raw_debug EXACT ===");
  console.log(JSON.stringify(raw.slice(0, 200)));
  console.log([...raw.slice(0, 80)].map((c) => (c.charCodeAt(0) < 33 ? `<${c.charCodeAt(0)}>` : c)).join(""));
} else {
  console.log("RESULT:", text.slice(0, 800));
}
