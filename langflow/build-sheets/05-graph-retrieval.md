# Build sheet 05 — Graph retrieval

**File:** `flows/graph-retrieval.json` · **Trigger:** backend call with `{template, params}` · **Model:** none · **Requires:** neo4j driver + env `NEO4J_*`

## Purpose
Python Interpreter running **fixed READ-ONLY Cypher templates with bound
parameters**. Queries are never built from user text: the template name
selects the query, values travel only as parameters.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Query (template + params) | JSON input |
| 2 | Type Convert | Query → Message | output_type: Message |
| 3 | Prompt Template | Graph Templates — fixed code | template = escaped `code/graph_retrieve.template.py` |
| 4 | Python Interpreter | Graph Templates (read-only) | global_imports: `json,os,neo4j` |
| 5 | Type Convert | Records → Message | output_type: Message |
| 6 | Chat Output | Graph Records (JSON) | — |

## Connections
```
ChatInput(1).message          → TypeConvert(2).input_data
TypeConvert(2).message_output → Prompt(3).context
Prompt(3).prompt              → PyInterpreter(4).python_code
PyInterpreter(4).results      → TypeConvert(5).input_data
TypeConvert(5).message_output → ChatOutput(6).input_value
```

## Fixed templates (whitelist inside the code)
`procedure_requirements`, `procedure_administration`, `documents_of_law`,
`administration_services` — any other name returns an error, never a query.

## Input / Output JSON
Input:
```json
{"template": "procedure_requirements", "params": {"procedure_name": "Renouvellement CIN"}}
```
Output:
```json
{"template": "procedure_requirements", "records": [{"requirement": "copie CIN"}],
 "params_used": {"procedure_name": "Renouvellement CIN"}, "error": null}
```

## Test case
1. After sheet 03 populated the graph, run `procedure_requirements` → records
   come back.
2. Run with `template: "MATCH (n) RETURN n"` → error `unknown template`; the
   raw Cypher is NEVER executed.
3. Check the Neo4j log: the session was opened READ-only.
