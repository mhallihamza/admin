// Decisive test: does the router's true_case_message deliver to Gate Result?
// Forces a test string into Route 1's true_case_message via runtime tweaks.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const FLOW_ID = "0a1e09ad-150e-47d5-839d-e8f373048cbd";

function curl(method, path, bodyFile) {
  const args = ["-s", "--max-time", "120", "-X", method, `${BASE}${path}`, "-H", `Authorization: Bearer ${KEY}`];
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

// stored id of router 1
const stored = JSON.parse(curl("GET", `/api/v1/flows/${FLOW_ID}`));
const r1 = stored.data.nodes.find((n) => (n.data.node.display_name || "").includes("Route 1"));
console.log("router 1 id:", r1.id);

const body = JSON.stringify({
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
  session_id: "casetest-" + Date.now(),
  tweaks: {
    [r1.id]: { true_case_message: "CASE-DELIVERY-TEST-12345" },
  },
});
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-case.json", body);

const runRaw = curl("POST", `/api/v1/run/${FLOW_ID}`, "C:/Users/PC/AppData/Local/Temp/run-case.json");
writeFileSync("C:/Users/PC/AppData/Local/Temp/run-case-result.json", runRaw);
const texts = findTexts(JSON.parse(runRaw));
console.log("=== outputs with tweaks ===");
if (texts.length === 0) console.log("none — response:", runRaw.slice(0, 300));
for (const t of texts) console.log("  > " + t.slice(0, 400));
console.log(texts.some((t) => t.includes("CASE-DELIVERY-TEST")) ? "DELIVERY WORKS ✓" : "DELIVERY BROKEN ✗");
