import { createClient } from "@/lib/supabase/server";
import type { AppRole } from "@/lib/dashboard/nav";

/**
 * Server-side role check for dashboard sections. Roles always come from the
 * verified session (auth cookies) joined with user_roles through RLS.
 */
export async function getSessionRoles(): Promise<AppRole[]> {
  const supabase = await createClient();
  if (!supabase) return [];
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return [];
  const { data } = await supabase.from("user_roles").select("role").eq("user_id", user.id);
  return ((data ?? []) as { role: AppRole }[]).map((row) => row.role);
}

export async function requireRoles(allowed: AppRole[]) {
  const roles = await getSessionRoles();
  return { roles, ok: allowed.some((role) => roles.includes(role)) };
}
