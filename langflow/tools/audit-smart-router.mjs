// Inspects the SmartRouter component from the reference export: module, fields,
// outputs, and the ACTUAL routing code (ground truth for behavior).
import { readFileSync, writeFileSync } from "node:fs";

const ref = JSON.parse(readFileSync("C:/Users/PC/Downloads/Supervisor (observability)(7).json", "utf8"));
const node = ref.data.nodes.find((n) => n.data.type === "SmartRouter");
if (!node) {
  console.log("SmartRouter NOT in reference; listing available types:");
  console.log([...new Set(ref.data.nodes.map((n) => n.data.type))].join(", "));
  process.exit(0);
}

const n = node.data.node;
console.log("display:", n.display_name);
console.log("module:", n.metadata?.module);
console.log("key:", n.key);
console.log("=== fields (non-code) ===");
for (const [k, v] of Object.entries(n.template)) {
  if (k === "code") continue;
  if (k.startsWith("_")) continue;
  console.log("-", k, "|", v._input_type || v.type, "| value:", JSON.stringify(v.value)?.slice(0, 100), v.options ? "options:" + JSON.stringify(v.options).slice(0, 120) : "");
}
console.log("=== outputs ===");
console.log(JSON.stringify(n.outputs.map((o) => ({ name: o.name, types: o.types, tool_mode: o.tool_mode }))));
console.log("=== code (routing logic, first 3000 chars) ===");
console.log((n.template.code?.value || "").slice(0, 3000));

// save the full template for the generator library
const lib = JSON.parse(readFileSync("component-library.json", "utf8"));
lib.SmartRouter = n;
writeFileSync("component-library.json", JSON.stringify(lib, null, 2));
console.log("\nSmartRouter saved to component-library.json");
