import AccessDenied from "@/components/dashboard/access-denied";
import OverviewClient from "@/components/dashboard/overview-client";
import { ADMIN_ONLY } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function AdminOverviewPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  const { ok } = await requireRoles([...ADMIN_ONLY]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return <OverviewClient locale={safeLocale} dict={dict} />;
}
