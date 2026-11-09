-- Phase 4 — default tool/agent permission seed (deny by default; only
-- explicit rows below are allowed). The backend tool gateway reads these.

insert into public.tool_permissions (tool_key, role, operation, data_scope, allowed) values
  ('VECTOR_RETRIEVAL',  'CITIZEN',             'execute', 'OWN',  true),
  ('GRAPH_RETRIEVAL',   'CITIZEN',             'execute', 'OWN',  true),
  ('HUMAN_HANDOFF',     'CITIZEN',             'execute', 'OWN',  true),
  ('DOCUMENT_INDEX',    'CONTENT_APPROVER',    'execute', 'ALL',  true),
  ('DOCUMENT_INDEX',    'SYSTEM_ADMIN',        'execute', 'ALL',  true),
  ('DOCUMENT_INDEX',    'PLATFORM_SUPER_ADMIN','execute', 'ALL',  true),
  ('SECURITY_GATE',     'SYSTEM_ADMIN',        'execute', 'ALL',  true),
  ('SECURITY_GATE',     'PLATFORM_SUPER_ADMIN','execute', 'ALL',  true)
on conflict (tool_key, role, operation, data_scope) do nothing;

insert into public.agent_permissions (agent_key, tool_key, operation, allowed) values
  ('SUPERVISOR',           'HUMAN_HANDOFF',    'execute', true),
  ('PROCEDURE_AGENT',      'VECTOR_RETRIEVAL', 'execute', true),
  ('PROCEDURE_AGENT',      'GRAPH_RETRIEVAL',  'execute', true),
  ('PROCEDURE_AGENT',      'HUMAN_HANDOFF',    'execute', true),
  ('LEGAL_RESEARCH_AGENT', 'VECTOR_RETRIEVAL', 'execute', true),
  ('LEGAL_RESEARCH_AGENT', 'GRAPH_RETRIEVAL',  'execute', true),
  ('DOCUMENT_ADMIN_AGENT', 'DOCUMENT_INDEX',   'execute', true),
  ('DETECTION_AGENT',      'SECURITY_GATE',    'execute', true)
on conflict (agent_key, tool_key, operation) do nothing;
