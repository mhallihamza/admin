# Build sheet 06 — Supervisor (intent → RunFlow)

**File:** `flows/supervisor.json` · **Trigger:** backend call with the session JSON · **Model:** mistral-small-latest (temperature 0.2)
**Import order: import the three specialist flows (06a, 06b, 06c) BEFORE this one.**

## Purpose
The supervisor **understands the client's intent itself** and calls the
dedicated specialist FLOW through native **RunFlow** tools — the same pattern
as the reference supervisor (one agent + one RunFlow tool per intent). It
never answers from its own knowledge: it returns the specialist flow's answer.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Session + Question | JSON `{question, gateway_base_url, user_token}` |
| 2 | Type Convert | Session → Message | output_type: Message |
| 3 | MistralAI | Supervisor Model | `mistral-small-latest`, temperature 0.2 |
| 4 | Agent | Supervisor (intent → RunFlow) | system_prompt = `code/supervisor_agent.template.txt`; Current Date off |
| 5 | Run Flow | Specialist — Procedure | flow_name_selected = **06a - Specialist Procedure** |
| 6 | Run Flow | Specialist — Legal research | flow_name_selected = **06b - Specialist Legal Research** |
| 7 | Run Flow | Specialist — Document and administration | flow_name_selected = **06c - Specialist Document Administration** |
| 8 | Chat Output | Supervisor Answer | — |

## Connections
```
ChatInput(1).message            → TypeConvert(2).input_data
MistralAI(3).model_output       → Agent(4).agent_llm
TypeConvert(2).message_output   → Agent(4).input_value
RunFlow(5).component_as_tool    → Agent(4).tools
RunFlow(6).component_as_tool    → Agent(4).tools
RunFlow(7).component_as_tool    → Agent(4).tools
Agent(4).response               → ChatOutput(8).input_value
```

## After import (one manual step per RunFlow)
Open each RunFlow component and **re-select the target flow by name** in the
`flow_name_selected` dropdown — this fills `flow_id_selected` with the real
imported flow id and refreshes the sub-flow input fields.

## Input / Output JSON
Input:
```json
{"question": "Quels documents pour renouveler la carte nationale ?",
 "gateway_base_url": "http://localhost:8100", "user_token": "<user access token>"}
```
Output: the routed specialist flow's answer (text), e.g. the procedure answer
with Steps / Required documents / Competent administration / Sources.

## Test case
1. «Quels documents pour renouveler la CIN ?» → the supervisor calls
   **Specialist — Procedure**; the audit trail shows the gateway tool calls
   issued by PROCEDURE_AGENT.
2. «ما المادة القانونية المنظمة للبطاقة؟» → **Specialist — Legal research**.
3. «حالة الوثيقة DOC-0001؟» → **Specialist — Document and administration**.
4. Unclear question → falls back to the Procedure specialist (per the system
   prompt), never an invented answer.
