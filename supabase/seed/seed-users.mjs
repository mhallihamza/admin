// Seeds one Supabase Auth user per role (Phase 2).
// Uses the Admin API with the service-role key — server-side only.
// Idempotent: re-running updates the same users instead of duplicating.
//
// Demo credentials (sample data, for local development only):
//   password for every seeded account: Demo2026!Guide
import { loadRootEnv } from "../tools/db.mjs";

const env = loadRootEnv();
const SUPABASE_URL = env.SUPABASE_URL;
const SERVICE_KEY = env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SERVICE_KEY) {
  throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing in .env.local");
}

const DEMO_PASSWORD = "Demo2026!Guide";

const seedUsers = [
  { email: "citizen@demo.ma", role: "CITIZEN", fullName: "Salma Citizen" },
  { email: "employee@demo.ma", role: "EMPLOYEE", fullName: "Youssef Employee" },
  { email: "admin@demo.ma", role: "SYSTEM_ADMIN", fullName: "Karim Admin" },
  { email: "auditor@demo.ma", role: "SECURITY_AUDITOR", fullName: "Hind Auditor" },
  { email: "superadmin@demo.ma", role: "PLATFORM_SUPER_ADMIN", fullName: "Omar Super Admin" },
];

function headers(extra = {}) {
  return {
    apikey: SERVICE_KEY,
    Authorization: `Bearer ${SERVICE_KEY}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function findUserByEmail(email) {
  const res = await fetch(
    `${SUPABASE_URL}/auth/v1/admin/users?per_page=200`,
    { headers: headers() }
  );
  if (!res.ok) throw new Error(`admin list failed: ${res.status} ${await res.text()}`);
  const body = await res.json();
  return (body.users || []).find((u) => u.email === email) || null;
}

async function createUser({ email, fullName }) {
  const res = await fetch(`${SUPABASE_URL}/auth/v1/admin/users`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      email,
      password: DEMO_PASSWORD,
      email_confirm: true,
      user_metadata: { full_name: fullName },
    }),
  });
  if (res.ok) {
    const body = await res.json();
    return body;
  }
  const text = await res.text();
  if (res.status === 422 || /already/i.test(text)) {
    const existing = await findUserByEmail(email);
    if (existing) return existing;
  }
  throw new Error(`create ${email} failed: ${res.status} ${text}`);
}

async function setRole(userId, role) {
  // Reset to exactly the target role (the signup trigger adds CITIZEN by default).
  const del = await fetch(
    `${SUPABASE_URL}/rest/v1/user_roles?user_id=eq.${userId}`,
    { method: "DELETE", headers: headers() }
  );
  if (!del.ok) throw new Error(`role reset failed: ${del.status} ${await del.text()}`);

  const ins = await fetch(`${SUPABASE_URL}/rest/v1/user_roles`, {
    method: "POST",
    headers: headers({ Prefer: "return=minimal" }),
    body: JSON.stringify({ user_id: userId, role }),
  });
  if (!ins.ok) throw new Error(`role insert failed: ${ins.status} ${await ins.text()}`);
}

async function updateProfile(userId, fullName) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/profiles?id=eq.${userId}`, {
    method: "PATCH",
    headers: headers({ Prefer: "return=minimal" }),
    body: JSON.stringify({ full_name: fullName }),
  });
  if (!res.ok) throw new Error(`profile update failed: ${res.status} ${await res.text()}`);
}

for (const spec of seedUsers) {
  const user = await createUser(spec);
  await setRole(user.id, spec.role);
  await updateProfile(user.id, spec.fullName);
  console.log(`+ ${spec.email} -> ${spec.role}`);
}

console.log(`\nSeed complete (${seedUsers.length} users). Password: ${DEMO_PASSWORD}`);
