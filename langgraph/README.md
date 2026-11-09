# langgraph/ — Guide Administratif workflow service

Standalone **LangGraph + FastAPI** service that replaces the Langflow 1.7
workflows (kept untouched in `../langflow/` as the reference). Same shape
as the soukna project's `workflow/` folder:

```
langgraph/
├── api.py                  # HTTP service (FastAPI) — what the backend calls
├── guide_graph/
│   ├── state.py            # shared state (WorkflowState TypedDict)
│   ├── config.py           # env-only settings (langgraph/.env + root .env.local)
│   ├── llm.py              # Mistral factory + heuristic fallback (no key = fail-safe)
│   ├── prompts.py          # fixed prompt texts (verbatim from langflow templates)
│   ├── graph.py            # master chat graph + standalone graphs
│   ├── tracing.py          # per-node timings (observable, no external service)
│   ├── nodes/              # one module per workflow (01→09)
│   └── tools/              # gateway client, Astra, Neo4j, incidents
├── tests/                  # 72 offline tests (no external service contacted)
├── scripts/                # run_gate.py, run_pipeline.py, redteam.py
├── requirements.txt · pyproject.toml · Dockerfile · .env.example
```

## The nine workflows (mirror of `../langflow/build-sheets/`)

| # | Langflow flow | Module | Guarantees kept |
| --- | --- | --- | --- |
| 01 | Central Security Gate | `nodes/gate.py` | layer1 rules → layer2 detector → deterministic decision; fail-closed (`DETECTOR_MALFORMED`/`DETECTOR_FAILURE` ⇒ REVIEW, never silent ALLOW); non-ALLOW writes the incident |
| 02 | Document ingestion | `nodes/ingestion.py` | clean → text security check → legal-article split (FR/AR) → Astra `admin_guide_chunks`, always `PENDING_REVIEW` |
| 03 | Graph population | `nodes/population.py` | extraction → strict schema whitelist → fixed parameterized MERGE only (validator + writer double-check) |
| 04 | Vector retrieval | `nodes/retrieval.py` | APPROVED + `is_current` chunks only |
| 05 | Graph retrieval | `nodes/graph_retrieval.py` | 4 fixed read-only Cypher templates; unknown template ⇒ outright error |
| 06 | Supervisor + specialists | `nodes/supervisor.py` | intent routing + FIXED gateway payloads (top_k 6, etc.); 2-step gateway token (60 s); agent markers on line 1 |
| 07b | Output safety filter | `nodes/output_filter.py` | scans final text for env assignments, control tokens, internal instructions, internal routes; final fail-closed judge/LLM (`REDTEAM_LIVE` unaffected but final graph always runs it) |
| 07 | Answer validation | `nodes/validation.py` | deterministic; zero/unbacked citation ⇒ answer withheld (REVIEW) |
| 08 | Human review handoff | `nodes/handoff.py` | via gateway (`HUMAN_HANDOFF`, `SUPERVISOR`) |
| 09 | Execution logging | `nodes/execution_log.py` | `POST /api/logs/execution` → `audit_events` |

## HTTP API (backend ↔ service)

| Endpoint | Purpose |
| --- | --- |
| `GET /health` · `GET /info` | liveness, readiness + workflow list |
| `POST /run/detect` | **Layer 2 only** — the exact Langflow contract `{text, request_type, user_id, filename}` → `{risk_level, attack_type, confidence, reason}`. The backend calls this from `security_gate.py` |
| `POST /run/security-gate` | full gate graph (layer1 + layer2 + decision + incident) |
| `POST /run/pipeline` | full chat pipeline: gate → supervisor → validation → log |
| `POST /run/ingestion` \| `/run/population` \| `/run/vector-retrieval` \| `/run/graph-retrieval` \| `/run/handoff` \| `/run/log-execution` | standalone flows 02–05, 08, 09 |
| `POST /run/ingest-file` | **flow 02 by file**: PDF (typed text or scan) or image → OCR (Tesseract fra/ara) → clean → split → Astra `PENDING_REVIEW`. 20 MB / 300 pages, magic-byte check |
| `POST /run/validate-answer` | flow 07 in isolation (citation extraction) |

Auth: `X-Flow-Token: $FLOW_TOKEN` (empty ⇒ open, dev-only).

## Run / test

All offline tests pass with **zero credentials** (heuristic mode: empty
`MISTRAL_API_KEY` ⇒ fake detector, mock gateway, in-memory stores):

```bash
cd langgraph
C:\Users\PC\Desktop\S6\backend\.venv\Scripts\python.exe -m pytest    # 72 passed
C:\Users\PC\Desktop\S6\backend\.venv\Scripts\python.exe scripts\run_gate.py
C:\Users\PC\Desktop\S6\backend\.venv\Scripts\python.exe scripts\redteam.py
C:\Users\PC\Desktop\S6\backend\.venv\Scripts\python.exe -m uvicorn api:app --port 8101
```

Wired on the backend side by three env vars (see `../.env.example`):

```
LANGGRAPH_SECURITY_GATE_URL=http://localhost:8101/run/detect
LANGGRAPH_BASE_URL=http://localhost:8101
LANGGRAPH_FLOW_TOKEN=
```

## Credentials needed to go live

| Variable | Unlocks |
| --- | --- |
| `MISTRAL_API_KEY` | real Layer-2 detector, specialist answers, embeddings (until then: heuristic fail-safe answers only) |
| `ASTRA_DB_APPLICATION_TOKEN` + `ASTRA_DB_API_ENDPOINT` | real vector store (collection `admin_guide_chunks`) |
| `NEO4J_URI` + `NEO4J_USERNAME` + `NEO4J_PASSWORD` | graph population (03) and graph retrieval (05) |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | direct incident writes by the gate (flow 01) |

Nothing else is required; `supabase/`, `backend/` secrets stay server-side.
