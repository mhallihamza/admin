"use client";

import { useEffect, useState } from "react";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { PermissionEntry } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Agents × tools matrix backed by agent_permissions via /api/admin/permissions. */
export default function PermissionsClient({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.dashboard.admin;
  const [rows, setRows] = useState<PermissionEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
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
        const response = await fetch(`${backendUrl}/api/admin/permissions`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as { permissions?: PermissionEntry[] };
        if (!cancelled) setRows(body.permissions || []);
      } catch {
        if (!cancelled) {
          setRows([]);
          setError(locale === "ar" ? "تعذر تحميل الصلاحيات." : "Impossible de charger les permissions.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [locale]);

  async function toggle(row: PermissionEntry) {
    setError(null);
    if (!backendUrl) return;
    const headers = await backendAuthHeaders(true);
    if (!headers) return;
    const next = !row.allowed;
    setRows((current) => (current ?? []).map((item) =>
      item.id === row.id ? { ...item, allowed: next } : item
    ));
    try {
      const response = await fetch(`${backendUrl}/api/admin/permissions`, {
        method: "PUT",
        headers,
        body: JSON.stringify({
          agent: row.agent,
          tool: row.tool,
          operation: row.operation,
          allowed: next,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch {
      setRows((current) => (current ?? []).map((item) =>
        item.id === row.id ? { ...item, allowed: row.allowed } : item
      ));
      setError(locale === "ar" ? "تعذر تحديث الصلاحية." : "La permission n'a pas pu être enregistrée.");
    }
  }

  if (rows === null) return <p className="card p-6 text-sm text-ink-secondary">…</p>;

  return (
    <div className="space-y-4">
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-stroke text-xs uppercase tracking-wide text-ink-secondary">
              <th className="px-5 py-3 text-start font-semibold">{t.colAgent}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colTool}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colOperation}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colAllowed}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-stroke last:border-0">
                <td className="px-5 py-3 font-medium">{row.agent}</td>
                <td className="px-5 py-3">{row.tool}</td>
                <td className="px-5 py-3 text-ink-secondary">{row.operation}</td>
                <td className="px-5 py-3">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={row.allowed}
                    onClick={() => void toggle(row)}
                    className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors duration-150 ${
                      row.allowed ? "border-success bg-success" : "border-stroke bg-background"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-all ${
                        row.allowed ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                    <span className="sr-only">{row.allowed ? t.allow : t.deny}</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
