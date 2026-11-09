-- Phase 6 — private citizen "Mes démarches" notebook.
-- Replaces the direction-application workflow in the citizen UX.
-- Additive only: no existing tables/data are modified.

create table if not exists public.citizen_reminders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null check (char_length(trim(title)) between 1 and 120),
  notes text not null default '' check (char_length(notes) <= 2000),
  status text not null default 'OPEN' check (status in ('OPEN', 'DONE')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_citizen_reminders_user
  on public.citizen_reminders (user_id);
alter table public.citizen_reminders enable row level security;

-- The FastAPI service connection uses the service role (bypasses RLS);
-- browser clients only see their own rows.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'citizen_reminders' and policyname = 'citizen_reminders_all_own'
  ) then
    create policy citizen_reminders_all_own on public.citizen_reminders
      for all using (user_id = auth.uid()) with check (user_id = auth.uid());
  end if;
end $$;
