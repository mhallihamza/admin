"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CaseStatusBadge, RiskBadge } from "@/components/dashboard/badges";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { ReviewCase, ReviewStatus, RiskLevel } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface ApiReviewCase {
  id: string;
  question_summary?: string;
  question?: string;
  proposed_answer?: string;
  legal_evidence?: string[];
  risk?: RiskLevel;
  status?: ReviewStatus;
  service_name?: string;
  requested_by?: string;
  created_at?: string;
}

function normalize(row: ApiReviewCase): ReviewCase {
  return {
    id: row.id,
    questionSummary: row.question_summary ?? "",
    question: row.question ?? row.question_summary ?? "",
    proposedAnswer: row.proposed_answer ?? "",
    legalEvidence: row.legal_evidence ?? [],
    risk: row.risk ?? "LOW",
    status: row.status ?? "OPEN",
    serviceName: row.service_name ?? "",
    requestedBy: row.requested_by ?? "",
    createdAt: row.created_at ?? "",
  };
}

/** Review queue: cases needing human review (real `/api/review-cases`). */
export default function ReviewTableClient({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.dashboard.employee;
  const [rows, setRows] = useState<ReviewCase[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(false);
      if (!backendUrl) {
        if (!cancelled) setRows([]);
        return;
      }
      const headers = await backendAuthHeaders();
      if (!headers) {
        if (!cancelled) setRows([]);
        return;
      }
      try {
        const response = await fetch(`${backendUrl}/api/review-cases`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as { review_cases?: ApiReviewCase[] };
        if (!cancelled) setRows((body.review_cases || []).map(normalize));
      } catch {
        if (!cancelled) {
          setRows([]);
          setError(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (rows === null) return <p className="card p-6 text-sm text-ink-secondary">…</p>;
  if (rows.length === 0) {
    return (
      <p className="card p-6 text-sm text-ink-secondary">
        {error ? (locale === "ar" ? "تعذر تحميل القائمة." : "La file de revue n'a pas pu être chargée.") : "—"}
      </p>
    );
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[720px] text-start text-sm">
        <thead>
          <tr className="border-b border-stroke text-start text-xs uppercase tracking-wide text-ink-secondary">
            <th className="px-5 py-3 text-start font-semibold">{t.colId}</th>
            <th className="px-5 py-3 text-start font-semibold">{t.colQuestion}</th>
            <th className="px-5 py-3 text-start font-semibold">{t.colRisk}</th>
            <th className="px-5 py-3 text-start font-semibold">{t.colStatus}</th>
            <th className="px-5 py-3 text-start font-semibold">{t.colCreated}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-stroke transition-colors duration-150 last:border-0 hover:bg-primary-light/40"
            >
              <td className="px-5 py-3 font-medium">
                <Link
                  href={`/${locale}/review/${encodeURIComponent(row.id)}`}
                  className="text-primary underline-offset-2 hover:underline"
                >
                  {row.id}
                </Link>
              </td>
              <td className="px-5 py-3">
                {row.questionSummary}
                {row.requestedBy ? (
                  <p className="mt-1 text-xs font-normal text-ink-secondary">{row.requestedBy}</p>
                ) : null}
              </td>
              <td className="px-5 py-3">
                <RiskBadge risk={row.risk} labels={t.risks} />
              </td>
              <td className="px-5 py-3">
                <CaseStatusBadge status={row.status} labels={t.statuses} />
              </td>
              <td className="px-5 py-3 text-ink-secondary">{row.createdAt}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
