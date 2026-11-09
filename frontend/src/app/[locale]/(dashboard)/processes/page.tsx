import { requireRoles } from "@/lib/dashboard/guard";
import { CITIZEN_ONLY } from "@/lib/dashboard/roles";
import { defaultLocale, isLocale, type Locale } from "@/lib/i18n/config";
import ProcessesClient from "@/components/dashboard/processes-client";

export default async function ProcessesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale: Locale = isLocale(locale) ? locale : defaultLocale;
  const { ok } = await requireRoles([...CITIZEN_ONLY]);
  if (!ok) {
    return <p className="card p-6">Accès restreint.</p>;
  }
  return <ProcessesClient locale={safeLocale} />;
}
