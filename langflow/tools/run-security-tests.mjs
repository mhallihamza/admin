// Runs the security gate flow twice (CITIZEN → ALLOW, VISITOR → BLOCK+log)
// and prints every output text found in the responses.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const FLOW_ID = process.argv[2] || "0a1e09ad-150e-47d5-839d-e8f373048cbd";

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

function run(label, roles, agentToolAllowed) {
  const body = JSON.stringify({
    output_type: "chat",
    input_type: "chat",
    input_value: JSON.stringify({
      text: "Comment renouveler ma carte ?",
      request_type: "chat",
      user_id: "u-1",
      roles,
      disabled: false,
      filename: null,
      source_user_id: null,
      agent: null,
      tool: null,
      agent_tool_allowed: agentToolAllowed,
    }),
    session_id: label + "-" + Date.now(),
  });
  writeFileSync("C:/Users/PC/AppData/Local/Temp/run-b.json", body);
  const runRaw = curl("POST", `/api/v1/run/${FLOW_ID}`, "C:/Users/PC/AppData/Local/Temp/run-b.json");
  writeFileSync(`C:/Users/PC/AppData/Local/Temp/run-${label}.json`, runRaw);
  console.log(`\n===== ${label} =====`);
  let texts = [];
  try {
    texts = findTexts(JSON.parse(runRaw));
  } catch {
    console.log("non-JSON response:", runRaw.slice(0, 400));
    return;
  }
  if (texts.length === 0) console.log("no output text — response:", runRaw.slice(0, 400));
  for (const t of texts) console.log("  > " + t.slice(0, 600));
}

run("citizen", ["CITIZEN"], true);
run("visitor", ["VISITOR"], false);
