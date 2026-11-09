import { notFound, redirect } from "next/navigation";
import AccessDenied from "@/components/dashboard/access-denied";
import DashboardShell from "@/components/dashboard/shell";
import { createClient } from "@/lib/supabase/server";
import type { AppRole } from "@/lib/dashboard/nav";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

/**
 * Route protection (frontend side): the session is read from the verified
 * Supabase auth cookies — never from user input. Roles come from the
 * user_roles table through RLS-restricted queries. The backend layer
 * (FastAPI, Phase 4) re-checks everything server-side.
 */
export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) {
    notFound();
  }
  const dict = getDictionary(locale);

  const supabase = await createClient();
  if (!supabase) {
    redirect(`/${locale || defaultLocale}/login`);
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect(`/${locale}/login`);
  }

  const [profileResult, rolesResult] = await Promise.all([
    supabase.from("profiles").select("full_name, disabled").eq("id", user.id).single(),
    supabase.from("user_roles").select("role").eq("user_id", user.id),
  ]);

  const profile = profileResult.data;
  const roles = ((rolesResult.data ?? []) as { role: AppRole }[]).map((row) => row.role);
  const staffRoles = roles.filter((role) => role !== "VISITOR");
  const accessDenied = Boolean(profile?.disabled) || staffRoles.length === 0;

  const userName = profile?.full_name || user.email || "";

  return (
    <DashboardShell
      locale={locale}
      dict={dict}
      user={{ name: userName, email: user.email ?? "" }}
      roles={roles}
    >
      {accessDenied ? <AccessDenied locale={locale} dict={dict} /> : children}
    </DashboardShell>
  );
}
