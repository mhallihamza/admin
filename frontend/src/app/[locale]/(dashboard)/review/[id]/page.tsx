import AccessDenied from "@/components/dashboard/access-denied";
import ReviewDetailClient from "@/components/dashboard/review-detail-client";
import { REVIEW_STAFF } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function ReviewCaseDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  const { ok } = await requireRoles([...REVIEW_STAFF]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return (
    <div className="space-y-6">
      <h1 className="page-title">{dict.dashboard.employee.detailTitle}</h1>
      <ReviewDetailClient locale={safeLocale} dict={dict} caseId={decodeURIComponent(id)} />
    </div>
  );
}
