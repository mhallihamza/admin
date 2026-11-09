# Build sheets 06a / 06b / 06c — Specialist flows (called by RunFlow)

**Files:** `flows/06a-specialist-procedure.json`, `flows/06b-specialist-legal-research.json`, `flows/06c-specialist-document-administration.json`
**Model:** mistral-small-latest (temperature 0.2) · **Import BEFORE the supervisor.**

## Purpose
One dedicated flow per intent, each hosting ONE specialist agent whose tools
call the backend gateway. The gateway tool code runs **two steps**: it first
asks the backend for a short-lived agent token (`POST /api/gateway/token` —
the backend checks `tool_permissions` + `agent_permissions` and audits
denials), then calls the tool with both tokens (`X-Agent-Token`).
**The tool payload is derived deterministically from the session** (e.g.
`VECTOR_RETRIEVAL` searches for `session.question`) — the model decides WHEN
to call the tool, never WHAT payload to send.

## Shared structure (identical in the three flows)
| # | Component | Settings |
|---|---|---|
| 1 | Chat Input | JSON `{question, gateway_base_url, user_token}` (passed through by RunFlow) |
| 2 | Type Convert | output_type: Message |
| 3 | MistralAI | Specialist Model |
| 4 | Agent | system_prompt = `code/specialist_*.txt`; tools = the gateway pairs below |
| 5+ | Prompt Template + Python Interpreter per tool | template = escaped `code/gateway_call.template.py` — **single named input `{session_json}`**; global_imports `json,re,urllib.request,urllib.error`; constants TOOL / AGENT injected |
| last | Chat Output | agent answer |

## The three variants
| Flow | Agent | system prompt | Tools (agent, tool) |
|---|---|---|---|
| 06a | PROCEDURE_AGENT | `specialist_procedure.txt` | (PROCEDURE_AGENT, VECTOR_RETRIEVAL) |
| 06b | LEGAL_RESEARCH_AGENT | `specialist_legal.txt` | (LEGAL_RESEARCH_AGENT, VECTOR_RETRIEVAL), (LEGAL_RESEARCH_AGENT, GRAPH_RETRIEVAL) |
| 06c | DOCUMENT_ADMIN_AGENT | `specialist_document.txt` | (DOCUMENT_ADMIN_AGENT, DOCUMENT_INDEX) |

## Connections (06a shown; 06b/06c identical with their extra tools)
```
ChatInput(1).message → TypeConvert(2).input_data
MistralAI(3).model_output → Agent(4).agent_llm
TypeConvert(2).message_output → Agent(4).input_value
TypeConvert(2).message_output → GatewayPrompt(5).session_json
GatewayPrompt(5).prompt → GatewayPyInterpreter.python_code
GatewayPyInterpreter.results → Agent(4).tools
Agent(4).response → ChatOutput.input_value
```

## Input / Output JSON
Input (same object the supervisor received — RunFlow passes it through):
```json
{"question": "...", "gateway_base_url": "http://localhost:8100", "user_token": "<token>"}
```
Output: the specialist's answer text (starts with its marker, e.g.
`[PROCEDURE_AGENT]`, followed by Steps / Required documents / Sources).

## Test case (per flow)
1. Run with a valid user token → the gateway issues an agent token (audit:
   `AGENT_TOKEN_DENIED` only when denied), the tool call is accepted, and the
   answer cites only tool results.
2. Revoke the role→tool permission in `tool_permissions` → step 1 returns 403,
   the flow reports `status: "denied"` and the backend audit contains
   `AGENT_TOKEN_DENIED`.
3. Unreachable gateway → `status: "error"`, and the agent states that no
   official data is available (never invented content).
