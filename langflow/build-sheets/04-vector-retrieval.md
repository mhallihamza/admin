# Build sheet 04 — Vector retrieval

**File:** `flows/vector-retrieval.json` · **Trigger:** canvas run or backend call with the question · **Model:** mistral-embed only (no LLM)

## Purpose
Semantic search on Astra DB restricted to chunks whose `approval_status` is
`APPROVED` and whose version is current (deterministic post-filter). The
database-level filter can be added via the Astra DB component's
`advanced_search_filter`; the post-filter below guarantees it regardless.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Question | the citizen question |
| 2 | MistralAI Embeddings | Mistral Embeddings | model `mistral-embed` |
| 3 | Astra DB | Astra DB — admin_guide_chunks (search) | collection `admin_guide_chunks`, number_of_results 12 |
| 4 | Type Convert | Search → Message | output_type: Message |
| 5 | Prompt Template | Filter Approved + Current — fixed code | template = escaped `code/vector_filter.template.py` |
| 6 | Python Interpreter | Filter Approved + Current | global_imports: `json,re` |
| 7 | Type Convert | Filtered → Message | output_type: Message |
| 8 | Chat Output | Approved Chunks (JSON) | — |

## Connections
```
ChatInput(1).message          → AstraDB(3).search_query
MistralEmbeddings(2).embeddings → AstraDB(3).embedding_model
AstraDB(3).search_results     → TypeConvert(4).input_data
TypeConvert(4).message_output → Prompt(5).context
Prompt(5).prompt              → PyInterpreter(6).python_code
PyInterpreter(6).results      → TypeConvert(7).input_data
TypeConvert(7).message_output → ChatOutput(8).input_value
```

## Input / Output JSON
Input: `Comment renouveler la carte nationale d'identité ?`
Output:
```json
{"results": [{"metadata": {"document_id": "DOC-0001", "article_number": "12",
   "version": 1, "approval_status": "APPROVED", "is_current": true}, "text": "..."}],
 "dropped": 0, "criteria": {"approval_status": "APPROVED", "is_current": true}}
```

## Test case
1. Ingest chunks from sheet 02, approve one in the admin dashboard, leave the
   rest PENDING_REVIEW → retrieval returns ONLY the approved one.
2. Add a newer version of the same article → the old version (`is_current:
   false`) disappears from results.
