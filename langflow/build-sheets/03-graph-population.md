# Build sheet 03 — Graph population

**File:** `flows/graph-population.json` · **Trigger:** canvas run per chunk (paste the chunk text) · **Model:** mistral-small-latest (temperature 0.1) · **Requires:** `pip install neo4j` in the Langflow environment; env `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

## Purpose
Extract entities/relations as structured JSON, **validate against the allowed
schema**, then write to Neo4j using **fixed parameterized MERGE queries only**.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Chunk Text | paste one chunk's text |
| 2 | Prompt Template | Entity Extraction Prompt | template = `code/entity_extraction_prompt.template.txt` (uses `{question}`) |
| 3 | MistralAI | Extraction Model | temperature 0.1 |
| 4 | Type Convert | Model → Message | output_type: Message |
| 5 | Prompt Template | Validate Schema — fixed code | template = escaped `code/entities_validate.template.py` |
| 6 | Python Interpreter | Validate Schema | global_imports: `json,re` |
| 7 | Type Convert | Validated → Message | output_type: Message |
| 8 | Prompt Template | Neo4j Writer — fixed code | template = escaped `code/neo4j_write.template.py` |
| 9 | Python Interpreter | Neo4j Writer | global_imports: `json,os,neo4j` |
| 10 | Type Convert | Write Result → Message | output_type: Message |
| 11 | Chat Output | Graph Write Summary | — |

## Connections
```
ChatInput(1).message        → Prompt(2).question
Prompt(2).prompt            → MistralAI(3).input_value
MistralAI(3).text_output    → TypeConvert(4).input_data
TypeConvert(4).message_output → Prompt(5).context
Prompt(5).prompt            → PyInterpreter(6).python_code
PyInterpreter(6).results    → TypeConvert(7).input_data
TypeConvert(7).message_output → Prompt(8).context
Prompt(8).prompt            → PyInterpreter(9).python_code
PyInterpreter(9).results    → TypeConvert(10).input_data
TypeConvert(10).message_output → ChatOutput(11).input_value
```

## Allowed schema (enforced twice: validator + writer)
- Entities: `ADMINISTRATION, SERVICE, PROCEDURE, DOCUMENT, LAW, ARTICLE, CITY, FORM, REQUIREMENT`
- Relations: `BELONGS_TO, REQUIRES, SUPERSEDES, MANAGED_BY, LOCATED_IN, CITES, PART_OF`

## Input / Output JSON
Input (model output, validated): `{"entities": [{"label": "PROCEDURE", "name": "..."}], "relations": [{"type": "REQUIRES", "source": "PROCEDURE:x", "target": "DOCUMENT:y"}]}`
Output: `{"written_entities": 2, "written_relations": 1, "errors": []}`

## Test case
1. Feed a chunk mentioning one procedure and one required document → summary
   reports `written_entities: 2`, `written_relations: 1`.
2. Feed model output containing label `HACKER` → the validator moves it to
   `rejected`, nothing is written.
3. Verify in Neo4j Browser: only whitelisted labels/relation types exist.
