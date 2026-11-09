"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/dashboard/badges";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { AuditEventRow, UserRow } from "@/lib/dashboard/api-types";
import type { AppRole } from "@/lib/dashboard/nav";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

const ALL_ROLES: AppRole[] = [
  "CITIZEN",
  "EMPLOYEE",
  "CONTENT_APPROVER",
  "SYSTEM_ADMIN",
  "SECURITY_AUDITOR",
  "PLATFORM_SUPER_ADMIN",
];

/** Users and roles: real admin endpoints, audited server-side. */
export default function UsersTableClient({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.dashboard.admin;
  const [rows, setRows] = useState<UserRow[] | null>(null);
  const [audit, setAudit] = useState<AuditEventRow[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftRole, setDraftRole] = useState<AppRole>("CITIZEN");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    if (!backendUrl) {
      setRows([]);
      setAudit([]);
      return;
    }
    const headers = await backendAuthHeaders();
    if (!headers) {
      setRows([]);
      setAudit([]);
      return;
    }
    try {
      const [usersResponse, auditResponse] = await Promise.all([
        fetch(`${backendUrl}/api/admin/users`, { headers }),
        fetch(`${backendUrl}/api/admin/audit-events?limit=6`, { headers }),
      ]);
      if (!usersResponse.ok) throw new Error(`HTTP ${usersResponse.status}`);
      const usersBody = (await usersResponse.json()) as { users?: UserRow[] };
      setRows(usersBody.users || []);
      if (auditResponse.ok) {
        const auditBody = (await auditResponse.json()) as { events?: AuditEventRow[] };
        setAudit(auditBody.events || []);
      }
    } catch {
      setRows([]);
      setError(locale === "ar" ? "تعذر تحميل المستخدمين." : "Impossible de charger les utilisateurs.");
    }
  }, [locale]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function saveRole(userId: string) {
    setBusy(true);
    setError(null);
    const headers = await backendAuthHeaders(true);
    if (!headers || !backendUrl) {
      setBusy(false);
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/admin/users/${encodeURIComponent(userId)}/role`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ role: draftRole }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
      setEditingId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.save);
    } finally {
      setBusy(false);
    }
  }

  async function toggleDisabled(row: UserRow) {
    setBusy(true);
    setError(null);
    const headers = await backendAuthHeaders(true);
    if (!headers || !backendUrl) {
      setBusy(false);
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/admin/users/${encodeURIComponent(row.id)}/disabled`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ disabled: !row.disabled }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.userDisable);
    } finally {
      setBusy(false);
    }
  }

  if (rows === null) return <p className="card p-6 text-sm text-ink-secondary">…</p>;

  return (
    <div className="space-y-6">
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b border-stroke text-xs uppercase tracking-wide text-ink-secondary">
              <th className="px-5 py-3 text-start font-semibold">{t.colEmail}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colName}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colRoles}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colState}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colActions}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-stroke last:border-0">
                <td className="px-5 py-3 font-medium">{row.email}</td>
                <td className="px-5 py-3">{row.fullName}</td>
                <td className="px-5 py-3">
                  {editingId === row.id ? (
                    <div className="flex items-center gap-2">
                      <select
                        aria-label={t.colRoles}
                        value={draftRole}
                        onChange={(event) => setDraftRole(event.target.value as AppRole)}
                        className="input h-9 w-44 py-1 text-sm"
                      >
                        {ALL_ROLES.map((role) => (
                          <option key={role} value={role}>
                            {dict.dashboard.roles[role] ?? role}
                          </option>
                        ))}
                      </select>
                      <button type="button" className="btn-primary h-9 px-3 py-1" disabled={busy} onClick={() => void saveRole(row.id)}>
                        {t.save}
                      </button>
                      <button
                        type="button"
                        className="btn-outline h-9 px-3 py-1"
                        onClick={() => setEditingId(null)}
                      >
                        {t.cancel}
                      </button>
                    </div>
                  ) : (
                    row.roles.map((role) => (
                      <Badge key={role} tone="info">
                        {dict.dashboard.roles[role] ?? role}
                      </Badge>
                    ))
                  )}
                </td>
                <td className="px-5 py-3">
                  {row.disabled ? (
                    <Badge tone="danger">{t.userDisabled}</Badge>
                  ) : (
                    <Badge tone="success">{t.active}</Badge>
                  )}
                </td>
                <td className="px-5 py-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn-outline h-9 px-3 py-1"
                      disabled={busy}
                      onClick={() => {
                        setEditingId(row.id);
                        setDraftRole(row.roles[0] ?? "CITIZEN");
                      }}
                    >
                      {t.changeRole}
                    </button>
                    <button
                      type="button"
                      className="btn-outline h-9 px-3 py-1"
                      disabled={busy}
                      onClick={() => void toggleDisabled(row)}
                    >
                      {row.disabled ? t.userEnable : t.userDisable}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card p-6">
        <h2 className="card-title">{t.auditRecent}</h2>
        <p className="mt-1 text-xs text-ink-secondary">{t.auditNote}</p>
        {audit.length === 0 ? (
          <p className="mt-4 text-sm text-ink-secondary">—</p>
        ) : (
          <ul className="mt-4 space-y-2">
            {audit.map((event) => (
              <li
                key={event.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-stroke bg-background px-3 py-2 text-sm"
              >
                <span className="font-medium">{event.action}</span>
                <span className="text-ink-secondary">{event.detail}</span>
                <span className="ms-auto text-xs text-ink-secondary">
                  {event.actor} · {event.createdAt}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
