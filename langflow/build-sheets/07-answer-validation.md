# Build sheet 07 — Answer validation (deterministic)

**File:** `flows/answer-validation.json` · **Trigger:** backend call with the proposed answer's citations + the retrieval results · **Model:** NONE (fully deterministic)

## Purpose
Every citation in a proposed answer must exist among the retrieved chunks AND
be `APPROVED` AND current. No model is involved anywhere in this flow.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Citations + Chunks | JSON input |
| 2 | Type Convert | Payload → Message | output_type: Message |
| 3 | Prompt Template | Validate Citations — fixed code | template = escaped `code/answer_validate.template.py` |
| 4 | Python Interpreter | Validate Citations | global_imports: `json,re` |
| 5 | Type Convert | Verdict → Message | output_type: Message |
| 6 | Chat Output | Validation Verdict | — |

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
{"citations": [{"document_id": "DOC-0001", "article_number": "12", "version": "1"}],
 "chunks": [{"metadata": {"document_id": "DOC-0001", "article_number": "12",
   "version": "1", "approval_status": "APPROVED", "is_current": true}}]}
```
Output: `{"valid": true, "invalid_citations": [], "checked_count": 1}`

## Test case
1. Citation matching an approved current chunk → `valid: true`.
2. Citation whose document is PENDING_REVIEW → `valid: false` and the citation
   is listed in `invalid_citations` (the backend then blocks the answer).
3. Answer with zero citations → `valid: false` (checked_count = 0).
