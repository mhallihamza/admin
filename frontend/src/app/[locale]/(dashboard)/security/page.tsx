import AccessDenied from "@/components/dashboard/access-denied";
import SecurityClient from "@/components/dashboard/security-client";
import { RED_TEAM_DETAIL_ROLES, SECURITY_STAFF } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

/**
 * Security & audit. Access rules from the spec:
 * - SECURITY_AUDITOR: full access (incidents, blocked requests, red team details).
 * - SYSTEM_ADMIN: sees incidents and blocked requests but NOT red team details,
 *   and can never see citizen conversation content without a recorded reason.
 * - PLATFORM_SUPER_ADMIN: full access.
 */
export default async function SecurityPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  const { roles, ok } = await requireRoles([...SECURITY_STAFF]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  const canViewRedTeamDetails = roles.some((role) =>
    RED_TEAM_DETAIL_ROLES.includes(role)
  );

  return (
    <div className="space-y-6">
      <h1 className="page-title">{dict.dashboard.security.title}</h1>
      <SecurityClient
        locale={safeLocale}
        dict={dict}
        canViewRedTeamDetails={canViewRedTeamDetails}
      />
    </div>
  );
}
