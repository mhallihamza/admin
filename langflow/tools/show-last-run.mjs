// Prints the FULL text of the last run result + the exact raw_debug value.
import { readFileSync } from "node:fs";

const run = JSON.parse(readFileSync("C:/Users/PC/AppData/Local/Temp/run-last.json", "utf8"));

function findText(node, depth = 0) {
  if (depth > 10 || typeof node !== "object" || node === null) return null;
  if (typeof node.text === "string" && node.text.length > 5) return node.text;
  for (const value of Object.values(node)) {
    const found = findText(value, depth + 1);
    if (found) return found;
  }
  return null;
}

const text = findText(run) || "";
console.log("=== FULL message text ===");
console.log(text);
console.log("=== END ===");
