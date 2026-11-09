// Prints EVERY text in the last run response WITH its source component.
import { readFileSync } from "node:fs";

const run = JSON.parse(readFileSync("C:/Users/PC/AppData/Local/Temp/run-c2.json", "utf8"));

function walk(node, path, depth = 0) {
  if (depth > 14 || typeof node !== "object" || node === null) return;
  if (Array.isArray(node)) {
    for (const item of node) walk(item, path, depth + 1);
    return;
  }
  if (typeof node.text === "string" && node.text.length > 3) {
    const src = node.properties?.source?.display_name || node.sender_name || "?";
    console.log(`[${src}] ${node.text.slice(0, 400)}`);
  }
  for (const [k, v] of Object.entries(node)) walk(v, path + "." + k, depth + 1);
}

walk(run, "root");
