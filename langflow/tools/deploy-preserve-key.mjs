// Deploys the current security-gate build while PRESERVING secrets the user
// entered in the UI (Mistral api_key on the detector node).
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const BASE = "https://stg-agentic.abafusion.ai";
const KEY = readFileSync("C:/Users/PC/AppData/Local/Temp/lflow-key.txt", "utf8").trim();
const CURL = "C:/Program Files/Git/mingw64/bin/curl.exe";
const FLOW_ID = process.argv[2] || "0a1e09ad-150e-47d5-839d-e8f373048cbd";

function curl(method, path, bodyFile) {
  const args = ["-s", "--max-time", "90", "-X", method, `${BASE}${path}`, "-H", `Authorization: Bearer ${KEY}`];
  if (bodyFile) args.push("-H", "Content-Type: application/json", "--data-binary", `@${bodyFile}`);
  try {
    return execFileSync(CURL, args, { encoding: "utf8" });
  } catch (error) {
    return (error.stdout || "") + " ERR:" + (error.stderr || error.message).slice(0, 150);
  }
}

// 1) read the remote flow and preserve the detector's api_key
const remoteRaw = curl("GET", `/api/v1/flows/${FLOW_ID}`);
const remote = JSON.parse(remoteRaw);
const remoteDetector = remote.data.nodes.find(
  (n) => (n.data.node.display_name || "").includes("Layer 2 Detector")
);
const preservedKey = remoteDetector?.data?.node?.template?.api_key?.value || "";
console.log("preserved Mistral key:", preservedKey ? "(present, " + preservedKey.length + " chars)" : "(EMPTY — user must enter it)");

// 2) build the local payload, inject the preserved key
const flow = JSON.parse(readFileSync("../flows/central-security-gate.json", "utf8"));
flow.id = FLOW_ID;
if (preservedKey) {
  const localDetector = flow.data.nodes.find(
    (n) => (n.data.node.display_name || "").includes("Layer 2 Detector")
  );
  localDetector.data.node.template.api_key.value = preservedKey;
}
const uniqueName = flow.name + " v" + Date.now();
writeFileSync("C:/Users/PC/AppData/Local/Temp/deploy01.json", JSON.stringify({ name: uniqueName, description: flow.description, data: flow.data }));

// 3) patch
console.log("patch:", curl("PATCH", `/api/v1/flows/${FLOW_ID}`, "C:/Users/PC/AppData/Local/Temp/deploy01.json").slice(0, 50));

// 4) verify stored
const check = JSON.parse(curl("GET", `/api/v1/flows/${FLOW_ID}`));
const checkDetector = check.data.nodes.find((n) => (n.data.node.display_name || "").includes("Layer 2 Detector"));
console.log("stored api_key now:", checkDetector.data.node.template.api_key.value ? "(present)" : "(EMPTY)");
