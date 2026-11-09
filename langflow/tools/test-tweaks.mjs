// Proves the stale-build theory: runs the SAME stored flow but overrides the
// merge wrapper's template at RUNTIME via tweaks. If the output changes to
// include raw_debug / ROLE_VS_REQUEST, the platform build cache is stale.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const FLOW_ID = process.argv[2] || "d2ca955f-bcb4-4c8d-bf1a-5dc1e53175b3";

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

// current local template for the merge wrapper
const local = JSON.parse(readFileSync("../flows/01b-security-gate-layer-1.json", "utf8"));
const localWrapper = local.data.nodes.find(
  (n) => (n.data.node.display_name || "").includes("Gate Merge")
);
const currentTemplate = localWrapper.data.node.template.template.value;

// stored node id of the merge wrapper on the platform
const stored = JSON.parse(curl("GET", `/api/v1/flows/${FLOW_ID}`));
const storedWrapper = stored.data.nodes.find(
  (n) => (n.data.node.display_name || "").includes("Gate Merge")
);
console.log("stored merge wrapper id:", storedWrapper.id);

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
  session_id: "tweaks-" + Date.now(),
  tweaks: {
    [storedWrapper.id]: { template: currentTemplate },
  },
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-tweaks.json", body);

const runRaw = curl("POST", `/api/v1/run/${FLOW_ID}`, "C:/Users/PC/AppData/Local/Temp/run-tweaks.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-tweaks-result.json", runRaw);
const run = JSON.parse(runRaw);
const text = findText(run) || runRaw.slice(0, 400);

if (text.includes("raw_debug")) {
  const match = text.match(/"raw_debug":\s*("(?:[^"\\]|\\.)*")/);
  const raw = JSON.parse(match[1]);
  console.log("=== TWEAKS WORKED — raw_debug EXACT ===");
  console.log(JSON.stringify(raw.slice(0, 250)));
} else {
  console.log("RESULT:", text.slice(0, 900));
}
