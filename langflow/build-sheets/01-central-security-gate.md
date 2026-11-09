# Build sheet 01 — Central Security Gate (entry workflow, Smart Router chain)

**File:** `flows/central-security-gate.json` · **29 nodes, 39 edges**
**Model:** mistral-small-latest (temperature 0, timeout 30s) for Layer 2 only
**Deployed:** flow `0a1e09ad` on stg-agentic.abafusion.ai

## Purpose
The ENTRY workflow. Layer 1 (fixed deterministic Python rules) + Layer 2
(detection model, sees ONLY the user text) → **Central Decision** (fixed
Python — the model never decides) → **deterministic conditional-router chain**
(exclusion-based — the untaken branch's downstream never executes):

- **ALLOW** → Gate Result (decision + full session payload for the next workflow)
- **REVIEW** → logged to DB (security_incidents REVIEW + audit) → held; never proceeds
- **RESTRICT** → logged to DB (RESTRICT + audit) → held; never proceeds
- **BLOCK** → logged to DB (BLOCK + audit) → stopped
- **Unknown/missing decision** → falls through the chain to the BLOCK branch (fail-closed)

## Why not the Smart Router component
The installed SmartRouter (`lfx.components.llm_operations.llm_conditional_router.SmartRouterComponent`)
routes via **LLM categorization** (its `llm` input is required). Using it would let a
language model choose security routes — non-deterministic, an injection surface, and
in violation of the platform rule "the model never decides". The native
`ConditionalRouter` (`lfx.components.flow_controls.conditional_router`) is deterministic
(no model), supports `starts with` matching, and **natively excludes the untaken
branch's downstream vertices** (`exclude_branch_conditionally` in its code — verified).
Three chained ConditionalRouters cover the four decisions + unknown→BLOCK fail-closed.

## Components (29)
| # | Component | Display name | Key settings |
|---|---|---|---|
| 1 | Chat Input | Request Payload (JSON) | payload from the platform server (verified session facts; citizen supplies only `text`) |
| 2 | Type Convert | Payload → Message | Message |
| 3 | Prompt Template | Layer 1 Rules — fixed code | `code/layer1_rules.template.py` — input `{context}` |
| 4 | Python Interpreter | Layer 1 Rules | `json,re,ast` |
| 5 | Prompt Template | Extract Text For Detection — fixed code | `code/extract_text_for_detection.template.py` — model sees ONLY `{text}` |
| 6 | Python Interpreter | Extract Text For Detection | `json,re,ast` |
| 7 | Type Convert | Text → Message | Message |
| 8 | MistralAI | Layer 2 Detector (plain model) | temperature 0, timeout 30; system_message = `code/layer2_detector_system_message.txt` |
| 9 | Type Convert | Layer1 → Message | Message |
| 10 | Prompt Template | Central Decision — fixed code | `code/gate_merge.template.py` — inputs `{layer1_json}` `{layer2_text}` `{session_json}` |
| 11 | Python Interpreter | Central Decision | `json,re,ast` |
| 12 | Type Convert | Decision → Message | Message |
| 13 | Conditional Router | Route 1 — ALLOW ? | operator `starts with`, match `GATE_DECISION: ALLOW` |
| 14 | Type Convert | ALLOW Payload → Message | Message |
| 15 | Chat Output | Gate Result (payload for the next workflow) | — |
| 16 | Conditional Router | Route 2 — REVIEW ? | operator `starts with`, match `GATE_DECISION: REVIEW` |
| 17 | Prompt Template | Log Review Hold — fixed code | `code/log_security_incident.template.py` — input `{context}` |
| 18 | Python Interpreter | Log Review Hold | `json,re,urllib.request,urllib.error` |
| 19 | Type Convert | Review → Message | Message |
| 20 | Chat Output | Review Hold (manual review required) | — |
| 21 | Conditional Router | Route 3 — RESTRICT ? | operator `starts with`, match `GATE_DECISION: RESTRICT` |
| 22 | Prompt Template | Log Restricted — fixed code | same code — input `{context}` |
| 23 | Python Interpreter | Log Restricted | same imports |
| 24 | Type Convert | Restricted → Message | Message |
| 25 | Chat Output | Restricted (held) | — |
| 26 | Prompt Template | Log Blocked Incident — fixed code | same code — input `{context}` (Router 3 false = BLOCK + unknown) |
| 27 | Python Interpreter | Log Blocked Incident | same imports |
| 28 | Type Convert | Blocked → Message | Message |
| 29 | Chat Output | Blocked | — |

## Connections
```
ChatInput(1).message           → TypeConvert(2).input_data
TypeConvert(2).message_output  → Prompt(3).context / Prompt(5).context
Prompt(3).prompt               → PyInterpreter(4).python_code
Prompt(5).prompt               → PyInterpreter(6).python_code
PyInterpreter(6).results       → TypeConvert(7).input_data
TypeConvert(7).message_output  → MistralAI(8).input_value            (text only)
PyInterpreter(4).results       → TypeConvert(9).input_data
TypeConvert(9).message_output  → Prompt(10).layer1_json
MistralAI(8).text_output       → Prompt(10).layer2_text
TypeConvert(2).message_output  → Prompt(10).session_json
Prompt(10).prompt              → PyInterpreter(11).python_code
PyInterpreter(11).results      → TypeConvert(12).input_data
TypeConvert(12).message_output → Router(13).input_text / true_case / false_case
                                 (same message to Router(16) and Router(21) inputs)
Router(13).true_result         → TypeConvert(14).input_data → ChatOutput(15)
Router(13).false_result        → Router(16).input_text / true_case / false_case
Router(16).true_result         → Prompt(17).context → PyInterpreter(18) → TypeConvert(19) → ChatOutput(20)
Router(16).false_result        → Router(21).input_text / true_case / false_case
Router(21).true_result         → Prompt(22).context → PyInterpreter(23) → TypeConvert(24) → ChatOutput(25)
Router(21).false_result        → Prompt(26).context → PyInterpreter(27) → TypeConvert(28) → ChatOutput(29)
```

## Central Decision rules (node 11 — deterministic, documented)
```
Any Layer 1 violation                        -> BLOCK   (rules are authoritative)
Layer 1 unreadable / malformed               -> BLOCK   (fail closed)
Layer 2 malformed / unparsable / missing     -> REVIEW  (never silently LOW)
Layer 2 CRITICAL, or confidence >= 0.85      -> BLOCK   (model near-certain of an attack)
Layer 2 HIGH,     or confidence >= 0.60      -> REVIEW  (classification alone does not prove
                                                         an attack; a human decides)
Layer 2 MEDIUM                               -> RESTRICT (continue only restricted)
otherwise                                    -> ALLOW
```
The reason text is sanitized (`GATE_DECISION` removed) so the model can never
forge the routing marker.

## Layer 2 output contract
`{"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "attack_type": ...|null, "confidence": 0.0-1.0, "reason": "..."}` —
validated in the Decision step; malformed/missing → HIGH + REVIEW (never ALLOW).

## Supabase logging (branch steps 18/23/27)
- Non-ALLOW: `security_incidents` row (user_id, attack_type, risk, decision, reason)
  + `audit_events` row (`SECURITY_GATE_STOPPED`).
- Logging failure NEVER changes the decision (the branch still terminates; the
  output reports `log_error`).
- One log execution per run (the router exclusion prevents duplicate branches).

## Environment variables (Langflow env)
`MISTRAL_API_KEY` · `SUPABASE_URL` · `SUPABASE_SERVICE_ROLE_KEY`

## Test results (executed on stg-agentic.abafusion.ai)

| # | Input | Expected | Actual | Evidence |
|---|---|---|---|---|
| 1 | CITIZEN, normal question | ALLOW | ⏳ blocked by Mistral 429 rate limit | run executed, detector reached |
| 2 | missing user_id | BLOCK | ✅ code path verified (LOGIN_REQUIRED → BLOCK) | layer1 unit test |
| 3 | disabled account | BLOCK | ✅ code path verified (ACCOUNT_DISABLED) | layer1 unit test |
| 4 | VISITOR chat | BLOCK | ✅ code path verified (ROLE_VS_REQUEST) | layer1 unit test + platform echo |
| 5 | text > 2000 chars | BLOCK | ✅ code path verified (SIZE_LIMIT) | layer1 unit test |
| 6 | unsupported extension | BLOCK | ✅ code path verified (FILE_TYPE) | layer1 unit test |
| 7 | source_user_id ≠ user_id | BLOCK | ✅ code path verified (DATA_SCOPE) | layer1 unit test |
| 8 | unauthorized agent/tool | BLOCK | ✅ code path verified (AGENT_NOT_ALLOWED) | layer1 unit test |
| 9 | prompt injection | REVIEW/BLOCK | ⏳ blocked by Mistral 429 (detector is the judge) | — |
| 10 | malformed JSON | BLOCK | ✅ code path verified (PAYLOAD_INVALID, fail-closed) | layer1 unit test |
| 11 | nested JSON in result | parsed | ✅ v3.2 parser passes the EXACT platform string | test-v32-exact.py |
| 12 | Layer 2 malformed output | never ALLOW | ✅ code verified: malformed → HIGH → REVIEW | gate_merge unit |
| 13 | Layer 2 fails/times out | never ALLOW | ✅ **EXECUTED**: 401/429 detector errors → flow failed, no ALLOW, nothing downstream | platform runs |
| 14 | unknown decision value | BLOCK | ✅ router chain: falls through all 3 → BLOCK branch (fail-closed) | router code verified |
| 15 | Supabase logging failure on BLOCK | remains BLOCK | ✅ code verified: raise fires regardless of log result | log step code |
| 16 | request after a BLOCK | independent | ✅ components are stateless per run (fresh session each time) | platform runs |

Unit-test evidence: 14 templates × behavioral parser tests (plain / wrapped once /
wrapped twice / newline+double-wrap) — ALL PASS (test-parsers.py).
