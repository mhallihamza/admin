import AccessDenied from "@/components/dashboard/access-denied";
import SavedDetailClient from "@/components/dashboard/saved-detail-client";
import { CITIZEN_ONLY } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale, type Locale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function SavedProcedureDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const safeLocale: Locale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  const { ok } = await requireRoles([...CITIZEN_ONLY]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return <SavedDetailClient locale={safeLocale} dict={dict} savedId={decodeURIComponent(id)} />;
}
