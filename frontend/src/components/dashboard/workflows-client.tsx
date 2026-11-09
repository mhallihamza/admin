"use client";

import { useEffect, useState } from "react";
import { WfStatusBadge } from "@/components/dashboard/badges";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { WorkflowExecution } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Admin workflow executions, read from real WORKFLOW_EXECUTION audit rows. */
export default function WorkflowsClient({ locale, dict }: { locale: Locale; dict: Dictionary }) {
  const t = dict.dashboard.admin;
  const [rows, setRows] = useState<WorkflowExecution[] | null>(null);
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
        const response = await fetch(`${backendUrl}/api/admin/workflows`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as { workflows?: WorkflowExecution[] };
        if (!cancelled) setRows(body.workflows || []);
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

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-danger">{locale === "ar" ? "تعذر تحميل سجلات سير العمل." : "Les exécutions n'ont pas pu être chargées."}</p>}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-stroke text-xs uppercase tracking-wide text-ink-secondary">
              <th className="px-5 py-3 text-start font-semibold">{t.colWorkflow}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colStarted}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colDuration}</th>
              <th className="px-5 py-3 text-start font-semibold">{t.colWfStatus}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-5 py-6 text-ink-secondary" colSpan={4}>—</td>
              </tr>
            ) : null}
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-stroke last:border-0">
                <td className="px-5 py-3 font-medium">{row.workflow}</td>
                <td className="px-5 py-3 text-ink-secondary">{row.startedAt}</td>
                <td className="px-5 py-3 text-ink-secondary">
                  {row.durationMs < 1000
                    ? `${row.durationMs} ms`
                    : `${(row.durationMs / 1000).toFixed(1)} s`}
                </td>
                <td className="px-5 py-3">
                  <WfStatusBadge status={row.status} labels={t.wfStatuses} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
