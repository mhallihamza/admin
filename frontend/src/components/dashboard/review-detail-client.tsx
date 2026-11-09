"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Alert from "@/components/alert";
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

/**
 * Case detail: question, proposed answer, legal evidence, and the four
 * actions (Approve, Correct, Reject, Transfer to another service).
 * All actions persist and are audited through `/api/review-cases/{id}`.
 */
export default function ReviewDetailClient({
  locale,
  dict,
  caseId,
}: {
  locale: Locale;
  dict: Dictionary;
  caseId: string;
}) {
  const t = dict.dashboard.employee;
  const [row, setRow] = useState<ReviewCase | null>(null);
  const [note, setNote] = useState("");
  const [serviceName, setServiceName] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      if (!backendUrl) {
        if (!cancelled) setRow(null);
        return;
      }
      const headers = await backendAuthHeaders();
      if (!headers) {
        if (!cancelled) setRow(null);
        return;
      }
      try {
        const response = await fetch(`${backendUrl}/api/review-cases/${encodeURIComponent(caseId)}`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as ApiReviewCase;
        if (!cancelled) {
          setRow(normalize(body));
          setServiceName(body.service_name ?? "");
        }
      } catch {
        if (!cancelled) setRow(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  if (row === null) {
    return (
      <p className="card p-6 text-sm text-ink-secondary">
        {locale === "ar" ? "لم يتم العثور على هذا الملف." : "Ce dossier est introuvable."}
      </p>
    );
  }

  async function apply(
    status: ReviewCase["status"],
    options?: { requireNote?: boolean; service?: string }
  ) {
    setError(null);
    setFeedback(null);
    if (options?.requireNote && note.trim().length === 0) {
      setError(t.noteRequired);
      return;
    }
    if (status === "TRANSFERRED" && !(options?.service ?? serviceName).trim()) {
      setError(locale === "ar" ? "اختر جهة التحويل." : "Précisez la direction ou le service destinataire.");
      return;
    }

    setBusy(true);
    const headers = await backendAuthHeaders(true);
    if (!headers || !backendUrl) {
      setBusy(false);
      setError(locale === "ar" ? "الخدمة غير متاحة." : "Le service de revue est indisponible.");
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/review-cases/${encodeURIComponent(row!.id)}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({
          status,
          note: note.trim(),
          service_name: (options?.service ?? serviceName).trim(),
        }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
      const updated = (await response.json()) as ApiReviewCase;
      setRow(normalize(updated));
      setServiceName(updated.service_name ?? "");
      setNote("");
      setFeedback(t.actionDone);
    } catch (err) {
      setError(err instanceof Error ? err.message : (locale === "ar" ? "حدث خطأ." : "Action impossible."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link
        href={`/${locale}/review`}
        className="inline-block text-sm text-primary underline-offset-2 hover:underline"
      >
        ← {t.backToList}
      </Link>

      {feedback ? <Alert tone="success">{feedback}</Alert> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <div className="card p-6">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-lg font-semibold">{row.id}</span>
          <RiskBadge risk={row.risk} labels={t.risks} />
          <CaseStatusBadge status={row.status} labels={t.statuses} />
          {row.requestedBy ? <span className="text-sm text-ink-secondary">{row.requestedBy}</span> : null}
          <span className="text-sm text-ink-secondary">
            {t.colCreated} : {row.createdAt}
          </span>
        </div>

        <div className="mt-6">
          <h2 className="text-sm font-semibold">{t.questionLabel}</h2>
          <p className="mt-1 text-sm text-ink-secondary">{row.question}</p>
        </div>

        <div className="mt-5">
          <h2 className="text-sm font-semibold">{t.proposedAnswerLabel}</h2>
          <p className="mt-1 text-sm text-ink-secondary">{row.proposedAnswer || (locale === "ar" ? "لم ينتج المحرك جواباً معتمداً" : "Aucun élément de réponse officiel n'a été produit.")}</p>
        </div>

        <div className="mt-5">
          <h2 className="text-sm font-semibold">{t.evidenceLabel}</h2>
          {row.legalEvidence.length === 0 ? (
            <p className="mt-2 text-sm text-ink-secondary">—</p>
          ) : (
            <ul className="mt-2 space-y-1.5">
              {row.legalEvidence.map((item) => (
                <li
                  key={item}
                  className="rounded-md border border-stroke bg-background px-3 py-2 text-sm"
                >
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        {row.status === "TRANSFERRED" ? (
          <p className="mt-5 text-sm text-ink-secondary">
            {t.colService} : {row.serviceName}
          </p>
        ) : null}

        <div className="mt-6 border-t border-stroke pt-5">
          <h2 className="text-sm font-semibold">{t.actionsLabel}</h2>
          <div className="mt-3 max-w-xl">
            <label htmlFor="review-note" className="block text-sm font-medium">
              {t.noteLabel}
            </label>
            <textarea
              id="review-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className="input mt-1.5 min-h-20"
            />
            <p className="mt-1 text-xs text-ink-secondary">{t.noteRequired}</p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void apply("APPROVED")}>
              {t.approve}
            </button>
            <button
              type="button"
              className="btn-outline"
              disabled={busy}
              onClick={() => void apply("CORRECTED", { requireNote: true })}
            >
              {t.correct}
            </button>
            <button
              type="button"
              className="btn-outline"
              disabled={busy}
              onClick={() => void apply("REJECTED", { requireNote: true })}
            >
              {t.reject}
            </button>
          </div>

          <div className="mt-4 flex max-w-xl flex-wrap items-end gap-2">
            <div className="min-w-0 flex-1">
              <label htmlFor="review-service" className="block text-sm font-medium">
                {t.transferTo}
              </label>
              <input
                id="review-service"
                type="text"
                value={serviceName}
                onChange={(event) => setServiceName(event.target.value)}
                className="input mt-1.5"
              />
            </div>
            <button
              type="button"
              className="btn-outline"
              disabled={busy}
              onClick={() => void apply("TRANSFERRED", { service: serviceName })}
            >
              {t.transferConfirm}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
