"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface SavedSnapshot {
  answer?: string;
  citations?: { document_id?: string; article_number?: string; version?: string }[];
  conversation_id?: string;
  [key: string]: unknown;
}

interface SavedItem {
  id: string;
  title: string;
  snapshot: SavedSnapshot;
  created_at?: string;
}

function cleanMarkers(text: string) {
  return text.replace(/^\s*\[(?:PROCEDURE|LEGAL_RESEARCH|DOCUMENT_ADMIN|SUPERVISOR|DETECTION)_AGENT\]\s*\n?/gim, "");
}

export default function SavedDetailClient({
  locale,
  dict,
  savedId,
}: {
  locale: Locale;
  dict: Dictionary;
  savedId: string;
}) {
  const [item, setItem] = useState<SavedItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      if (!backendUrl) {
        setError(locale === "ar" ? "الخدمة غير متاحة." : "Le service n'est pas configuré.");
        setItem(null);
        return;
      }
      const headers = await backendAuthHeaders();
      if (!headers) {
        setError(locale === "ar" ? "الجلسة منتهية." : "Votre session a expiré.");
        return;
      }
      try {
        const response = await fetch(`${backendUrl}/api/procedures/saved/${encodeURIComponent(savedId)}`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as { saved: SavedItem };
        if (!cancelled) setItem(body.saved);
      } catch {
        if (!cancelled) setError(locale === "ar" ? "تعذر تحميل هذا العنصر." : "Impossible de charger cette procédure.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [locale, savedId]);

  return (
    <div className="space-y-6">
      <Link href={`/${locale}/saved-procedures`} className="inline-block text-sm text-primary underline-offset-2 hover:underline">
        ← {dict.dashboard.citizen.savedTitle}
      </Link>

      {error && <p className="card p-6 text-sm text-danger">{error}</p>}
      {!error && !item && <p className="card p-6 text-sm text-ink-secondary">…</p>}
      {item && (
        <article className="card p-6">
          <h1 className="text-xl font-semibold">{item.title}</h1>
          {item.created_at && (
            <p className="mt-1 text-xs text-ink-secondary">{item.created_at.slice(0, 16).replace("T", " ")}</p>
          )}
          <div className="mt-4 whitespace-pre-wrap border-t border-stroke pt-4 text-sm text-ink">
            {cleanMarkers(item.snapshot.answer ?? JSON.stringify(item.snapshot, null, 2))}
          </div>
          {item.snapshot.conversation_id && (
            <div className="mt-6 border-t border-stroke pt-4">
              <Link
                href={`/${locale}/chat?conversation=${encodeURIComponent(item.snapshot.conversation_id)}`}
                className="btn-outline"
              >
                {locale === "ar" ? "فتح المحادثة الأصلية" : "Ouvrir la conversation d'origine"}
              </Link>
            </div>
          )}
        </article>
      )}
    </div>
  );
}
