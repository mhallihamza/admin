"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { Locale } from "@/lib/i18n/config";

interface ReminderRow {
  id: string;
  title: string;
  notes: string;
  status: "OPEN" | "DONE";
  createdAt: string;
  updatedAt: string;
}

/**
 * "Mes démarches" — private citizen notebook. No CNIE/passport application
 * is submitted or processed here; it is only a place to remember a démarche,
 * its context and whether you handled it.
 */
export default function ProcessesClient({ locale }: { locale: Locale }) {
  const isAr = locale === "ar";
  const [items, setItems] = useState<ReminderRow[] | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
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
      const response = await fetch(`${backendUrl}/api/reminders`, { headers });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = (await response.json()) as { reminders?: ReminderRow[] };
      setItems(body.reminders || []);
    } catch {
      setItems([]);
      setError(isAr ? "تعذر تحميل المساطر الخاصة بك." : "Impossible de charger vos démarches.");
    }
  }, [isAr]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleaned = title.trim();
    if (!cleaned || busy || !backendUrl) return;
    setBusy(true);
    setError(null);
    const headers = await backendAuthHeaders(true);
    if (!headers) {
      setBusy(false);
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/reminders`, {
        method: "POST",
        headers,
        body: JSON.stringify({ title: cleaned, notes: notes.trim() }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
      setTitle("");
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : (isAr ? "تعذر الحفظ." : "Impossible d'enregistrer."));
    } finally {
      setBusy(false);
    }
  }

  async function toggleDone(item: ReminderRow) {
    if (!backendUrl) return;
    const headers = await backendAuthHeaders(true);
    if (!headers) return;
    const status = item.status === "DONE" ? "OPEN" : "DONE";
    setItems((current) => (current ?? []).map((row) =>
      row.id === item.id ? { ...row, status, updatedAt: new Date().toISOString() } : row
    ));
    try {
      const response = await fetch(`${backendUrl}/api/reminders/${encodeURIComponent(item.id)}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await load();
    } catch {
      setError(isAr ? "تعذر تحديث التذكير." : "Impossible de mettre à jour ce rappel.");
      await load();
    }
  }

  async function deleteReminder(item: ReminderRow) {
    if (!backendUrl) return;
    const headers = await backendAuthHeaders();
    if (!headers) return;
    try {
      const response = await fetch(`${backendUrl}/api/reminders/${encodeURIComponent(item.id)}`, {
        method: "DELETE",
        headers,
      });
      if (response.status !== 204 && !response.ok) throw new Error(`HTTP ${response.status}`);
      setItems((current) => (current ?? []).filter((row) => row.id !== item.id));
    } catch {
      setError(isAr ? "تعذر حذف التذكير." : "Impossible de supprimer ce rappel.");
    }
  }

  if (items === null) return <p className="card p-6 text-sm text-ink-secondary">…</p>;

  return (
    <div className="space-y-6">
      <section className="card p-6">
        <h2 className="card-title">
          {isAr ? "مذكرتي للإجراء الإداري" : "Mémo de ma démarche"}
        </h2>
        <p className="mt-1 text-sm text-ink-secondary">
          {isAr
            ? "منصة تذكير خاصة بك: سجل ما تريد فعله أو الوثائق/الأسئلة المتبقية. لا تقدم هنا طلب CNIE أو جواز سفر ولا تمرره للإدارة."
            : "Un mémo privé pour vous rappeler votre démarche (informations, documents, questions à revoir). Ici, vous ne déposez pas de demande CNIE ou passeport."}
        </p>

        <form onSubmit={createReminder} className="mt-4 flex max-w-2xl flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-secondary">{isAr ? "ما الذي تذكّر به؟" : "À quoi voulez-vous vous rappeler ?"}</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={120}
              required
              className="input"
              placeholder={isAr ? "مثال: الوثائق التي أحتاجها لشهادة التوريث" : "Ex. : les documents pour mon dossier"}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-secondary">{isAr ? "ملاحظة (اختياري)" : "Note (facultative)"}</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              maxLength={2000}
              className="input min-h-20"
              placeholder={isAr ? "مثال: اتصلت بالبلدية، أحصل على النسخة الأصلية أولاً…" : "Ex. : j'ai appelé la mairie, il manque la copie originale…"}
            />
          </label>
          <button type="submit" disabled={busy} className="btn-primary h-11 self-start px-5">
            {busy ? "…" : isAr ? "حفظ" : "Enregistrer"}
          </button>
        </form>
        {error && <p className="mt-3 text-sm text-danger">{error}</p>}
      </section>

      <section className="space-y-3">
        <h2 className="card-title">{isAr ? "ملاحظاتي / مساطري" : "Mes démarches"}</h2>
        {items.length === 0 ? (
          <p className="card p-4 text-sm text-ink-secondary">
            {isAr ? "لا توجد حتى الآن. احفظ أول مذكرة." : "Aucune démarche notée pour le moment."}
          </p>
        ) : null}
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="card p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${item.status === "DONE" ? "text-ink-secondary line-through" : ""}`}>
                    {item.title}
                  </p>
                  {item.notes ? <p className="mt-1 whitespace-pre-wrap text-sm text-ink-secondary">{item.notes}</p> : null}
                  <p className="mt-2 text-xs text-ink-secondary">
                    {item.status === "DONE" ? (isAr ? "منجزة" : "Terminée") : (isAr ? "قيد التذكر" : "À retenir")} · {item.updatedAt?.slice(0, 16).replace("T", " ")}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <button type="button" className="btn-outline h-9 px-3 py-1" onClick={() => void toggleDone(item)}>
                    {item.status === "DONE" ? (isAr ? "ملاحظة" : "Rouvrir") : (isAr ? "تم" : "Terminé")}
                  </button>
                  <button type="button" className="btn-outline h-9 px-3 py-1" onClick={() => void deleteReminder(item)}>
                    {isAr ? "حذف" : "Supprimer"}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
