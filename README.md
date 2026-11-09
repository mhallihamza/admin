# Administrative Guide (Guide Administratif / الدليل الإداري)

An e-government assistant platform for Morocco. Citizens ask questions about
administrative procedures and laws; answers come from **approved official
documents only**.

**Stack (fixed):** Next.js (App Router) + TypeScript + Tailwind CSS + Supabase
Auth (frontend) · FastAPI (backend, security gateway) · LangGraph
(workflow service, replaces Langflow 1.7) · Supabase Postgres + Astra DB +
Neo4j (data).

## Repository layout

```
S6/
├── frontend/    # Next.js app (Phase 1: landing + auth)
├── backend/     # FastAPI security gateway (Phase 4)
├── langflow/    # Langflow 1.7 workflows (reference — kept as source of truth)
├── langgraph/   # LangGraph workflow service (Phase 5: api.py + guide_graph/)
├── documents/   # Corpus officiel (PDFs sources de l'État FR/AR) + ingestion
├── security/    # Security rules and policies
├── docker/      # Local development compose files (later phases)
└── .env.example # Environment variable names only — never real keys
```

---

## Phase 1 — Landing page (public) + Login / Create account

### What was built

- **Landing page** (`/fr`, `/ar`) with, in order:
  1. Header 72 px (white, bottom border, logo + name, centered nav: Comment
     ça marche / Services / Sources / FAQ, language switcher, Log in outlined,
     Create account filled green) and the 3 px red accent line underneath.
     Collapses to a menu button below 1024 px.
  2. Hero, two columns: headline, subtitle, 56 px search field with green
     button, three clickable example chips; right: a static answer-preview
     card **clearly marked as sample data**, with three numbered steps and a
     Sources row with two official-source badges.
  3. "How it works": three numbered white cards.
  4. Services grid: 6 cards (3 columns desktop / 2 tablet / 1 mobile).
  5. "Official sources and trust" band: green background, white text,
     three points in a row.
  6. FAQ accordion: 6 sample questions (native `details/summary`,
     keyboard accessible).
  7. Footer: dark green 0B5D3B, four columns (platform, legal, contact,
     language) + copyright line.
- **Login** (`/fr/login`, `/ar/login`) and **Create account**
  (`/fr/register`, `/ar/register`): centered 420 px card, Supabase Auth
  (email + password), clear error states (wrong credentials, unconfirmed
  e-mail, password mismatch / too short, account exists, Supabase not
  configured).
- **i18n**: French and Arabic with full RTL support (`dir="rtl"`,
  Noto Sans Arabic for Arabic, Inter for French). Language switcher in every
  header. `middleware.ts` redirects `/` → `/fr` and prefixes all routes.
- **Design tokens** fixed in `frontend/tailwind.config.ts` and
  `frontend/src/app/globals.css` (colors 0B5D3B / C1272D / F7F8F6 / E3E7E2 /
  14201A / 5B6B62, status colors, 8 px / 6 px radii, no shadows except the
  mobile menu, 2 px green focus ring, no animations beyond 150 ms
  hover/focus).

### How to run

```bash
cd frontend
npm install
copy .env.example .env.local   # then fill the two values (see below)
npm run dev                    # http://localhost:3000
```

Production check (used during development of this phase):

```bash
cd frontend
npm run build && npm start
```

Environment variables (names only — values are never committed):
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

> Login/Create account work as soon as you put a Supabase project URL and
> its anon public key in `frontend/.env.local`. Without them, every page
> still renders and the auth forms show a clear configuration error instead
> of crashing.

### Verify in the browser (checklist)

- [ ] `/` redirects to `/fr`; switcher FR ⇄ عربي works from every page and
      keeps the current page.
- [ ] Arabic page is fully RTL (`<html lang="ar" dir="rtl">`), including the
      header order, hero alignment and footer.
- [ ] Header: 72 px, white, bottom border, 3 px red line underneath; nav
      links jump to How it works / Services / Sources / FAQ.
- [ ] Hero: 56 px search field + green button; example chips fill the field
      when clicked; preview card is labelled "sample data".
- [ ] Services grid: 3 columns at desktop, 2 at tablet (~768 px), 1 on
      mobile (~390 px); hero stacks with the preview card below on mobile.
- [ ] Header collapses to a menu button below ~1024 px; the menu opens with
      nav + language switcher + auth buttons.
- [ ] FAQ items open/close by keyboard (Tab + Enter).
- [ ] Focus ring (2 px green) is visible when tabbing through links/buttons.
- [ ] Login: wrong credentials show the red error alert; with Supabase
      configured, a valid account signs in and returns to the home page.
- [ ] Register: mismatched or short passwords show the inline errors; a
      successful signup shows the confirmation message (or signs you in if
      e-mail confirmation is disabled).

### Credentials needed for this phase

- A **Supabase project** (free tier is enough): provide the **Project URL**
  and **anon public key** so login/registration actually authenticate.
  Later phases will need: Supabase service-role key (backend only),
  Astra DB token + endpoint, Neo4j credentials, and an LLM API key
  (Mistral, matching the reference flows).

---

## Phase 2 — Roles and dashboard shell

### What was built

**Database (Supabase Postgres)** — `supabase/migrations/0001_phase2_roles_and_tables.sql`:

- Role enum: `VISITOR`, `CITIZEN`, `EMPLOYEE`, `CONTENT_APPROVER`,
  `SYSTEM_ADMIN`, `SECURITY_AUDITOR`, `PLATFORM_SUPER_ADMIN`.
- 12 application tables, **all with RLS enabled** (22 policies): profiles,
  user_roles, conversations, messages, saved_procedures, review_cases,
  documents, document_versions, agent_permissions, tool_permissions,
  audit_events, security_incidents.
- Triggers: every new auth user automatically gets a profile + the CITIZEN
  role; every role grant/revoke is written to `audit_events` automatically.
- Citizens read/write only their own conversations, messages and saved
  procedures; staff roles get review-case and document access;
  audit/security tables are read-only for auditors/admins and writable only
  by the backend (service role) — client-side write policies don't exist.

**Seed** — `supabase/seed/seed-users.mjs`: one auth user per role
(verified: 7 users + audit trail populated).

| E-mail | Role |
| --- | --- |
| visitor@demo.ma | VISITOR |
| citizen@demo.ma | CITIZEN |
| employee@demo.ma | EMPLOYEE |
| approver@demo.ma | CONTENT_APPROVER |
| admin@demo.ma | SYSTEM_ADMIN |
| auditor@demo.ma | SECURITY_AUDITOR |
| superadmin@demo.ma | PLATFORM_SUPER_ADMIN |

Password for every demo account (sample data — change before any real use):
`Demo2026!Guide`

**Frontend** — shared dashboard shell + route protection:

- `/fr|ar/dashboard` behind the `(dashboard)` route group: 260 px white
  sidebar with grouped navigation (active item = 3 px green start bar +
  light green background; flips correctly in RTL), 64 px top bar (page
  title, language switcher, notifications, user menu with roles + sign out),
  32 px content padding on F7F8F6.
- Sidebar shows 260 px ≥1024 px, icon rail 768–1023 px, drawer below 768 px.
- Navigation is filtered by the roles of the verified session (identity
  comes from the Supabase session cookie only — never user input). Phase 3
  sections are listed but rendered disabled.
- Guards: middleware refreshes the session; the dashboard layout redirects
  unauthenticated users to login and shows an "Access restricted" card for
  VISITOR-only or disabled accounts. The DB (RLS) is the backend-level
  protection until FastAPI takes over in Phase 4.

### How to run

```bash
# 1) Database (requires SUPABASE_DB_URL in the root .env.local)
cd supabase/tools && npm install && npm run migrate

# 2) Seed demo users (requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
cd ../seed && node seed-users.mjs

# 3) Frontend
cd ../../frontend && npm run dev
```

Useful check: `cd supabase/tools && node verify.mjs` prints tables/RLS
state, seeded users with roles, and audit-event counts.

### Verify in the browser (checklist)

- [x] `/fr/dashboard` redirects to the login page when signed out (307).
- [x] `supabase/tools/verify.mjs` shows 12 tables with RLS, 22 policies,
      7 users (one per role), and audit events for every role change.
- [x] All 7 demo accounts authenticate against Supabase Auth.
- [ ] With the anon key present: log in as `citizen@demo.ma` → dashboard
      shows only the citizen navigation; log in as `admin@demo.ma` → admin
      groups appear; `visitor@demo.ma` → "Access restricted" card;
      Arabic dashboard renders RTL with the sidebar on the right.

> Full dashboard-shell visual verification runs as soon as
> `NEXT_PUBLIC_SUPABASE_ANON_KEY` is set in `frontend/.env.local` (the
> login flow itself still works without it only after the key is added).

---

## Phase 3 — Dashboards (sample data behind a swappable data layer)

Every dashboard section below is built with **clearly marked sample data**
(each page shows a "Données d'exemple / بيانات توضيحية" badge) behind a
single data layer:

```
frontend/src/lib/data/
├── index.ts    # public contract — pages import only this
├── store.ts    # SWAP POINT: replaced by FastAPI calls in Phase 4
├── sample.ts   # locale-aware sample datasets (FR/AR), nothing is real
└── types.ts    # shared types
```

Section access is re-checked server-side on every page (`guard.ts` +
`roles.ts`): CITIZEN sees the citizen area; EMPLOYEE (+admins) the review
queue; CONTENT_APPROVER (+admins) document management; SYSTEM_ADMIN /
PLATFORM_SUPER_ADMIN the admin sections; SECURITY_AUDITOR / admins the
security page.

### Citizen dashboard
- `/fr|ar/chat`: chat panel (assistant messages start-aligned, user
  end-aligned), answer cards with **Steps, Required documents, Competent
  administration, Sources** sections and **Save procedure** / **Request
  human review** buttons; right column 320 px with suggested + saved
  procedures. Composer works in sample mode (assistant reply = explicit
  sample notice; no invented legal content).
- `/fr|ar/conversations`: conversation history list.
- `/fr|ar/saved-procedures`: saved procedures.

### Employee dashboard
- `/fr|ar/review`: cases table (case ID, question summary, risk badge,
  status badge, created date); row click opens the detail page.
- `/fr|ar/review/[id]`: question, proposed answer, legal evidence used, and
  the actions **Approve, Correct, Reject, Transfer to another service**
  (note required for correct/reject; status updates live in the queue).

### Admin dashboard (SYSTEM_ADMIN / PLATFORM_SUPER_ADMIN)
- `/fr|ar/admin/overview`: 4 KPI cards (users, requests today, blocked
  requests, workflow errors) + 2 simple charts (requests per day, blocked by
  attack type) — pure CSS bars, no animation, no chart library.
- `/fr|ar/admin/users`: users table with role change and disable/enable;
  every change is appended to the audit journal shown under the table.
- `/fr|ar/admin/documents`: drag-and-drop upload (PDF/DOCX/TXT, 20 MB limit
  displayed and enforced), documents table with status badges (Uploaded,
  Parsed, Pending review, Approved, Disabled), extracted-text preview side
  panel, and the actions **Send to indexing, Send to review, Approve,
  Reject, Disable, Retry**. Uploading never publishes a document.
- `/fr|ar/admin/permissions`: agents × tools matrix with Allow/Deny toggles
  (production storage: `agent_permissions` table).
- `/fr|ar/admin/workflows`: workflow executions with duration and status.

### Security (SECURITY_AUDITOR / SYSTEM_ADMIN / PLATFORM_SUPER_ADMIN)
- `/fr|ar/security`: incidents table, blocked requests list, red team
  reports, audit journal.
- **Citizen conversation content is hidden by default.** Revealing it
  requires a mandatory reason and writes
  `CONVERSATION_CONTENT_REVEALED — motif : …` to the audit journal.
- **SYSTEM_ADMIN does not see red team report details** (reserved to
  SECURITY_AUDITOR / PLATFORM_SUPER_ADMIN), per the access rules.

### Verify in the browser (checklist)

- [ ] Citizen (`citizen@demo.ma`): chat panel renders the sample answer
      card; Save procedure adds it to the saved list; history and saved
      pages work; Arabic is RTL (assistant bubbles mirrored).
- [ ] Employee (`employee@demo.ma`): queue table with risk/status badges;
      detail page actions change the status; note required for
      correct/reject.
- [ ] Approver (`approver@demo.ma`): sidebar shows ONLY document
      management; upload rejects a .exe (renamed) and a >20 MB file; the
      status pipeline works; preview panel shows extracted text.
- [ ] Admin (`admin@demo.ma`): KPIs + charts; role change/disable writes an
      audit line; permissions toggles flip; workflows table shows
      durations/statuses; security page hides red team details.
- [ ] Auditor (`auditor@demo.ma`): security page only in the sidebar;
      reveal requires a reason and logs the access; red team details visible.
- [ ] Visitor (`visitor@demo.ma`): "Access restricted" card on /dashboard;
      direct URLs to /review, /documents, /admin/* show the same card.

---

## Phase 4 — Backend (FastAPI security gateway)

The backend is the ONLY entry point to data and tools. It lives in
`backend/` (FastAPI + psycopg pool + PyJWT) with its own venv. Databases
are never exposed to clients.

```
backend/app/
├── main.py            # app factory, CORS, /api/health, /api/docs
├── config.py          # env-only settings (root .env.local)
├── db.py              # psycopg pool (service connection, audited writes)
├── auth.py            # Supabase token verification + current-user + roles
├── permissions.py     # tool/agent permission lookups (swap point for tests)
├── gateway.py         # short-lived agent tokens + per-call re-validation
├── security_gate.py   # Layer 1 fixed rules + Layer 2 hook; backend decides
├── rate_limit.py      # in-memory sliding window (per user/IP, per scope)
├── uploads.py         # magic-byte type check, size/page limits, scan hook
├── audit.py           # audit_events + security_incidents writers
└── routers/           # me, chat, documents, tools, security
```

### Endpoints

| Endpoint | What it does |
| --- | --- |
| `GET /api/health` | liveness |
| `GET /api/me` | identity + roles from the verified token |
| `POST /api/chat/message` | citizen chat entry: rate limit → security gate → accept/flag/block |
| `POST /api/documents/upload` | CONTENT_APPROVER+: magic-byte check (PDF/DOCX/TXT), 20 MB, 300 pages, malware hook; row starts UPLOADED (never published) |
| `POST /api/gateway/token` | issues a 60 s agent token AFTER checking tool_permissions + agent_permissions; denials audited (`AGENT_TOKEN_DENIED`) |
| `POST /api/tools/vector-retrieval` \| `graph-retrieval` \| `document-index` \| `human-handoff` | one endpoint per tool; requires user token **and** `X-Agent-Token`; re-checks user, role, agent, tool, operation, data scope; denials audited (`TOOL_DENIED`) |
| `POST /api/security/gate` | central gate: Layer 1 fixed rules (login state, role vs request type, size, file type, foreign user data, agent allow-list) + Layer 2 detection hook (Langflow in Phase 5). **The final allow/restrict/review/block decision is backend code, never the model**; non-allow decisions land in `security_incidents` |

### Automated tests (25, offline — no Supabase needed)

```bash
cd backend
py -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest
```

Covered: unauthorized role access (401/403, disabled accounts), tool call
by an agent that is not allowed (403 + audit), oversized / fake-extension /
binary-renamed / too-many-pages uploads (413/415), rate limiting (429 +
Retry-After), expired/foreign agent tokens, security-gate decisions.

### Live check

```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --port 8100
# then: GET /api/health, GET /api/me with a Supabase access token
```

Verified against the live project: real tokens resolve roles from the DB,
citizen upload → 403, approver upload → 201 with a real `documents` row,
`SUPERVISOR × DOCUMENT_INDEX` denied + audited, issued agent token (60 s)
calls the tool successfully, visitor at the gate → BLOCK recorded in
`security_incidents`.

Credentials needed for this phase: none beyond Phase 2 (service role key
and DB URL, server-side only). The malware scan hook activates when
`MALWARE_SCAN_URL` is set; the Layer 2 detection hook when
`LANGGRAPH_SECURITY_GATE_URL` is set (Phase 5).

---

## Phase 5 — LangGraph workflow service

The nine Langflow workflows have been rebuilt on **LangGraph** as a
standalone service (`langgraph/`, same shape as a sibling project's
`workflow/` folder: `api.py` + `guide_graph/` package). The backend talks to
it over HTTP exactly the way it used to talk to Langflow:

- `POST {LANGGRAPH_SECURITY_GATE_URL}` (i.e. `/run/detect`) — Layer 2
  detection (same payload/response contract as the Langflow flow 01);
- `POST {LANGGRAPH_BASE_URL}/run/pipeline` — after an ALLOW: flows
  06 → 07 → 09 (supervisor → answer validation → execution logging).

The workflows keep the same behaviour as the Langflow build sheets:

1. **Central Security Gate** (`nodes/gate.py`) — layer1 rules → layer2
   detector → deterministic decision; non-ALLOW writes the incident
   (fail-closed: malformed detector output ⇒ REVIEW `DETECTOR_MALFORMED`,
   transport failure ⇒ REVIEW `DETECTOR_FAILURE` — never a silent ALLOW).
2. **Document ingestion** (`nodes/ingestion.py`) — clean → text security
   check → split by legal article (FR/AR) → Astra `admin_guide_chunks`,
   always `PENDING_REVIEW`.
3. **Graph population** (`nodes/population.py`) — LLM extraction → strict
   schema whitelist → fixed parameterized MERGE (Neo4j), double-checked by
   validator and writer.
4. **Vector retrieval** (`nodes/retrieval.py`) — APPROVED + `is_current`
   chunks only.
5. **Graph retrieval** (`nodes/graph_retrieval.py`) — four fixed read-only
   Cypher templates; unknown template ⇒ `unknown template` error, raw
   Cypher from user text is never executed.
6. **Supervisor + specialists** (`nodes/supervisor.py`) — deterministic
   intent routing and FIXED gateway payloads (the model never composes what
   is sent): `VECTOR_RETRIEVAL` (top_k 6), `GRAPH_RETRIEVAL`,
   `DOCUMENT_INDEX`; two-step gateway calls (60 s agent token after
   permission checks). Answers are tagged `[PROCEDURE_AGENT]`,
   `[LEGAL_RESEARCH_AGENT]` or `[DOCUMENT_ADMIN_AGENT]` on the first line.
7. **Answer validation** (`nodes/validation.py`) — deterministic; zero
   citations or a citation not backed by an APPROVED current chunk ⇒ the
   answer is withheld (`REVIEW`).
8. **Human review handoff** (`nodes/handoff.py`) — via the gateway
   (`HUMAN_HANDOFF`, `SUPERVISOR`).
9. **Execution logging** (`nodes/execution_log.py`) — `POST
   /api/logs/execution` → `audit_events`.

### How to run / test (offline — no credentials needed)

```bash
cd langgraph
..\backend\.venv\Scripts\python.exe -m pytest            # 72 offline tests
..\backend\.venv\Scripts\python.exe scripts\run_gate.py  # gate CLI
..\backend\.venv\Scripts\python.exe scripts\redteam.py   # red-team cases
..\backend\.venv\Scripts\python.exe -m uvicorn api:app --port 8101  # service
```

The tests use a fake detector, a mock backend gateway (`httpx.MockTransport`
with the permission matrix) and in-memory stores; nothing external is
contacted. The 72 tests cover the gate red team (visitor/foreign data/
file types/injection/fail-closed), ingestion (PENDING_REVIEW, injection
rejected, nothing stored), population whitelist, retrieval filtering,
fixed templates, gateway contracts, validation withholding, handoff and
the HTTP API.

### Live verification (2026-11-08, real `MISTRAL_API_KEY` + Astra + Supabase)

- `scripts\redteam.py`: **9/9 cases conform** — layer-1 attacks BLOCK
  (detector not even consulted), prompt-injection cases detected live
  (`PROMPT_INJECTION`, `ROLE_ESCALATION`) and BLOCK/REVIEW, never ALLOW.
- Backend ↔ service integration: `POST /api/security/gate` — clean citizen
  question → `ALLOW` (real Layer-2 LOW), injection → `BLOCK`
  (`PROMPT_INJECTION`, 0.9); `GET /api/me` → 200 with DB roles.
- Gate incident write → `security_incidents` 201 (real user uuid),
  audit marker best-effort.
- **Full pipeline end-to-end (real answer)**: dedicated Astra database
  (the shared one had hit the 100-index serverless cap — the `$vector`
  index could not be created there). Sample official document ingested
  (`scripts/sample_document.py` → 5 chunks `PENDING_REVIEW`), approved,
  then the citizen question through `POST /api/chat/message`: gate ALLOW →
  PROCEDURE specialist → 2-step gateway → vector retrieval (Article 2
  ranked first) → cited answer, citation validated against the APPROVED
  chunk (`doc-demo-cnie-001, article 2, version 1`).
- Fail-closed checks along the way: with the vector store unreachable the
  answer was withheld (`review`), and the Phase-4 tool stubs were wired to
  the service (`backend/app/routers/tools.py`) — retrievals proxy to the
  LangGraph service, document-index reads the `documents` table,
  human-handoff creates a `review_cases` (OPEN) row + audit event.
- **Graph flows 03/05 live on Neo4j Aura Free** (2026-11-08): population
  wrote 6 nodes + `REQUIRES` relations with fixed parameterized MERGEs;
  the `procedure_requirements` template returned the real graph records;
  a raw-Cypher request (`DETACH DELETE`) was refused (`unknown template`)
  with the graph untouched. Two Aura-specific fixes landed in
  `guide_graph/tools/neo4j_store.py`: TLS anchored on the `certifi` bundle
  (the Windows system store lacks Aura's SSL.com root — `neo4j+s://` is
  downgraded to `neo4j://` + explicit context, encryption unchanged) and
  `NEO4J_DATABASE` is honoured (Aura Free names the database after the
  instance). Also fixed there: relation sources `LABEL:name` are stripped
  to the node name before the `MATCH` (latent reference bug — nodes are
  keyed by name only).
- Neo4j note: on this machine run the service with
  `OPENBLAS_NUM_THREADS=1` (low free RAM otherwise aborts the import).

Credentials that unlock the live behaviour: `MISTRAL_API_KEY`
(detector + specialists + embeddings), `ASTRA_DB_APPLICATION_TOKEN` +
`ASTRA_DB_API_ENDPOINT` (vector store), `NEO4J_PASSWORD` (+ URI/username)
(graph store), `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (gate incident
writes from the workflow service). Langflow-era flows and build sheets are
kept untouched under `langflow/` as the authoritative reference.

---

## Phase 5 (legacy reference) — Langflow 1.7 workflows

> Superseded by the LangGraph service above; kept untouched as the
> authoritative build reference (prompts, test cases, tool contracts).

See **`langflow/README.md`** for the full guide. Each of the nine workflows
has an **importable JSON** in `langflow/flows/`, an authoritative **build
sheet** in `langflow/build-sheets/` (components, settings, connections, I/O
JSON, test case), and its **fixed code** in `langflow/code/`:

1. **Central Security Gate** — Layer 1 fixed Python rules + Layer 2 detection
   model (no tools). The final decision is made by the backend only.
2. **Document ingestion** — Read File → clean → security check of extracted
   text → split by legal article/section → Astra DB with metadata; always
   `PENDING_REVIEW` (ingestion never publishes).
3. **Graph population** — entity/relation extraction validated against the
   allowed schema → Neo4j with fixed parameterized MERGE queries only.
4. **Vector retrieval** — Astra DB restricted to APPROVED + current chunks.
5. **Graph retrieval** — fixed read-only Cypher templates with bound
   parameters; queries are never built from user text.
6. **Supervisor** — one supervisor agent understands the client's intent and
   calls the dedicated specialist **flow** via native RunFlow tools
   (Procedure / Legal research / Document & administration, flows 06a–06c);
   every tool call goes through the backend gateway, which first issues a
   short-lived agent token after checking the permission tables.
7. **Answer validation** — deterministic: every citation must exist, be
   APPROVED and current. No model involved.
8. **Human review handoff** — through the gateway (`HUMAN_HANDOFF`).
9. **Execution logging** — into the existing `audit_events` table via
   `POST /api/logs/execution` (new backend endpoint, 27/27 tests pass).

Flows follow the reference architecture (Prompt Template "code wrapper" →
Python Interpreter) so that all data-processing code is fixed, never
model-generated. Regenerate with `node langflow/tools/generate-flows.mjs`.
