import ConversationsClient from "@/components/dashboard/conversations-client";
import AccessDenied from "@/components/dashboard/access-denied";
import { CITIZEN_ONLY } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function ConversationsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);
  const t = dict.dashboard.citizen;

  const { ok } = await requireRoles([...CITIZEN_ONLY]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return (
    <div className="space-y-6">
      <h1 className="page-title">{t.historyTitle}</h1>
      <ConversationsClient locale={safeLocale} dict={dict} />
    </div>
  );
}
