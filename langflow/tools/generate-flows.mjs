// Generates the importable Langflow 1.7 flow files from the component library
// (cloned from real reference exports) and the fixed code templates in ../code.
//
// Guarantees enforced here:
//   * every {variable} in a Prompt Template has its OWN input field created,
//     and the flow definitions wire every variable explicitly — no dangling
//     placeholder, no unused "second connection";
//   * all values inherited from the reference exports (clinic prompts, system
//     messages, leftovers) are scrubbed;
//   * no template text contains unresolved @@ markers.
//
// Run: node generate-flows.mjs  →  writes ../flows/*.json
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

const here = dirname(fileURLToPath(import.meta.url));
const library = JSON.parse(readFileSync(join(here, "component-library.json"), "utf8"));
const codeDir = join(here, "..", "code");
const outDir = join(here, "..", "flows");

// ---------------------------------------------------------------------------
// Text helpers
// ---------------------------------------------------------------------------
function loadCode(name) {
  return readFileSync(join(codeDir, name), "utf8");
}

/**
 * Build a Prompt Template `template` value from a fixed code/prompt file:
 * escape Python braces for Langflow, then turn @@VAR:name@@ markers into
 * {name} placeholders. Returns the text and the ordered variable names.
 */
function toPromptValue(fileName, opts = {}) {
  let text = loadCode(fileName);
  text = text.replace(/\{/g, "{{").replace(/\}/g, "}}");
  text = text.replace(/@@QUOTE@@/g, "'''");
  const vars = [];
  text = text.replace(/@@VAR:([a-z_0-9]+)@@/g, (_match, name) => {
    vars.push(name);
    return `{${name}}`;
  });
  if (opts.tool) text = text.replace(/@@TOOL@@/g, opts.tool);
  if (opts.agent) text = text.replace(/@@AGENT@@/g, opts.agent);
  if (/@@/.test(text)) throw new Error(`Unresolved @@ marker in ${fileName}`);
  return { text, vars };
}

/** Plain (non-python) prompt file: same escaping, {question}/{context} kept. */
function toPlainPrompt(fileName) {
  let text = loadCode(fileName);
  text = text.replace(/\{/g, "{{").replace(/\}/g, "}}");
  return text
    .replace(/\{\{question\}\}/g, "{question}")
    .replace(/\{\{context\}\}/g, "{context}");
}

// ---------------------------------------------------------------------------
// Node factory (clones the real reference template, then scrubs it)
// ---------------------------------------------------------------------------
let counter = 0;

const SCRUB_DEFAULTS = {
  "Prompt Template": ["context", "question", "tool_placeholder", "template"],
  MistralModel: ["system_message", "input_value"],
  Agent: ["system_prompt", "input_value", "agent_description"],
};

/** Remove any inherited reference text (e.g. clinic file paths) from a value. */
function scrubInherited(value) {
  if (typeof value === "string") return /clinic/i.test(value) ? "" : value;
  if (Array.isArray(value)) return value.map(scrubInherited).filter((v) => v !== "");
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, item] of Object.entries(value)) out[key] = scrubInherited(item);
    return out;
  }
  return value;
}

function node(type, displayName, position, fieldOverrides = {}, opts = {}) {
  if (!library[type]) throw new Error(`Component ${type} missing from library`);
  const nodeTemplate = JSON.parse(JSON.stringify(library[type]));

  // Scrub session artifacts and inherited reference values — deep, across
  // every string inside the field (value, file_path, options, info, ...).
  for (const key of Object.keys(nodeTemplate.template)) {
    if (key.startsWith("_")) continue; // metadata keys (_type, is_refresh, ...)
    nodeTemplate.template[key] = scrubInherited(nodeTemplate.template[key]);
  }
  for (const field of SCRUB_DEFAULTS[type] || []) {
    if (nodeTemplate.template[field]) nodeTemplate.template[field].value = "";
  }

  const id = `${type.replace(/\s+/g, "")}-${opts.suffix || ++counter}`;
  for (const [field, value] of Object.entries(fieldOverrides)) {
    if (!nodeTemplate.template[field]) {
      throw new Error(`Unknown field ${field} on ${type} (node ${displayName})`);
    }
    nodeTemplate.template[field].value = value;
  }
  // Prompt Template: drop any optional input field the template text does not
  // use, so no dangling handle (context/question/tool_placeholder) survives.
  if (type === "Prompt Template") {
    const text = nodeTemplate.template.template?.value || "";
    const used = new Set([...text.matchAll(/(?<!\{)\{([a-z_0-9]+)\}(?!\})/g)].map((m) => m[1]));
    for (const f of ["context", "question", "tool_placeholder"]) {
      if (!used.has(f)) delete nodeTemplate.template[f];
    }
  }
  if (displayName) nodeTemplate.display_name = displayName;
  const outputs = nodeTemplate.outputs || [];
  return {
    id,
    type,
    displayName,
    position,
    nodeTemplate,
    primaryOutput: opts.primaryOutput || outputs[0]?.name || null,
  };
}

/** Ensure an input field exists for a {variable} of a Prompt Template. */
function ensureVarField(promptNode, varName) {
  const template = promptNode.nodeTemplate.template;
  if (template[varName]) return;
  const modelSource = template.context || template.question || {
    _input_type: "MultilineInput",
    advanced: false,
    display_name: varName,
    dynamic: false,
    info: "",
    input_types: ["Message"],
    list: false,
    list_add_label: "Add More",
    load_from_db: false,
    multiline: true,
    name: varName,
    override_skip: false,
    placeholder: "",
    required: false,
    show: true,
    title_case: false,
    tool_mode: false,
    trace_as_metadata: true,
    track_in_telemetry: false,
    type: "str",
    value: "",
  };
  const model = JSON.parse(JSON.stringify(modelSource));
  model.name = varName;
  model.display_name = varName.charAt(0).toUpperCase() + varName.slice(1).replace(/_/g, " ");
  model.value = "";
  template[varName] = model;
}

function serializeNode(node) {
  return {
    data: {
      id: node.id,
      node: node.nodeTemplate,
      selected_output: node.primaryOutput,
      showNode: true,
      type: node.type,
    },
    dragging: false,
    id: node.id,
    measured: { height: 300, width: 320 },
    position: { x: node.position.x, y: node.position.y },
    selected: false,
    type: "genericNode",
  };
}

// ---------------------------------------------------------------------------
// Edge factory (œ-encoded handles, same convention as reference exports)
// ---------------------------------------------------------------------------
function outputMeta(node, outputName) {
  const output = node.nodeTemplate.outputs.find((o) => o.name === outputName);
  if (!output) throw new Error(`Node ${node.id} has no output ${outputName}`);
  const types = output.types || (output.selected ? [output.selected] : ["Data"]);
  return { dataType: node.type, id: node.id, name: outputName, output_types: types };
}

function inputMeta(node, fieldName) {
  const field = node.nodeTemplate.template[fieldName];
  if (!field) throw new Error(`Node ${node.id} has no input ${fieldName}`);
  return { fieldName, id: node.id, inputTypes: field.input_types || [], type: field.type || "str" };
}

function edge(source, sourceOutput, target, targetField, opts = {}) {
  let sh = outputMeta(source, sourceOutput);
  if (opts.asTool) {
    // Components exposed as agent tools connect through the component_as_tool
    // handle (same convention as the reference exports).
    sh = { ...sh, name: "component_as_tool", output_types: ["Tool"] };
  }
  const th = inputMeta(target, targetField);
  const encode = (obj) => JSON.stringify(obj).replace(/"/g, "\u0153");
  return {
    animated: false,
    className: "",
    data: { sourceHandle: sh, targetHandle: th },
    id: `xy-edge__${encode(sh)}-${encode(th)}`,
    selected: false,
    source: source.id,
    sourceHandle: encode(sh),
    target: target.id,
    targetHandle: encode(th),
  };
}

/** TypeConverter variant that emits a DataFrame output. */
function asDataFrameConverter(converter) {
  const outputs = converter.nodeTemplate.outputs;
  if (!outputs.some((o) => o.name === "dataframe_output")) {
    const message = outputs.find((o) => o.name === "message_output");
    outputs.push({
      ...JSON.parse(JSON.stringify(message)),
      name: "dataframe_output",
      display_name: "DataFrame",
      types: ["DataFrame"],
      selected: "DataFrame",
    });
  }
  converter.nodeTemplate.template.output_type.value = "DataFrame";
  return converter;
}

function buildFlow(name, description, nodes, edges) {
  return {
    data: { edges, nodes: nodes.map(serializeNode), viewport: { x: 60, y: 40, zoom: 0.85 } },
    description,
    endpoint_name: null,
    id: randomUUID(),
    is_component: false,
    last_tested_version: "1.7.0",
    name,
    tags: [],
  };
}

/**
 * Prompt(fixed code wrapper) + Python Interpreter pair.
 * vars: map of {variableName: [sourceNode, sourceOutput]} — every variable
 * declared in the code file gets exactly ONE explicit connection, and every
 * UNUSED library input (context/question/tool_placeholder) is DELETED so no
 * dangling handle ever appears on the canvas.
 */
function replStep(suffix, displayName, codeFile, imports, x, y, opts = {}) {
  const { text, vars } = toPromptValue(codeFile, opts);
  const wrapper = node("Prompt Template", `${displayName} — fixed code`, { x, y }, { template: text }, { suffix: `${suffix}p` });
  for (const varName of vars) ensureVarField(wrapper, varName);
  for (const unused of ["context", "question", "tool_placeholder"]) {
    if (!vars.includes(unused)) delete wrapper.nodeTemplate.template[unused];
  }

  const interpreter = node(
    "PythonREPLComponent",
    displayName,
    { x: x + 360, y },
    { python_code: "print('code provided by the upstream Prompt Template (fixed)')", global_imports: imports },
    { suffix: `${suffix}r` }
  );

  const connections = Object.entries(opts.vars || {}).map(([varName, [source, sourceOutput]]) => {
    if (!vars.includes(varName)) throw new Error(`${displayName}: edge for unknown variable ${varName}`);
    return edge(source, sourceOutput, wrapper, varName);
  });
  for (const varName of vars) {
    if (!opts.vars || !opts.vars[varName]) {
      throw new Error(`${displayName}: template variable {${varName}} has no connection`);
    }
  }

  return { wrapper, interpreter, internal: edge(wrapper, "prompt", interpreter, "python_code"), connections };
}

function col(x) {
  return x * 360;
}

// ---------------------------------------------------------------------------
// Flow 1 — Central Security Gate (full: Layer 1 + Layer 2 detection model)
// Layer 2 is a PLAIN model node — deliberately NOT an Agent component — so it
// is structurally incapable of calling tools. Its instructions live in the
// model's own system_message; the question connects directly. No prompt node.
// ---------------------------------------------------------------------------
function flowSecurityGate() {
  const chat = node("ChatInput", "Request Payload (JSON)", { x: col(0), y: 0 },
    { input_value: '{"text": "Comment renouveler ma carte ?", "request_type": "chat", "user_id": "u-1", "roles": ["CITIZEN"], "disabled": false, "filename": null, "source_user_id": null, "agent": null, "tool": null, "agent_tool_allowed": true}' },
    { suffix: "s0" });
  const toMsg = node("TypeConverterComponent", "Payload to Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "s1" });
  const layer1 = replStep("s2", "Layer 1 Rules", "layer1_rules.template.py", "json,re,ast", col(2), 0,
    { vars: { context: [toMsg, "message_output"] } });
  const extract = replStep("s3", "Extract Text For Detection", "extract_text_for_detection.template.py", "json,re,ast", col(2), 300,
    { vars: { context: [toMsg, "message_output"] } });
  const toMsgL2 = node("TypeConverterComponent", "Text to Message", { x: col(4), y: 300 }, { output_type: "Message" }, { suffix: "s4c" });
  const detector = node("MistralModel", "Layer 2 Detector (plain model)", { x: col(5), y: 300 },
    { model_name: "codestral-latest", temperature: 0, input_value: "", api_key: "", timeout: 30, system_message: loadCode("layer2_detector_system_message.txt") }, { suffix: "s4" });
  const toMsg2 = node("TypeConverterComponent", "Layer1 to Message", { x: col(3), y: 120 }, { output_type: "Message" }, { suffix: "s7" });
  const merge = replStep("s5", "Central Decision (fixed code)", "gate_merge.template.py", "json,re,ast", col(6), 0,
    { vars: { layer1_json: [toMsg2, "message_output"], layer2_text: [detector, "text_output"], session_json: [toMsg, "message_output"] } });
  const toMsgDec = node("TypeConverterComponent", "Decision to Message", { x: col(8), y: 120 }, { output_type: "Message" }, { suffix: "s9" });

  // Deterministic conditional-router chain — no LLM in routing
  const routerAllow = node("ConditionalRouter", "Route ALLOW", { x: col(9), y: 0 },
    { operator: "contains", match_text: '"decision": "ALLOW"', case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r1" });
  const routerReview = node("ConditionalRouter", "Route REVIEW", { x: col(10), y: 280 },
    { operator: "contains", match_text: '"decision": "REVIEW"', case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r2" });
  const routerRestrict = node("ConditionalRouter", "Route RESTRICT", { x: col(11), y: 280 },
    { operator: "contains", match_text: '"decision": "RESTRICT"', case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r3" });

  // ALLOW route — carries the full payload for the next workflow
  const gateOut = node("ChatOutput", "Gate Result (payload for next workflow)", { x: col(12), y: 0 }, {}, { suffix: "g1" });

  // REVIEW route — log and hold
  const revLog = replStep("v1", "Log Review Hold", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(12), 280,
    { vars: { context: [routerReview, "true_result"] } });
  const revTc = node("TypeConverterComponent", "Review to Message", { x: col(14), y: 280 }, { output_type: "Message" }, { suffix: "v2" });
  const revOut = node("ChatOutput", "Review Hold", { x: col(15), y: 280 }, {}, { suffix: "v3" });

  // RESTRICT route — log and hold
  const resLog = replStep("x1", "Log Restricted", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(12), 560,
    { vars: { context: [routerRestrict, "true_result"] } });
  const resTc = node("TypeConverterComponent", "Restricted to Message", { x: col(14), y: 560 }, { output_type: "Message" }, { suffix: "x2" });
  const resOut = node("ChatOutput", "Restricted (held)", { x: col(15), y: 560 }, {}, { suffix: "x3" });

  // BLOCK route — log incident and stop
  const blkLog = replStep("b1", "Log Blocked Incident", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(14), 840,
    { vars: { context: [routerRestrict, "false_result"] } });
  const blkTc = node("TypeConverterComponent", "Blocked to Message", { x: col(16), y: 840 }, { output_type: "Message" }, { suffix: "b2" });
  const blkOut = node("ChatOutput", "Blocked", { x: col(17), y: 840 }, {}, { suffix: "b3" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    ...layer1.connections,
    layer1.internal,
    ...extract.connections,
    extract.internal,
    edge(extract.interpreter, "results", toMsgL2, "input_data"),
    edge(toMsgL2, "message_output", detector, "input_value"),
    edge(layer1.interpreter, "results", toMsg2, "input_data"),
    ...merge.connections,
    merge.internal,
    edge(merge.interpreter, "results", toMsgDec, "input_data"),
    // routers read the decision message
    edge(toMsgDec, "message_output", routerAllow, "input_text"),
    edge(toMsgDec, "message_output", routerReview, "input_text"),
    edge(toMsgDec, "message_output", routerRestrict, "input_text"),
    // ALLOW
    edge(routerAllow, "true_result", gateOut, "input_value"),
    // REVIEW
    edge(routerReview, "true_result", revLog.wrapper, "context"),
    ...revLog.connections,
    revLog.internal,
    edge(revLog.interpreter, "results", revTc, "input_data"),
    edge(revTc, "message_output", revOut, "input_value"),
    // RESTRICT
    edge(routerRestrict, "true_result", resLog.wrapper, "context"),
    ...resLog.connections,
    resLog.internal,
    edge(resLog.interpreter, "results", resTc, "input_data"),
    edge(resTc, "message_output", resOut, "input_value"),
    // BLOCK (Router 3 false = not RESTRICT = BLOCK or unknown)
    edge(routerRestrict, "false_result", blkLog.wrapper, "context"),
    ...blkLog.connections,
    blkLog.internal,
    edge(blkLog.interpreter, "results", blkTc, "input_data"),
    edge(blkTc, "message_output", blkOut, "input_value"),
  ];

  return buildFlow(
    "01 - Central Security Gate",
    "SECURITY ONLY. Linear fail-closed pipeline with deterministic conditional-router chain. Layer 1 rules + Layer 2 detection + Central Decision (fixed code, model never decides) + Smart routing (ALLOW passes the full payload; REVIEW held; RESTRICT held; BLOCK logged and stopped; unknown falls to BLOCK).",
    [chat, toMsg, layer1.wrapper, layer1.interpreter, extract.wrapper, extract.interpreter, toMsgL2, detector, toMsg2, merge.wrapper, merge.interpreter, toMsgDec, routerAllow, gateOut, routerReview, revLog.wrapper, revLog.interpreter, revTc, revOut, routerRestrict, resLog.wrapper, resLog.interpreter, resTc, resOut, blkLog.wrapper, blkLog.interpreter, blkTc, blkOut],
    edges
  );
}
function flowGraphPopulation() {
  const chat = node("ChatInput", "Chunk Text", { x: col(0), y: 0 },
    { input_value: "[Exemple] Article 12 : la carte nationale d'identité est délivrée par la direction de la sûreté nationale." }, { suffix: "g1" });
  const extractionPrompt = node("Prompt Template", "Entity Extraction Prompt", { x: col(1), y: 0 },
    { template: toPlainPrompt("entity_extraction_prompt.template.txt"), question: "" }, { suffix: "g2" });
  const model = node("MistralModel", "Extraction Model", { x: col(2), y: 0 },
    { model_name: "mistral-small-latest", temperature: 0.1, input_value: "", api_key: "" }, { suffix: "g3" });
  const toMsg1 = node("TypeConverterComponent", "Model → Message", { x: col(3), y: 0 }, { output_type: "Message" }, { suffix: "g4" });
  const validate = replStep("g5", "Validate Schema", "entities_validate.template.py", "json,re", col(4), 0,
    { vars: { context: [toMsg1, "message_output"] } });
  const toMsg2 = node("TypeConverterComponent", "Validated → Message", { x: col(6), y: 120 }, { output_type: "Message" }, { suffix: "g6" });
  const write = replStep("g7", "Neo4j Writer", "neo4j_write.template.py", "json,os,neo4j", col(6), 0,
    { vars: { context: [toMsg2, "message_output"] } });
  const toMsg3 = node("TypeConverterComponent", "Write Result → Message", { x: col(8), y: 120 }, { output_type: "Message" }, { suffix: "g8" });
  const out = node("ChatOutput", "Graph Write Summary", { x: col(9), y: 0 }, {}, { suffix: "g9" });

  const edges = [
    edge(chat, "message", extractionPrompt, "question"),
    edge(extractionPrompt, "prompt", model, "input_value"),
    edge(model, "text_output", toMsg1, "input_data"),
    ...validate.connections,
    validate.internal,
    edge(validate.interpreter, "results", toMsg2, "input_data"),
    ...write.connections,
    write.internal,
    edge(write.interpreter, "results", toMsg3, "input_data"),
    edge(toMsg3, "message_output", out, "input_value"),
  ];

  return buildFlow(
    "03 - Graph Population",
    "Extract entities/relations as structured JSON, validate against the allowed schema, then write to Neo4j using fixed parameterized MERGE queries only.",
    [chat, extractionPrompt, model, toMsg1, validate.wrapper, validate.interpreter, toMsg2, write.wrapper, write.interpreter, toMsg3, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Flow 4 — Vector retrieval
// ---------------------------------------------------------------------------
function flowVectorRetrieval() {
  const chat = node("ChatInput", "Question", { x: col(0), y: 0 },
    { input_value: "Comment renouveler la carte nationale d'identité ?" }, { suffix: "v1" });
  const embeddings = node("MistalAIEmbeddings", "Mistral Embeddings", { x: col(1), y: 260 }, { model: "mistral-embed", mistral_api_key: "" }, { suffix: "v2" });
  const astra = node("AstraDB", "Astra DB — admin_guide_chunks (search)", { x: col(2), y: 0 },
    { collection_name: "admin_guide_chunks", token: "", api_endpoint: "", number_of_results: 12 }, { suffix: "v3", primaryOutput: "search_results" });
  const toMsg1 = node("TypeConverterComponent", "Search → Message", { x: col(3), y: 0 }, { output_type: "Message" }, { suffix: "v4" });
  const filter = replStep("v5", "Filter Approved + Current", "vector_filter.template.py", "json,re", col(4), 0,
    { vars: { context: [toMsg1, "message_output"] } });
  const toMsg2 = node("TypeConverterComponent", "Filtered → Message", { x: col(6), y: 120 }, { output_type: "Message" }, { suffix: "v6" });
  const out = node("ChatOutput", "Approved Chunks (JSON)", { x: col(7), y: 0 }, {}, { suffix: "v7" });

  const edges = [
    edge(chat, "message", astra, "search_query"),
    edge(embeddings, "embeddings", astra, "embedding_model"),
    edge(astra, "search_results", toMsg1, "input_data"),
    ...filter.connections,
    filter.internal,
    edge(filter.interpreter, "results", toMsg2, "input_data"),
    edge(toMsg2, "message_output", out, "input_value"),
  ];

  return buildFlow(
    "04 - Vector Retrieval",
    "Semantic search on Astra DB restricted to chunks whose approval_status is APPROVED and whose version is current (deterministic post-filter).",
    [chat, embeddings, astra, toMsg1, filter.wrapper, filter.interpreter, toMsg2, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Flow 5 — Graph retrieval
// ---------------------------------------------------------------------------
function flowGraphRetrieval() {
  const chat = node("ChatInput", "Query (template + params)", { x: col(0), y: 0 },
    { input_value: '{"template": "procedure_requirements", "params": {"procedure_name": "Renouvellement CIN"}}' }, { suffix: "q1" });
  const toMsg = node("TypeConverterComponent", "Query → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "q2" });
  const retrieve = replStep("q3", "Graph Templates (read-only)", "graph_retrieve.template.py", "json,os,neo4j", col(2), 0,
    { vars: { context: [toMsg, "message_output"] } });
  const toMsg2 = node("TypeConverterComponent", "Records → Message", { x: col(4), y: 120 }, { output_type: "Message" }, { suffix: "q4" });
  const out = node("ChatOutput", "Graph Records (JSON)", { x: col(5), y: 0 }, {}, { suffix: "q5" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    ...retrieve.connections,
    retrieve.internal,
    edge(retrieve.interpreter, "results", toMsg2, "input_data"),
    edge(toMsg2, "message_output", out, "input_value"),
  ];

  return buildFlow(
    "05 - Graph Retrieval",
    "Python Interpreter running fixed READ-ONLY Cypher templates with bound parameters. Queries are never built from user text.",
    [chat, toMsg, retrieve.wrapper, retrieve.interpreter, toMsg2, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Flow 6 — Supervisor: understands intent, calls the specialist FLOW via RunFlow
// ---------------------------------------------------------------------------
function flowSupervisor() {
  const chat = node("ChatInput", "Session + Question", { x: col(0), y: 0 },
    { input_value: '{"question": "Quels documents pour renouveler la carte nationale ?", "gateway_base_url": "http://localhost:8100", "user_token": "<user access token>"}' },
    { suffix: "u1" });
  const toMsg = node("TypeConverterComponent", "Session → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "u2" });
  const model = node("MistralModel", "Supervisor Model", { x: col(1), y: 300 },
    { model_name: "mistral-small-latest", temperature: 0.2, input_value: "", api_key: "" }, { suffix: "u3" });
  const supervisor = node("Agent", "Supervisor (intent → RunFlow)", { x: col(2), y: 0 },
    { system_prompt: toPlainPrompt("supervisor_agent.template.txt"), add_current_date_tool: false }, { suffix: "u4" });

  // RunFlow tools — each one runs a dedicated specialist flow. After import,
  // re-select the target flow by name in each dropdown (fills flow_id_selected).
  const runProcedure = node("RunFlow", "Specialist — Procedure", { x: col(3), y: 0 },
    { flow_name_selected: "06a - Specialist Procedure", flow_id_selected: "", cache_flow: false }, { suffix: "u5" });
  const runLegal = node("RunFlow", "Specialist — Legal research", { x: col(3), y: 280 },
    { flow_name_selected: "06b - Specialist Legal Research", flow_id_selected: "", cache_flow: false }, { suffix: "u6" });
  const runDocuments = node("RunFlow", "Specialist — Document and administration", { x: col(3), y: 560 },
    { flow_name_selected: "06c - Specialist Document Administration", flow_id_selected: "", cache_flow: false }, { suffix: "u7" });

  // Offer the real specialist flow names in the dropdown options.
  for (const run of [runProcedure, runLegal, runDocuments]) {
    const field = run.nodeTemplate.template.flow_name_selected;
    field.options = ["06a - Specialist Procedure", "06b - Specialist Legal Research", "06c - Specialist Document Administration"];
  }

  const out = node("ChatOutput", "Supervisor Answer", { x: col(4), y: 0 }, {}, { suffix: "u8" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    edge(model, "model_output", supervisor, "agent_llm"),
    edge(toMsg, "message_output", supervisor, "input_value"),
    edge(runProcedure, "component_as_tool", supervisor, "tools"),
    edge(runLegal, "component_as_tool", supervisor, "tools"),
    edge(runDocuments, "component_as_tool", supervisor, "tools"),
    edge(supervisor, "response", out, "input_value"),
  ];

  return buildFlow(
    "06 - Supervisor",
    "Supervisor agent understands the client's intent and calls the dedicated specialist FLOW through RunFlow tools (Procedure / Legal research / Document & administration).",
    [chat, toMsg, model, supervisor, runProcedure, runLegal, runDocuments, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Flows 06a/06b/06c — specialist agents (imported before the supervisor;
// gateway tools: two-step agent-token issuance + tool call, session-driven)
// ---------------------------------------------------------------------------
function specialistFlow(name, suffix, displayName, promptFile, toolsSpec) {
  const chat = node("ChatInput", "Session + Question", { x: col(0), y: 0 },
    { input_value: '{"question": "Quels documents pour renouveler la carte nationale ?", "gateway_base_url": "http://localhost:8100", "user_token": "<user access token>"}' },
    { suffix: `${suffix}1` });
  const toMsg = node("TypeConverterComponent", "Session → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: `${suffix}2` });
  const model = node("MistralModel", "Specialist Model", { x: col(1), y: 300 },
    { model_name: "mistral-small-latest", temperature: 0.2, input_value: "", api_key: "" }, { suffix: `${suffix}3` });
  const agent = node("Agent", displayName, { x: col(2), y: 0 },
    { system_prompt: toPlainPrompt(promptFile), add_current_date_tool: false }, { suffix: `${suffix}4` });

  const nodes = [chat, toMsg, model, agent];
  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    edge(model, "model_output", agent, "agent_llm"),
    edge(toMsg, "message_output", agent, "input_value"),
  ];

  let y = 300;
  for (const tool of toolsSpec) {
    const gw = replStep(`${suffix}t${tool}`, `Gateway Tool — ${tool}`, "gateway_call.template.py",
      "json,re,urllib.request,urllib.error", col(1), y, { tool, agent: displayName, vars: { session_json: [toMsg, "message_output"] } });
    nodes.push(gw.wrapper, gw.interpreter);
    edges.push(...gw.connections);
    edges.push(gw.internal);
    edges.push(edge(gw.interpreter, "results", agent, "tools", { asTool: true }));
    y += 280;
  }

  const out = node("ChatOutput", `${displayName} Answer`, { x: col(4), y: 0 }, {}, { suffix: `${suffix}9` });
  nodes.push(out);
  edges.push(edge(agent, "response", out, "input_value"));

  return buildFlow(name, `Specialist agent (${displayName}). Tools go through the backend gateway: the fixed tool code first requests a short-lived agent token (backend checks permissions), then calls the tool with both tokens. The tool payload is derived from the session, never composed by the model.`, nodes, edges);
}

function flowSpecialistProcedure() {
  return specialistFlow("06a - Specialist Procedure", "sa", "PROCEDURE_AGENT", "specialist_procedure.txt", ["VECTOR_RETRIEVAL"]);
}

function flowSpecialistLegal() {
  return specialistFlow("06b - Specialist Legal Research", "sb", "LEGAL_RESEARCH_AGENT", "specialist_legal.txt", ["VECTOR_RETRIEVAL", "GRAPH_RETRIEVAL"]);
}

function flowSpecialistDocuments() {
  return specialistFlow("06c - Specialist Document Administration", "sc", "DOCUMENT_ADMIN_AGENT", "specialist_document.txt", ["DOCUMENT_INDEX"]);
}

// ---------------------------------------------------------------------------
// Flow 7 — Answer validation (deterministic)
// ---------------------------------------------------------------------------
function flowAnswerValidation() {
  const chat = node("ChatInput", "Citations + Chunks", { x: col(0), y: 0 },
    { input_value: '{"citations": [{"document_id": "DOC-0001", "article_number": "12", "version": "1"}], "chunks": [{"metadata": {"document_id": "DOC-0001", "article_number": "12", "version": "1", "approval_status": "APPROVED", "is_current": true}}]}' },
    { suffix: "a1" });
  const toMsg = node("TypeConverterComponent", "Payload → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "a2" });
  const validate = replStep("a3", "Validate Citations", "answer_validate.template.py", "json,re", col(2), 0,
    { vars: { context: [toMsg, "message_output"] } });
  const toMsg2 = node("TypeConverterComponent", "Verdict → Message", { x: col(4), y: 120 }, { output_type: "Message" }, { suffix: "a4" });
  const out = node("ChatOutput", "Validation Verdict", { x: col(5), y: 0 }, {}, { suffix: "a5" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    ...validate.connections,
    validate.internal,
    edge(validate.interpreter, "results", toMsg2, "input_data"),
    edge(toMsg2, "message_output", out, "input_value"),
  ];

  return buildFlow(
    "07 - Answer Validation",
    "Deterministic validation: every citation must exist among retrieved chunks AND be APPROVED and current. No model involved.",
    [chat, toMsg, validate.wrapper, validate.interpreter, toMsg2, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Flow 8 — Human review handoff
// ---------------------------------------------------------------------------
function flowHumanHandoff() {
  const chat = node("ChatInput", "Session + Case", { x: col(0), y: 0 },
    { input_value: '{"gateway_base_url": "http://localhost:8100", "user_token": "<user access token>", "conversation_id": "c1", "question_summary": "[Exemple] question sensible"}' },
    { suffix: "h1" });
  const toMsg = node("TypeConverterComponent", "Payload → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "h2" });
  const handoff = replStep("h3", "Submit Review Case", "human_handoff.template.py", "json,re,urllib.request,urllib.error", col(2), 0,
    { vars: { session_json: [toMsg, "message_output"] } });
  const toMsg2 = node("TypeConverterComponent", "Result → Message", { x: col(4), y: 120 }, { output_type: "Message" }, { suffix: "h4" });
  const out = node("ChatOutput", "Handoff Result", { x: col(5), y: 0 }, {}, { suffix: "h5" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    ...handoff.connections,
    handoff.internal,
    edge(handoff.interpreter, "results", toMsg2, "input_data"),
    edge(toMsg2, "message_output", out, "input_value"),
  ];

  return buildFlow(
    "08 - Human Review Handoff",
    "Builds the review case and submits it through the backend tool gateway (HUMAN_HANDOFF). The backend creates the case for the employee dashboard.",
    [chat, toMsg, handoff.wrapper, handoff.interpreter, toMsg2, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Flow 9 — Execution logging
// ---------------------------------------------------------------------------
function flowExecutionLogging() {
  const chat = node("ChatInput", "Execution Record", { x: col(0), y: 0 },
    { input_value: '{"gateway_base_url": "http://localhost:8100", "user_token": "<user access token>", "flow": "01 - Central Security Gate", "status": "SUCCESS", "duration_ms": 240, "correlation_id": "run-001"}' },
    { suffix: "l1" });
  const toMsg = node("TypeConverterComponent", "Record → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "l2" });
  const log = replStep("l3", "Log Execution", "execution_log.template.py", "json,re,urllib.request,urllib.error", col(2), 0,
    { vars: { context: [toMsg, "message_output"] } });
  const toMsg2 = node("TypeConverterComponent", "Log Result → Message", { x: col(4), y: 120 }, { output_type: "Message" }, { suffix: "l4" });
  const out = node("ChatOutput", "Logging Result", { x: col(5), y: 0 }, {}, { suffix: "l5" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    ...log.connections,
    log.internal,
    edge(log.interpreter, "results", toMsg2, "input_data"),
    edge(toMsg2, "message_output", out, "input_value"),
  ];

  return buildFlow(
    "09 - Execution Logging",
    "Posts each workflow execution to the backend, which writes it into the audit_events table (action WORKFLOW_EXECUTION).",
    [chat, toMsg, log.wrapper, log.interpreter, toMsg2, out],
    edges
  );
}

// ---------------------------------------------------------------------------
// Emit + validate
// ---------------------------------------------------------------------------
const builders = [
  flowSecurityGate,
  flowGraphPopulation,
  flowVectorRetrieval,
  flowGraphRetrieval,
  flowSupervisor,
  flowSpecialistProcedure,
  flowSpecialistLegal,
  flowSpecialistDocuments,
  flowAnswerValidation,
  flowHumanHandoff,
  flowExecutionLogging,
];

let written = 0;
for (const build of builders) {
  const flow = build();
  const fileName =
    flow.name
      .replace(/^[0-9]+ - /, "")
      .toLowerCase()
      .replace(/\([^)]*\)/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-+$/, "") + ".json";
  const serialized = JSON.stringify(flow, null, 2);

  // Hard guarantees before writing:
  if (/@@/.test(serialized)) throw new Error(`${flow.name}: unresolved @@ marker`);
  if (/clinic/i.test(serialized)) throw new Error(`${flow.name}: inherited reference text found`);
  for (const nodeJson of flow.data.nodes) {
    if (nodeJson.data.type !== "Prompt Template") continue;
    const template = nodeJson.data.node.template;
    const text = template.template?.value || "";
    // Real placeholders are single-braced; {{...}} are escaped Python braces.
    const usedVars = [...text.matchAll(/(?<!\{)\{([a-z_0-9]+)\}(?!\})/g)].map((m) => m[1]);
    for (const varName of usedVars) {
      if (!template[varName]) throw new Error(`${flow.name}: {${varName}} has no field in ${nodeJson.id}`);
      const wired = flow.data.edges.some(
        (e) => e.target === nodeJson.id && e.data.targetHandle.fieldName === varName
      );
      if (!wired) throw new Error(`${flow.name}: {${varName}} in ${nodeJson.id} has no connection`);
    }
    // No dangling inputs: an optional input field may exist only if used.
    for (const fieldName of ["context", "question", "tool_placeholder"]) {
      if (template[fieldName] && !usedVars.includes(fieldName)) {
        throw new Error(`${flow.name}: unused input ${fieldName} still present on ${nodeJson.id}`);
      }
    }
  }
  // Prompt text inputs accept ONLY Message sources — a Data/DataFrame output
  // must go through a Type Convert first (reference convention).
  for (const edgeJson of flow.data.edges) {
    const target = flow.data.nodes.find((n) => n.id === edgeJson.target);
    if (!target || target.data.type !== "Prompt Template") continue;
    const outTypes = edgeJson.data.sourceHandle.output_types || [];
    if (!outTypes.includes("Message")) {
      throw new Error(
        `${flow.name}: edge ${edgeJson.source} → ${edgeJson.target} feeds a Prompt with ${outTypes.join(",")} — needs a Type Convert`
      );
    }
  }

  writeFileSync(join(outDir, fileName), serialized);
  console.log(`+ ${fileName} (${flow.data.nodes.length} nodes, ${flow.data.edges.length} edges)`);
  written += 1;
}
console.log(`\nWrote ${written} flows to ${outDir} — all guarantees enforced`);
