# Langflow 1.7 — Workflows

> **STATUS 2026: reference only.** This Langflow implementation has been
> superseded by the standalone **LangGraph workflow service** in
> `../langgraph/` (`api.py` + `guide_graph/`): same architecture, same
> security guarantees (2-layer gate, RAG approval filter, blue/red team,
> gateway agent-token flow), rebuilt as LangGraph nodes + a FastAPI
> service the backend calls over HTTP. The build sheets below remain the
> authoritative source for prompts, tests and tool contracts.

Nine workflows for the Administrative Guide platform, built with **native
Langflow 1.7 components only**. Each workflow has:

- an **importable JSON file** in `flows/` (generated in the exact 1.7 export
  format — component templates cloned from real reference exports),
- a **build sheet** in `build-sheets/` (authoritative: ordered components with
  settings, every connection, fixed code files, I/O JSON contract, test case),
- its **fixed Python / prompt code** in `code/` (the code that goes into the
  Prompt Template + Python Interpreter pairs — never model-generated).

## Import

1. Start Langflow 1.7 and open your project.
2. Import each file from `flows/` (Import → select the JSON). **Order:
   06a → 06b → 06c → then 06** (the supervisor's RunFlow components reference
   the specialist flows by name), and note `flow_id` of flow 06.
3. Environment variables required by the flows:
   - `MISTRAL_API_KEY` — Mistral model + embeddings API keys (leave the key
     fields empty in the components; Langflow reads the env var)
   - `ASTRA_DB_APPLICATION_TOKEN`, `ASTRA_DB_API_ENDPOINT` — Astra DB
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — graph flows
   - `pip install neo4j` inside the Langflow environment (flows 03/05)
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — flow 01 logs blocked
     requests directly to the database
   - `LANGFLOW_BASE_URL`, `LANGFLOW_SUPERVISOR_FLOW_ID`, `LANGFLOW_API_KEY`
     — flow 01 chains ALLOW requests to the supervisor workflow
4. If an edge renders disconnected after import, reconnect it following the
   flow's build sheet (the sheet is authoritative).

## The twelve flow files (9 workflows + 3 specialists)

| # | Flow | JSON | Sheet |
|---|------|------|-------|
| 01 | Central Security Gate (entry: decides in-flow, chains to 06 on ALLOW, logs + stops otherwise) | `central-security-gate.json` | `build-sheets/01-central-security-gate.md` |
| 01b | Security Gate Layer 1 only — **keyless testing variant** | `01b-security-gate-layer-1.json` | `build-sheets/01-central-security-gate.md` |
| 02 | Document ingestion → Astra DB (PENDING_REVIEW, never publishes) | `document-ingestion.json` | `build-sheets/02-document-ingestion.md` |
| 03 | Graph population → Neo4j (validated schema, fixed MERGE) | `graph-population.json` | `build-sheets/03-graph-population.md` |
| 04 | Vector retrieval (APPROVED + current only) | `vector-retrieval.json` | `build-sheets/04-vector-retrieval.md` |
| 05 | Graph retrieval (fixed read-only templates) | `graph-retrieval.json` | `build-sheets/05-graph-retrieval.md` |
| 06 | Supervisor (intent → RunFlow) | `supervisor.json` | `build-sheets/06-supervisor.md` |
| 06a | Specialist — Procedure | `06a-specialist-procedure.json` | `build-sheets/06a-specialists.md` |
| 06b | Specialist — Legal research | `06b-specialist-legal-research.json` | `build-sheets/06a-specialists.md` |
| 06c | Specialist — Document administration | `06c-specialist-document-administration.json` | `build-sheets/06a-specialists.md` |
| 07 | Answer validation (deterministic, no model) | `answer-validation.json` | `build-sheets/07-answer-validation.md` |
| 08 | Human review handoff (through the gateway) | `human-review-handoff.json` | `build-sheets/08-human-review-handoff.md` |
| 09 | Execution logging → backend audit tables | `execution-logging.json` | `build-sheets/09-execution-logging.md` |

> Import order: 06a → 06b → 06c → then 06 (the supervisor's RunFlow
> components reference the specialist flows by name).

## How data enters the Python Interpreters

Langflow 1.7's Python Interpreter takes its code as text. The fixed pattern
used everywhere in these flows:

```
[upstream JSON] → Type Convert (Message) → Prompt Template ("code wrapper",
template = fixed python with {context}/{question} placeholders, braces
escaped) → Python Interpreter (python_code from the prompt) → results
```

The wrapper embeds the incoming JSON as a `r'''...'''` literal; the fixed code
parses it and always ends with `print(json.dumps(result))`. Nothing in these
files is model-generated at runtime — the only model calls are the ones the
spec asks for (Layer 2 detection, entity extraction, specialist answers).

## Regenerating the flows

```bash
cd langflow/tools
node extract-components.mjs   # rebuilds component-library.json from the reference exports
node generate-flows.mjs       # rebuilds flows/*.json from the code templates
```

The generator escapes Python braces for the Prompt Templates automatically
(`{` → `{{`) and substitutes the `@@CONTEXT@@ / @@QUESTION@@ / @@QUOTE@@ /
@@TOOL@@` markers used in `code/*.template.py`.
