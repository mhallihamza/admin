# Build sheet 09 — Execution logging

**File:** `flows/execution-logging.json` · **Trigger:** after each workflow run (backend calls this flow, or the flow is invoked with the run record) · **Model:** NONE

## Purpose
Post each workflow execution to the backend `POST /api/logs/execution`, which
writes it into the existing `audit_events` table (action `WORKFLOW_EXECUTION`)
— surfaced in the admin **Workflows monitor**.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Execution Record | JSON: `{gateway_base_url, user_token, flow, status, duration_ms, correlation_id}` |
| 2 | Type Convert | Record → Message | output_type: Message |
| 3 | Prompt Template | Log Execution — fixed code | template = escaped `code/execution_log.template.py` |
| 4 | Python Interpreter | Log Execution | global_imports: `json,re,urllib.request,urllib.error` |
| 5 | Type Convert | Log Result → Message | output_type: Message |
| 6 | Chat Output | Logging Result | — |

## Connections
```
ChatInput(1).message → TypeConvert(2).input_data
TypeConvert(2).message_output → Prompt(3).context
Prompt(3).prompt → PyInterpreter(4).python_code
PyInterpreter(4).results → TypeConvert(5).input_data
TypeConvert(5).message_output → ChatOutput(6).input_value
```

## Input / Output JSON
Input:
```json
{"gateway_base_url": "http://localhost:8100", "user_token": "<user access token>",
 "flow": "01 - Central Security Gate", "status": "SUCCESS", "duration_ms": 240,
 "correlation_id": "run-001"}
```
Output: `{"status": "logged", "http_status": 200, "body": {"status": "logged"}}`

## Test case
1. Post a record → `audit_events` contains `WORKFLOW_EXECUTION` with the flow
   name, status and duration in metadata; it appears in the admin monitor.
2. Post `status: "MAYBE"` → the backend rejects with 422 (nothing logged).
