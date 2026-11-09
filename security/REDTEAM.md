# Red team / Blue team — Central Security Gate (Phase 5, LangGraph)

The attack cases below are enforced **as automated offline tests**. Every
case is verified in two places: the LangGraph gate tests (`langgraph/tests/`)
and the backend gate (`backend/app/security_gate.py`, same Layer-1 rules).

## Attack cases → tests

| Attack scenario | Layer / rule | LangGraph test | Expected |
| --- | --- | --- | --- |
| Visitor tries to chat | L1 `ROLE_VS_REQUEST` | `tests/test_gate_red_team.py::test_visitor_chat_blocked_role_vs_request` | BLOCK + incident |
| No authenticated session | L1 `LOGIN_REQUIRED` | `…::test_missing_user_id_blocked_login_required` | BLOCK |
| Disabled account | L1 `ACCOUNT_DISABLED` | `…::test_disabled_account_blocked` | BLOCK |
| Forged role value (`SUPERHACKER`) | L1 `ROLE_STRUCTURE_INVALID` | `…::test_unknown_role_blocked_role_structure` | BLOCK |
| Unknown request type | L1 `REQUEST_TYPE_INVALID` | `…::test_unknown_request_type_blocked` | BLOCK |
| Oversized payload (> 2000 chars) | L1 `SIZE_LIMIT` | `…::test_oversized_text_blocked_size_limit` | BLOCK |
| Executable renamed / no extension | L1 `FILE_TYPE` | `…::test_executable_file_blocked_file_type`, `…::test_extension_less_filename_blocked` | BLOCK |
| Foreign user's data (`source_user_id`) | L1 `DATA_SCOPE` | `…::test_foreign_data_scope_blocked` | BLOCK |
| Agent/tool not in permission tables | L1 `AGENT_NOT_ALLOWED` | `…::test_non_allowed_agent_blocked` | BLOCK (403 `AGENT_TOKEN_DENIED` at gateway: `tests/test_supervisor.py::test_denied_agent_tool_combo_gets_403`) |
| Malformed / non-JSON payload | L1 fail-closed | `…::test_malformed_json_payload_blocked_fail_closed`, `…::test_missing_text_blocked_fail_closed` | BLOCK |
| Direct prompt injection ("ignore previous instructions") | L2 detector | `…::test_prompt_injection_high_confidence_blocked` (confidence ≥ 0.85 ⇒ BLOCK; HIGH ⇒ REVIEW) | REVIEW/BLOCK |
| Role escalation ("you are now an admin") | L2 detector | same tests, scripted HIGH/CRITICAL | REVIEW/BLOCK |
| Detector returns garbage | L2 fail-closed | `…::test_detector_malformed_output_never_allows` | REVIEW (`DETECTOR_MALFORMED`) |
| Detector transport failure | L2 fail-closed | `…::test_detector_failure_fail_closed_to_review` | REVIEW (`DETECTOR_FAILURE`) |
| Detector tries to forge `GATE_DECISION` in `reason` | L2 output sanitization | `…::test_detector_reason_cannot_forg_gate_marker` | marker stripped, REVIEW |
| Confidentiality: no incident on clean traffic | audit discipline | `…::test_citizen_normal_question_allowed` (incident None) | ALLOW, nothing logged |

## Gateway & agents (blue team)

| Threat | Enforcement point | Test |
| --- | --- | --- |
| Model composes the tool payload | Fixed payloads in `nodes/supervisor.py` (model never builds them) | `test_procedure_specialist_uses_fixed_vector_payload`, `test_tool_call_payloads_are_deterministic_end_to_end` |
| Agent token replay / wrong tool | gateway re-validation + `X-Agent-Token` | `test_handoff_denied_when_token_for_other_tool` (403) |
| Ingestion tries to publish or smuggle instructions | text security check + `PENDING_REVIEW` always | `tests/test_ingestion.py::test_ingestion_graph_rejects_injected_text_and_stores_nothing` |
| RAG answers from unapproved content | APPROVED + `is_current` filter | `tests/test_retrieval.py` |
| Cypher injection / reading anything | 4 fixed read-only templates | `tests/test_graph_retrieval.py::test_unknown_template_never_executes_cypher` |
| Hallucinated legal citations | deterministic citation check, answer withheld | `tests/test_validation.py`, `tests/test_pipeline.py::test_answer_with_unbacked_citation_withheld` |
| Success-path logging forge | endpoint whitelist of `status` values | `test_execution_log_rejects_invalid_status` |

## Runner

```bash
cd langgraph
..\backend\.venv\Scripts\python.exe -m pytest                            # 80+ tests green
..\backend\.venv\Scripts\python.exe -m pytest tests/test_extended_red_team.py -q
..\backend\.venv\Scripts\python.exe scripts\redteam.py                 # 45 deterministic cases, writes reports + DB

cd ..\backend
.venv\Scripts\python.exe -m pytest tests/test_extended_red_team.py -q     # backend mirror
```

By default `redteam.py` uses a deterministic Layer-2 double so CI/local runs are reliable and free. Set `REDTEAM_LIVE=1` to exercise the configured Mistral detector. Layer-2 detections are not a substitute for L1 SQL/PPI/token controls; the report proves both layers.

All decisions are taken by deterministic backend/workflow code — never by
the model. In production, Layer 2 needs `MISTRAL_API_KEY` on the workflow
service; without it the layer is skipped with an explicit
"not connected" placeholder (Layer-1-only parity with Phase 4).
