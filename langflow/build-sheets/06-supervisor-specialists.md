# Build sheet 06 — Supervisor + three specialists

**File:** `flows/supervisor-specialists.json` · **Trigger:** backend call with the session JSON · **Model:** mistral-small-latest · **Tools:** ONLY via the backend gateway

## Purpose
Supervisor with three specialist agents — Procedure, Legal research, Document &
administration. Every tool call goes through the backend tool gateway with a
per-request agent token (`X-Agent-Token`) that the backend minted for this run.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Session + Question | JSON: `{question, gateway_base_url, user_token, agent_token}` |
| 2 | Type Convert | Session → Message | output_type: Message |
| 3 | Prompt Template | Route — fixed code | template = escaped `code/supervisor_route.template.py` (deterministic keyword rules; backend can force a route) |
| 4 | Python Interpreter | Route | global_imports: `json,re` |
| 5 | MistralAI | Specialists Model | temperature 0.2 |
| 6–8 | Prompt Template + Python Interpreter ×3 | Gateway Tool — VECTOR_RETRIEVAL / GRAPH_RETRIEVAL / DOCUMENT_INDEX | template = escaped `code/gateway_call.template.py` (generator injects the TOOL constant); global_imports: `json,re,urllib.request,urllib.error` |
| 9 | Agent | PROCEDURE_AGENT | system_prompt = `code/specialist_procedure.txt`; tools: gateway VECTOR_RETRIEVAL |
| 10 | Agent | LEGAL_RESEARCH_AGENT | system_prompt = `code/specialist_legal.txt`; tools: VECTOR_RETRIEVAL + GRAPH_RETRIEVAL |
| 11 | Agent | DOCUMENT_ADMIN_AGENT | system_prompt = `code/specialist_document.txt`; tools: DOCUMENT_INDEX |
| 12–14 | Type Convert ×3 | agent answer → Message | output_type: Message |
| 15 | Prompt Template | Assemble — fixed code | template = escaped `code/supervisor_assemble.template.py` |
| 16 | Python Interpreter | Assemble Routed Answer | global_imports: `json,re` |
| 17 | Type Convert | Answer → Message | output_type: Message |
| 18 | Chat Output | Supervisor Answer | — |

## Connections (essential)
```
ChatInput(1).message → TypeConvert(2).input_data
TypeConvert(2).message_output → Prompt(3).context ; Prompt(3).prompt → PyInterpreter(4).python_code
MistralAI(5).model_output → Agent(9/10/11).agent_llm
TypeConvert(2).message_output → Agent(9/10/11).input_value
TypeConvert(2).message_output → GatewayPrompt(6/7/8).context  (session: base_url + tokens)
GatewayPrompt(6/7/8).prompt → GatewayPyInterpreter.python_code
GatewayPyInterpreter(6).results → Agent(9).tools ; Agent(10).tools
GatewayPyInterpreter(7).results → Agent(10).tools
GatewayPyInterpreter(8).results → Agent(11).tools
Agent(9/10/11).response → TypeConvert(12/13/14).input_data
TypeConvert(12/13/14).message_output → Prompt(15).context   (3 edges, list input)
PyInterpreter(4).results → Prompt(15).question
Prompt(15).prompt → PyInterpreter(16).python_code
PyInterpreter(16).results → TypeConvert(17).input_data → ChatOutput(18).input_value
```
> If a `results → tools` edge renders disconnected after import, reconnect it
> by dragging the gateway Python Interpreter onto the agent's Tools handle —
> the build sheet is authoritative.

## Input / Output JSON
Input:
```json
{"question": "Quels documents pour renouveler la carte nationale ?",
 "gateway_base_url": "http://localhost:8100",
 "user_token": "<user access token>", "agent_token": "<agent token>"}
```
Output:
```json
{"specialist": "PROCEDURE_AGENT", "answer": "[PROCEDURE_AGENT] ..."}
```

## Test case
1. Question «Quels documents pour renouveler la CIN ?» → routed to
   PROCEDURE_AGENT; the gateway tool logs `VECTOR_RETRIEVAL` acceptance in the
   backend audit (`/api/logs` + tools table checks).
2. Question mentioning «article de loi» → LEGAL_RESEARCH_AGENT.
3. Stop the backend → the gateway tool returns `status: "denied"` and the
   agent answers that no official data is available (no invented content).
