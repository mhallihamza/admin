# Build sheet 08 — Human review handoff

**File:** `flows/human-review-handoff.json` · **Trigger:** backend call when the gate flags a case or the citizen requests review · **Model:** NONE

## Purpose
Build the review case and submit it **through the backend tool gateway**
(`HUMAN_HANDOFF`). The backend creates the case that appears in the employee
dashboard queue.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Session + Case | JSON: `{gateway_base_url, user_token, conversation_id, question_summary}` |
| 2 | Type Convert | Payload → Message | output_type: Message |
| 3 | Prompt Template | Submit Review Case — fixed code | template = escaped `code/human_handoff.template.py` — **single named input `{session_json}`** |
| 4 | Python Interpreter | Submit Review Case | global_imports: `json,re,urllib.request,urllib.error` |
| 5 | Type Convert | Result → Message | output_type: Message |
| 6 | Chat Output | Handoff Result | — |

## Connections
```
ChatInput(1).message → TypeConvert(2).input_data
TypeConvert(2).message_output → Prompt(3).session_json
Prompt(3).prompt → PyInterpreter(4).python_code
PyInterpreter(4).results → TypeConvert(5).input_data
TypeConvert(5).message_output → ChatOutput(6).input_value
```

## Input / Output JSON
Input: session + case (see Chat Input default in the flow).
Output: `{"status": "handed_off", "http_status": 200, "body": {...}}`

## Test case
1. Valid session + `agent_token` issued for `HUMAN_HANDOFF` → gateway returns
   200; the case appears with status OPEN in the employee queue (Phase 3 UI /
   `review_cases` table in production).
2. Agent token issued for another tool → the gateway denies; the flow returns
   `status: "failed"` with the 403 body and the denial is audited.
