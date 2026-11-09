// Ad-hoc verification queries for Phase 2 (tables, RLS, policies, seed).
import { makeClient } from "./db.mjs";

const c = makeClient();
await c.connect();

const tables = await c.query(`
  select c.relname as table, c.relrowsecurity as rls
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind = 'r'
  order by c.relname
`);
console.log(
  "tables:",
  tables.rows.map((r) => `${r.table}${r.rls ? "(RLS)" : "(NO RLS)"}`).join(", ")
);

const pol = await c.query(
  "select count(*) as n from pg_policies where schemaname = 'public'"
);
console.log("policies:", pol.rows[0].n);

const users = await c.query(`
  select p.email, p.full_name, p.disabled,
           coalesce(string_agg(ur.role::text, ', ' order by ur.role), '-') as roles
  from public.profiles p
  left join public.user_roles ur on ur.user_id = p.id
  group by p.id, p.email, p.full_name, p.disabled
  order by p.email
`);
console.log("seeded users:");
for (const u of users.rows) {
  console.log(`  - ${u.email} [${u.roles}] ${u.disabled ? "DISABLED" : ""}`);
}

const audits = await c.query(
  "select action, count(*) as n from public.audit_events group by action"
);
console.log("audit events:", audits.rows.map((r) => `${r.action}:${r.n}`).join(", ") || "none");

await c.end();
