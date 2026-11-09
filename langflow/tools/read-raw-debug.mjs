// Reads the last 01b run and extracts the raw_debug field cleanly.
import { readFileSync } from "node:fs";

const run = JSON.parse(readFileSync("C:/Users/PC/AppData/Local/Temp/run-rawdbg2.json", "utf8"));

function findText(node, depth = 0) {
  if (depth > 10 || typeof node !== "object" || node === null) return null;
  if (typeof node.text === "string" && node.text.length > 5) return node.text;
  for (const value of Object.values(node)) {
    const found = findText(value, depth + 1);
    if (found) return found;
  }
  return null;
}

const text = findText(run) || JSON.stringify(run).slice(0, 500);

// the output text is str({'result': '<json>'}) — a Python dict repr
let parsed = null;
try {
  parsed = (0, eval)(`(${text})`); // python repr of str/dict usually evals in JS for simple cases
} catch {
  parsed = null;
}

let rawDebug = null;
const match = text.match(/"raw_debug":\s*("(?:[^"\\]|\\.)*")/);
if (match) {
  rawDebug = JSON.parse(match[1]);
} else {
  const m2 = text.match(/raw_debug.: ?(.{0,400})/);
  rawDebug = m2 ? m2[1] : null;
}

console.log("=== raw_debug (exact) ===");
if (rawDebug) {
  console.log(JSON.stringify(rawDebug.slice(0, 160)));
  console.log([...rawDebug.slice(0, 60)].map((c) => (c.charCodeAt(0) < 33 ? `<${c.charCodeAt(0)}>` : c)).join(""));
} else {
  console.log("not found; text:", text.slice(0, 600));
}
