"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface SavedProcedure {
  id: string;
  title: string;
  created_at?: string;
}

/** Saved procedures: read/delete from `/api/procedures/saved`. */
export default function SavedListClient({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.dashboard.citizen;
  const [items, setItems] = useState<SavedProcedure[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    if (!backendUrl) {
      setItems([]);
      return;
    }
    const headers = await backendAuthHeaders();
    if (!headers) {
      setItems([]);
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/procedures/saved`, { headers });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = (await response.json()) as { saved: SavedProcedure[] };
      setItems(body.saved || []);
    } catch {
      setItems([]);
      setError(t.savedEmpty);
    }
  }, [t.savedEmpty]);

  useEffect(() => {
    void load();
  }, [load]);

  async function remove(item: SavedProcedure) {
    if (!backendUrl) return;
    const headers = await backendAuthHeaders();
    if (!headers) return;
    try {
      const response = await fetch(`${backendUrl}/api/procedures/saved/${encodeURIComponent(item.id)}`, {
        method: "DELETE",
        headers,
      });
      if (!response.ok && response.status !== 204) throw new Error(`HTTP ${response.status}`);
      setItems((current) => (current ?? []).filter((saved) => saved.id !== item.id));
    } catch {
      setError(t.savedEmpty);
    }
  }

  if (items === null) {
    return <p className="card p-6 text-sm text-ink-secondary">…</p>;
  }
  if (items.length === 0) {
    return (
      <p className="card p-6 text-sm text-ink-secondary">{error ?? t.savedEmpty}</p>
    );
  }

  return (
    <>
      {error ? <p className="text-sm text-ink-secondary">{error}</p> : null}
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
            <Link href={`/${locale}/saved-procedures/${encodeURIComponent(item.id)}`} className="font-medium text-primary underline-offset-2 hover:underline">
              {item.title}
            </Link>
            <button type="button" className="btn-outline h-9 px-3 py-1" onClick={() => void remove(item)}>
              {locale === "ar" ? "حذف" : "Supprimer"}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
