import AccessDenied from "@/components/dashboard/access-denied";
import ReviewTableClient from "@/components/dashboard/review-table-client";
import { REVIEW_STAFF } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function ReviewQueuePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  const { ok } = await requireRoles([...REVIEW_STAFF]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return (
    <div className="space-y-6">
      <h1 className="page-title">{dict.dashboard.employee.queueTitle}</h1>
      <ReviewTableClient locale={safeLocale} dict={dict} />
    </div>
  );
}
