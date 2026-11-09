// Tests the platform build-cache-by-name hypothesis: creates the SAME 01b
// flow under a DIFFERENT name and runs it.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";

function curl(method, path, bodyFile) {
  const args = ["-s", "--max-time", "90", "-X", method, `${BASE}${path}`, "-H", `Authorization: Bearer ${KEY}`];
  if (bodyFile) args.push("-H", "Content-Type: application/json", "--data-binary", `@${bodyFile}`);
  try {
    return execFileSync(CURL, args, { encoding: "utf8" });
  } catch (error) {
    return (error.stdout || "") + " ERR:" + (error.stderr || error.message).slice(0, 150);
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

const flow = JSON.parse(readFileSync("../flows/01b-security-gate-layer-1.json", "utf8"));
flow.name = "gate-l1-test-" + Date.now(); // UNIQUE name — defeats any name-keyed cache
writeFileSync("C:/Users/PC/AppData/Local/Temp/deploy-unique.json", JSON.stringify(flow));

const created = JSON.parse(curl("POST", "/api/v1/flows/", "C:/Users/PC/AppData/Local/Temp/deploy-unique.json"));
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
  session_id: "cachetest-" + Date.now(),
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-body2.json", body);

const runRaw = curl("POST", `/api/v1/run/${created.id}`, "C:/Users/PC/AppData/Local/Temp/run-body2.json");
const run = JSON.parse(runRaw);
const text = findText(run) || runRaw.slice(0, 400);

if (text.includes("raw_debug")) {
  const match = text.match(/"raw_debug":\s*("(?:[^"\\]|\\.)*")/);
  const raw = JSON.parse(match[1]);
  console.log("=== raw_debug EXACT ===");
  console.log(JSON.stringify(raw.slice(0, 200)));
  console.log([...raw.slice(0, 80)].map((c) => (c.charCodeAt(0) < 33 ? `<${c.charCodeAt(0)}>` : c)).join(""));
} else {
  console.log("RESULT:", text.slice(0, 800));
}
