"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { ConversationSummary } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface ApiConversation {
  id: string;
  title: string;
  updated_at?: string;
  updatedAt?: string;
  message_count?: number;
  messageCount?: number;
}

function normalize(row: ApiConversation): ConversationSummary {
  return {
    id: row.id,
    title: row.title,
    updatedAt: row.updatedAt ?? row.updated_at ?? "",
    messageCount: row.messageCount ?? row.message_count ?? 0,
  };
}

export default function ConversationsClient({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.dashboard.citizen;
  const [rows, setRows] = useState<ConversationSummary[] | null>(null);
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
        const response = await fetch(`${backendUrl}/api/conversations`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as { conversations?: ApiConversation[] };
        if (!cancelled) setRows((body.conversations || []).map(normalize));
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
        {error ? (locale === "ar" ? "تعذر تحميل سجل المحادثات." : "Le registre des conversations n'a pas pu être chargé.") : t.historyEmpty}
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {rows.map((conversation) => (
        <li key={conversation.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="font-medium">{conversation.title}</p>
            <p className="mt-1 text-sm text-ink-secondary">
              {t.updatedLabel} : {conversation.updatedAt} · {conversation.messageCount} {t.messagesLabel}
            </p>
          </div>
          <Link href={`/${locale}/chat?conversation=${encodeURIComponent(conversation.id)}`} className="btn-outline">
            {dict.dashboard.sidebar.items.chat}
          </Link>
        </li>
      ))}
    </ul>
  );
}
