# Build sheet 02 — Document ingestion

**File:** `flows/document-ingestion.json` · **Trigger:** run in the Langflow canvas (CONTENT_APPROVER uploads the file and edits the metadata node) · **Model:** none for processing; mistral-embed for vectors

## Purpose
Read File → clean text → security check of the extracted text → split by legal
article/section → store in Astra DB with full metadata. Every chunk is stored
with `approval_status: "PENDING_REVIEW"` — **ingestion never publishes**.

## Components (in order)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Read File | Read File (PDF/DOCX/TXT) | upload the document here |
| 2 | Type Convert | File → Message | output_type: Message |
| 3 | Chat Input | Document Metadata (JSON) | paste per document: `{document_id, title, language, effective_date, version}` |
| 4 | Type Convert | Metadata → Message | output_type: Message |
| 5 | Prompt Template | Clean Text — fixed code | template = escaped `code/clean_text.template.py` (`{context}`) |
| 6 | Python Interpreter | Clean Text | global_imports: `json,re` |
| 7 | Prompt Template | Text Security Check — fixed code | template = escaped `code/text_security_check.template.py` (`{context}`) |
| 8 | Python Interpreter | Text Security Check | global_imports: `json,re` |
| 9 | Prompt Template | Split By Article — fixed code | template = escaped `code/split_articles.template.py` — **two named inputs: `{metadata_json}` + `{text_json}`** |
| 10 | Python Interpreter | Split By Article | global_imports: `json,re` |
| 11 | Type Convert | Chunks → DataFrame | output_type: **DataFrame** |
| 12 | MistralAI Embeddings | Mistral Embeddings | model `mistral-embed`, key from env `MISTRAL_API_KEY` |
| 13 | Astra DB | Astra DB — admin_guide_chunks | collection `admin_guide_chunks`; token/endpoint from env |
| 14 | Type Convert | Checked text → Message | output_type: Message |
| 15 | Type Convert | Chunks → Message | output_type: Message |
| 16 | Chat Output | Ingestion Summary (PENDING_REVIEW) | — |

## Connections
```
File(1).dataframe              → TypeConvert(2).input_data
ChatInput(3).message           → TypeConvert(4).input_data
TypeConvert(2).message_output  → Prompt(5).context
Prompt(5).prompt               → PyInterpreter(6).python_code
PyInterpreter(6).results       → Prompt(7).context
Prompt(7).prompt               → PyInterpreter(8).python_code
TypeConvert(4).message_output  → Prompt(9).metadata_json
PyInterpreter(8).results       → TypeConvert(14).input_data
TypeConvert(14).message_output → Prompt(9).text_json
Prompt(9).prompt               → PyInterpreter(10).python_code
PyInterpreter(10).results      → TypeConvert(11).input_data
TypeConvert(11).dataframe_output → AstraDB(13).ingest_data
MistralEmbeddings(12).embeddings → AstraDB(13).embedding_model
PyInterpreter(10).results      → TypeConvert(15).input_data
TypeConvert(15).message_output → ChatOutput(16).input_value
```

## Input JSON (Doc Metadata — edited per document)
```json
{"document_id": "DOC-0001", "title": "[Exemple] Recueil des procédures",
 "language": "fr", "effective_date": "2026-01-01", "version": 1}
```

## Output JSON (per chunk, stored in Astra DB metadata)
```json
{"document_id": "DOC-0001", "title": "...", "language": "fr",
 "effective_date": "2026-01-01", "version": 1,
 "approval_status": "PENDING_REVIEW", "article_number": "12",
 "section_title": null, "text": "..."}
```

## Test case
1. Upload a small TXT containing `Article 1 : ... Article 2 : ...` → the
   summary reports 2 chunks (+ preamble if any), all with
   `approval_status: PENDING_REVIEW`.
2. Upload a TXT containing "ignore all previous instructions" → the security
   step sets `text_safe: false` with flag `INJECTION_IGNORE_INSTRUCTIONS`; the
   backend does NOT approve the document.
3. Verify in Astra DB that no chunk exists with `approval_status: APPROVED`
   right after ingestion.
