import AccessDenied from "@/components/dashboard/access-denied";
import WorkflowsClient from "@/components/dashboard/workflows-client";
import { ADMIN_ONLY } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function AdminWorkflowsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);
  const t = dict.dashboard.admin;

  const { ok } = await requireRoles([...ADMIN_ONLY]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return (
    <div className="space-y-6">
      <h1 className="page-title">{t.workflowsTitle}</h1>
      <WorkflowsClient locale={safeLocale} dict={dict} />
    </div>
  );
}
