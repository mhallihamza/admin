// Tests the component-id-keyed code-cache hypothesis: renames EVERY node id
// in the 01b flow (nodes + handles + edges) to brand-new unique ids, creates
// the flow, and runs it. If the output changes, the platform caches compiled
// code per component id.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";

function curl(method, path, bodyFile) {
  const args = ["-s", "--max-time", "120", "-X", method, `${BASE}${path}`, "-H", `Authorization: Bearer ${KEY}`];
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

const salt = "z" + Math.floor(Math.random() * 1e9);
let flow = readFileSync("../flows/01b-security-gate-layer-1.json", "utf8");

// collect every node id and replace it globally (nodes, handles, edge ids)
const parsed = JSON.parse(flow);
for (const node of parsed.data.nodes) {
  const oldId = node.id;
  const newId = oldId + salt;
  flow = flow.split(`"${oldId}"`).join(`"${newId}"`); // quoted occurrences
  flow = flow.split(oldId).join(newId); // handle strings + edge ids
}
writeFileSync("C:/Users/PC/AppData/Local/Temp/deploy-unique-ids.json", flow);

flow = JSON.parse(flow);
flow.name = "gate-l1-unique-ids-" + salt;
writeFileSync("C:/Users/PC/AppData/Local/Temp/deploy-unique-ids.json", JSON.stringify(flow));

const created = JSON.parse(curl("POST", "/api/v1/flows/", "C:/Users/PC/AppData/Local/Temp/deploy-unique-ids.json"));
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
  session_id: "uniqids-" + Date.now(),
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-body3.json", body);

const runRaw = curl("POST", `/api/v1/run/${created.id}`, "C:/Users/PC/AppData/Local/Temp/run-body3.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-uniq.json", runRaw);
const run = JSON.parse(runRaw);
const text = findText(run) || runRaw.slice(0, 400);

if (text.includes("raw_debug")) {
  const match = text.match(/"raw_debug":\s*("(?:[^"\\]|\\.)*")/);
  const raw = JSON.parse(match[1]);
  console.log("=== UNIQUE IDS WORKED — raw_debug EXACT ===");
  console.log(JSON.stringify(raw.slice(0, 250)));
} else {
  console.log("RESULT:", text.slice(0, 500));
}
