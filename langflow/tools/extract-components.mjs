// Extracts real component templates from the reference flow exports so the
// generated flows use byte-faithful Langflow 1.7 node structures.
// Run: node extract-components.mjs  →  writes component-library.json
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const downloads = "C:/Users/PC/Downloads";

const sources = {
  graphrag: join(downloads, "ClinicFaqGraphRAGv3 (2).json"),
  ragagent: join(downloads, "ClinicFaqRagAgent (6).json"),
  booking: join(downloads, "ClinicBookingAgent(4).json"),
  supervisor: join(downloads, "Supervisor (observability)(7).json"),
};

const wanted = {
  graphrag: [
    "File",
    "AstraDB",
    "ChatInput",
    "Prompt Template",
    "MistralModel",
    "ChatOutput",
    "TypeConverterComponent",
    "PythonREPLComponent",
    "MistalAIEmbeddings",
  ],
  ragagent: ["SplitText"],
  booking: ["Agent"],
  supervisor: ["Webhook", "TextOutput", "RunFlow", "ConditionalRouter"],
};

const library = {};

for (const [sourceName, path] of Object.entries(sources)) {
  const flow = JSON.parse(readFileSync(path, "utf8"));
  for (const node of flow.data.nodes) {
    const type = node.data.type;
    if (!wanted[sourceName]?.includes(type)) continue;
    if (library[type]) continue; // first occurrence wins
    library[type] = node.data.node;
  }
}

const out = join(here, "component-library.json");
writeFileSync(out, JSON.stringify(library, null, 2));

for (const [type, node] of Object.entries(library)) {
  const outputs = (node.outputs || []).map((o) => o.name).join(", ");
  const fields = Object.keys(node.template || {})
    .filter((f) => f !== "code")
    .slice(0, 30)
    .join(", ");
  console.log(`${type}: outputs=[${outputs}] fields=[${fields}]`);
}
console.log(`\nWrote ${Object.keys(library).length} component templates to ${out}`);
