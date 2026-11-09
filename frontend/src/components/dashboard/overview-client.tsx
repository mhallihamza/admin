"use client";

import { useEffect, useState } from "react";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { Kpis, AttackType } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Overview KPIs loaded from the backend's real audit/incident counters. */
export default function OverviewClient({ locale, dict }: { locale: Locale; dict: Dictionary }) {
  const t = dict.dashboard.admin;
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(false);
      if (!backendUrl) {
        if (!cancelled) setKpis({ users: 0, requestsToday: 0, blockedRequests: 0, workflowErrors: 0, requestsPerDay: [], blockedByAttack: [] });
        return;
      }
      const headers = await backendAuthHeaders();
      if (!headers) {
        if (!cancelled) setKpis({ users: 0, requestsToday: 0, blockedRequests: 0, workflowErrors: 0, requestsPerDay: [], blockedByAttack: [] });
        return;
      }
      try {
        const response = await fetch(`${backendUrl}/api/admin/overview`, { headers });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as Kpis;
        if (!cancelled) setKpis(body);
      } catch {
        if (!cancelled) {
          setKpis({ users: 0, requestsToday: 0, blockedRequests: 0, workflowErrors: 0, requestsPerDay: [], blockedByAttack: [] });
          setError(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (kpis === null) return <p className="card p-6 text-sm text-ink-secondary">…</p>;

  const maxRequests = Math.max(0, ...kpis.requestsPerDay.map((d) => d.count));
  const maxBlocked = Math.max(0, ...kpis.blockedByAttack.map((d) => d.count));
  const cards = [
    { label: t.kpiUsers, value: kpis.users },
    { label: t.kpiRequests, value: kpis.requestsToday },
    { label: t.kpiBlocked, value: kpis.blockedRequests },
    { label: t.kpiErrors, value: kpis.workflowErrors },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">{t.overviewTitle}</h1>
        {error && <p className="text-sm text-danger">{locale === "ar" ? "تعذر تحديث المؤشرات." : "Les indicateurs n'ont pas pu être chargés."}</p>}
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="card p-6">
            <p className="text-sm text-ink-secondary">{card.label}</p>
            <p className="mt-2 text-[32px] font-semibold leading-none">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card p-6">
          <h2 className="card-title">{t.chartRequests}</h2>
          <div className="mt-6 flex h-48 items-end gap-3">
            {kpis.requestsPerDay.map((day) => (
              <div key={day.day} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                <span className="text-xs font-medium">{day.count}</span>
                <div
                  className="w-full rounded-t-md bg-primary"
                  style={{ height: `${maxRequests ? Math.round((day.count / maxRequests) * 100) : 0}%` }}
                  role="img"
                  aria-label={`${day.day} : ${day.count}`}
                />
                <span className="text-xs text-ink-secondary">{day.day}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-6">
          <h2 className="card-title">{t.chartBlocked}</h2>
          <div className="mt-6 space-y-4">
            {kpis.blockedByAttack.length === 0 ? (
              <p className="text-sm text-ink-secondary">—</p>
            ) : null}
            {kpis.blockedByAttack.map((row) => (
              <div key={row.type}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span>{dict.dashboard.security.attacks[row.type as AttackType] ?? row.type}</span>
                  <span className="font-medium">{row.count}</span>
                </div>
                <div className="mt-1.5 h-3 w-full rounded-md bg-background">
                  <div
                    className="h-3 rounded-md bg-danger"
                    style={{ width: `${maxBlocked ? Math.round((row.count / maxBlocked) * 100) : 0}%` }}
                    role="img"
                    aria-label={`${row.type} : ${row.count}`}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
