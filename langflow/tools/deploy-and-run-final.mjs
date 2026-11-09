// Sets the Mistral api_key on the security gate flow, then runs both tests.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const LF_KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const MISTRAL_KEY = "mstrl_rQvJVVDihRKJ5xAnSHqRrcXGXlrScVsl_0eDxUG";
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";

function curl(method, path, bodyFile) {
  const args = ["-s", "--max-time", "120", "-X", method, `${BASE}${path}`, "-H", `Authorization: Bearer ${LF_KEY}`];
  if (bodyFile) args.push("-H", "Content-Type: application/json", "--data-binary", `@${bodyFile}`);
  try {
    return execFileSync(CURL, args, { encoding: "utf8" });
  } catch (error) {
    return (error.stdout || "") + " ERR:" + (error.stderr || error.message).slice(0, 150);
  }
}

function findTexts(node, depth = 0, acc = []) {
  if (depth > 12 || typeof node !== "object" || node === null) return acc;
  if (typeof node.text === "string" && node.text.length > 3) acc.push(node.text);
  for (const value of Object.values(node)) findTexts(value, depth + 1, acc);
  return acc;
}

// 1) GET the flow
let FLOW_ID = "3ff56628-91a9-4e16-b43d-b3a80a70fae5";
let stored = JSON.parse(curl("GET", `/api/v1/flows/${FLOW_ID}`));
if (!stored.data) {
  console.log("flow not found, listing...");
  const list = JSON.parse(curl("GET", "/api/v1/flows/"));
  const mine = list.find((f) => f.name.includes("Central Security Gate"));
  if (!mine) { console.log("NO SECURITY GATE FLOW FOUND"); process.exit(1); }
  FLOW_ID = mine.id;
  stored = mine;
  console.log("found:", stored.name, FLOW_ID);
} else {
  console.log("found:", stored.name, FLOW_ID);
}

// 2) Set the Mistral api_key in the detector node
const det = stored.data.nodes.find((n) => (n.data.node.display_name || "").includes("Detector"));
if (det) {
  det.data.node.template.api_key.value = MISTRAL_KEY;
  det.data.node.template.model_name.value = "codestral-latest";
  console.log("api_key set OK | model: codestral-latest OK");
}

// 3) DELETE + CREATE (preserves all fields)
console.log("delete:", curl("DELETE", `/api/v1/flows/${FLOW_ID}`).slice(0, 50));
writeFileSync("C:/Users/PC/AppData/Local/Temp/recreate-sg.json", JSON.stringify(stored));
const created = JSON.parse(curl("POST", "/api/v1/flows/", "C:/Users/PC/AppData/Local/Temp/recreate-sg.json"));
console.log("created:", created.id, "|", created.name);

// 4) Run CITIZEN test
const citizenBody = JSON.stringify({
  output_type: "chat",
  input_type: "chat",
  input_value: JSON.stringify({
    text: "Comment renouveler ma carte ?",
    request_type: "chat",
    user_id: "u-1",
    roles: ["CITIZEN"],
    disabled: false,
    filename: null,
    source_user_id: null,
    agent: null,
    tool: null,
    agent_tool_allowed: true,
  }),
  session_id: "citizen-" + Date.now(),
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-c.json", citizenBody);
const cRun = curl("POST", `/api/v1/run/${created.id}`, "C:/Users/PC/AppData/Local/Temp/run-c.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-c-result.json", cRun);
console.log("\n===== CITIZEN =====");
const cTexts = findTexts(JSON.parse(cRun));
if (cTexts.length === 0) console.log("no output:", cRun.slice(0, 300));
for (const t of cTexts) console.log("  > " + t.slice(0, 600));

// 5) Run VISITOR test
const visitorBody = JSON.stringify({
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
  session_id: "visitor-" + Date.now(),
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-v.json", visitorBody);
const vRun = curl("POST", `/api/v1/run/${created.id}`, "C:/Users/PC/AppData/Local/Temp/run-v.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-v-result.json", vRun);
console.log("\n===== VISITOR =====");
const vTexts = findTexts(JSON.parse(vRun));
if (vTexts.length === 0) console.log("no output:", vRun.slice(0, 300));
for (const t of vTexts) console.log("  > " + t.slice(0, 600));

writeFileSync("C:/Users/PC/AppData/Local/Temp/sg-id.txt", created.id);
