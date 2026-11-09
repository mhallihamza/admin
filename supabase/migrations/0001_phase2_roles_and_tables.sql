-- ============================================================================
-- Phase 2 — roles, application tables, triggers, row-level security
-- All 12 application tables have RLS enabled. The FastAPI backend (Phase 4)
-- and scripts use the service role (bypasses RLS); browser clients are
-- restricted by the policies below.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Enumerations
-- ---------------------------------------------------------------------------
create type public.app_role as enum (
  'VISITOR',
  'CITIZEN',
  'EMPLOYEE',
  'CONTENT_APPROVER',
  'SYSTEM_ADMIN',
  'SECURITY_AUDITOR',
  'PLATFORM_SUPER_ADMIN'
);

create type public.document_status as enum (
  'UPLOADED',
  'PARSED',
  'PENDING_REVIEW',
  'APPROVED',
  'DISABLED'
);

create type public.review_case_status as enum (
  'OPEN',
  'IN_REVIEW',
  'APPROVED',
  'CORRECTED',
  'REJECTED',
  'TRANSFERRED'
);

create type public.risk_level as enum ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

create type public.message_role as enum ('USER', 'ASSISTANT', 'SYSTEM');

-- ---------------------------------------------------------------------------
-- Profiles
-- ---------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null unique,
  full_name text not null default '',
  locale text not null default 'fr' check (locale in ('fr', 'ar')),
  disabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- User roles
-- ---------------------------------------------------------------------------
create table public.user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  role public.app_role not null,
  granted_by uuid references auth.users (id),
  created_at timestamptz not null default now(),
  unique (user_id, role)
);

-- ---------------------------------------------------------------------------
-- Conversations and messages
-- ---------------------------------------------------------------------------
create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default '',
  locale text not null default 'fr' check (locale in ('fr', 'ar')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  role public.message_role not null,
  content text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Saved procedures
-- ---------------------------------------------------------------------------
create table public.saved_procedures (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  procedure_snapshot jsonb not null default '{}',
  created_at timestamptz not null default now(),
  unique (user_id, title)
);

-- ---------------------------------------------------------------------------
-- Review cases (human review handoff)
-- ---------------------------------------------------------------------------
create table public.review_cases (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references public.conversations (id) on delete set null,
  message_id uuid references public.messages (id) on delete set null,
  requested_by uuid references auth.users (id) on delete set null,
  question_summary text not null,
  proposed_answer text,
  legal_evidence jsonb not null default '[]',
  risk_level public.risk_level not null default 'LOW',
  status public.review_case_status not null default 'OPEN',
  assigned_to uuid references auth.users (id) on delete set null,
  service_name text,
  resolution_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Documents and document versions
-- ---------------------------------------------------------------------------
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  language text not null default 'fr' check (language in ('fr', 'ar')),
  status public.document_status not null default 'UPLOADED',
  uploaded_by uuid references auth.users (id) on delete set null,
  file_name text,
  file_size_bytes bigint,
  file_type text,
  page_count integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  version_number integer not null,
  file_path text,
  extracted_text text,
  effective_date date,
  end_date date,
  is_current boolean not null default true,
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now(),
  unique (document_id, version_number)
);

-- ---------------------------------------------------------------------------
-- Agent / tool permissions (checked by the backend tool gateway, Phase 4)
-- ---------------------------------------------------------------------------
create table public.agent_permissions (
  id uuid primary key default gen_random_uuid(),
  agent_key text not null,
  tool_key text not null,
  operation text not null,
  allowed boolean not null default false,
  updated_by uuid references auth.users (id) on delete set null,
  updated_at timestamptz not null default now(),
  unique (agent_key, tool_key, operation)
);

create table public.tool_permissions (
  id uuid primary key default gen_random_uuid(),
  tool_key text not null,
  role public.app_role not null,
  operation text not null,
  data_scope text not null default 'OWN',
  allowed boolean not null default false,
  updated_by uuid references auth.users (id) on delete set null,
  updated_at timestamptz not null default now(),
  unique (tool_key, role, operation, data_scope)
);

-- ---------------------------------------------------------------------------
-- Audit events and security incidents (written by backend / triggers only)
-- ---------------------------------------------------------------------------
create table public.audit_events (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users (id) on delete set null,
  actor_role public.app_role,
  action text not null,
  entity text not null,
  entity_id text,
  ip inet,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table public.security_incidents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  source_ip inet,
  attack_type text,
  risk_level public.risk_level,
  decision text check (decision in ('ALLOW', 'RESTRICT', 'REVIEW', 'BLOCK')),
  reason text not null default '',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Indexes for the access paths used by the dashboards
-- ---------------------------------------------------------------------------
create index idx_user_roles_user on public.user_roles (user_id);
create index idx_conversations_user on public.conversations (user_id);
create index idx_messages_conversation on public.messages (conversation_id);
create index idx_saved_procedures_user on public.saved_procedures (user_id);
create index idx_review_cases_status on public.review_cases (status);
create index idx_documents_status on public.documents (status);
create index idx_audit_events_created on public.audit_events (created_at desc);
create index idx_security_incidents_created on public.security_incidents (created_at desc);

-- ---------------------------------------------------------------------------
-- Helper: role check for policies (security definer avoids RLS recursion)
-- ---------------------------------------------------------------------------
create or replace function public.has_role(p_role public.app_role)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.user_roles ur
    where ur.user_id = auth.uid()
      and ur.role = p_role
  );
$$;

-- ---------------------------------------------------------------------------
-- Triggers
-- ---------------------------------------------------------------------------
-- 1) Every new auth user gets a profile and starts as CITIZEN.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', '')
  )
  on conflict (id) do nothing;

  insert into public.user_roles (user_id, role)
  values (new.id, 'CITIZEN')
  on conflict (user_id, role) do nothing;

  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

-- 2) Role grants/revokes are always written to the audit log.
create or replace function public.audit_user_role_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if (TG_OP = 'INSERT') then
    insert into public.audit_events (actor_id, action, entity, entity_id, metadata)
    values (
      auth.uid(),
      'ROLE_GRANTED',
      'user_roles',
      new.id::text,
      jsonb_build_object('user_id', new.user_id, 'role', new.role)
    );
    return new;
  elsif (TG_OP = 'DELETE') then
    insert into public.audit_events (actor_id, action, entity, entity_id, metadata)
    values (
      auth.uid(),
      'ROLE_REVOKED',
      'user_roles',
      old.id::text,
      jsonb_build_object('user_id', old.user_id, 'role', old.role)
    );
    return old;
  end if;
  return null;
end;
$$;

create trigger user_roles_audit
after insert or delete on public.user_roles
for each row
execute function public.audit_user_role_change();

-- ---------------------------------------------------------------------------
-- Row-level security — enabled on every application table
-- ---------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.saved_procedures enable row level security;
alter table public.review_cases enable row level security;
alter table public.documents enable row level security;
alter table public.document_versions enable row level security;
alter table public.agent_permissions enable row level security;
alter table public.tool_permissions enable row level security;
alter table public.audit_events enable row level security;
alter table public.security_incidents enable row level security;

-- profiles -------------------------------------------------------------------
create policy profiles_select_own_or_admin on public.profiles
  for select using (
    id = auth.uid()
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );

create policy profiles_update_own on public.profiles
  for update using (id = auth.uid());

create policy profiles_update_admin on public.profiles
  for update using (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  );

-- user_roles ------------------------------------------------------------------
create policy user_roles_select_own_or_admin on public.user_roles
  for select using (
    user_id = auth.uid()
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
    or public.has_role('SECURITY_AUDITOR')
  );

create policy user_roles_manage_admin on public.user_roles
  for insert with check (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  );

create policy user_roles_revoke_admin on public.user_roles
  for delete using (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  );

-- conversations ----------------------------------------------------------------
create policy conversations_all_own on public.conversations
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- messages ----------------------------------------------------------------------
create policy messages_all_own_conversation on public.messages
  for all using (
    exists (
      select 1 from public.conversations c
      where c.id = messages.conversation_id and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.conversations c
      where c.id = messages.conversation_id and c.user_id = auth.uid()
    )
  );

-- saved_procedures ----------------------------------------------------------------
create policy saved_procedures_all_own on public.saved_procedures
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- review_cases --------------------------------------------------------------------
create policy review_cases_select_participant_or_staff on public.review_cases
  for select using (
    requested_by = auth.uid()
    or public.has_role('EMPLOYEE')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );

create policy review_cases_insert_own on public.review_cases
  for insert with check (requested_by = auth.uid());

create policy review_cases_update_staff on public.review_cases
  for update using (
    public.has_role('EMPLOYEE')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );

-- documents / document_versions ------------------------------------------------------
create policy documents_select_staff on public.documents
  for select using (
    public.has_role('EMPLOYEE')
    or public.has_role('CONTENT_APPROVER')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
    or public.has_role('SECURITY_AUDITOR')
  );

create policy documents_manage_approvers on public.documents
  for all using (
    public.has_role('CONTENT_APPROVER')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  )
  with check (
    public.has_role('CONTENT_APPROVER')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );

create policy document_versions_select_staff on public.document_versions
  for select using (
    public.has_role('EMPLOYEE')
    or public.has_role('CONTENT_APPROVER')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
    or public.has_role('SECURITY_AUDITOR')
  );

create policy document_versions_manage_approvers on public.document_versions
  for all using (
    public.has_role('CONTENT_APPROVER')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  )
  with check (
    public.has_role('CONTENT_APPROVER')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );

-- agent_permissions / tool_permissions ---------------------------------------------
create policy agent_permissions_select_admin_or_auditor on public.agent_permissions
  for select using (
    public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
    or public.has_role('SECURITY_AUDITOR')
  );

create policy agent_permissions_manage_admin on public.agent_permissions
  for all using (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  )
  with check (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  );

create policy tool_permissions_select_admin_or_auditor on public.tool_permissions
  for select using (
    public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
    or public.has_role('SECURITY_AUDITOR')
  );

create policy tool_permissions_manage_admin on public.tool_permissions
  for all using (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  )
  with check (
    public.has_role('SYSTEM_ADMIN') or public.has_role('PLATFORM_SUPER_ADMIN')
  );

-- audit_events ----------------------------------------------------------------------
create policy audit_events_select_auditor_or_admin on public.audit_events
  for select using (
    public.has_role('SECURITY_AUDITOR')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );
-- No client insert/update/delete policies: the backend (service role) writes audit rows.

-- security_incidents ------------------------------------------------------------------
create policy security_incidents_select_auditor_or_admin on public.security_incidents
  for select using (
    public.has_role('SECURITY_AUDITOR')
    or public.has_role('SYSTEM_ADMIN')
    or public.has_role('PLATFORM_SUPER_ADMIN')
  );
-- No client write policies: the security gate (backend, Phase 4) writes incidents.
