"use client";

import { useEffect, useState } from "react";
import Alert from "@/components/alert";
import { Badge, RiskBadge } from "@/components/dashboard/badges";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { AuditEventRow, AttackType, BlockedRequest, SecurityIncident } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface SecurityClientProps {
  locale: Locale;
  dict: Dictionary;
  canViewRedTeamDetails: boolean;
}

/** Rapport red team réel (reports/redteam-*.json via le backend). */
interface RedteamCase {
  case: string;
  decision: string;
  expected: string;
  status: string;
  layer2: string;
}
interface RedteamReport {
  filename: string;
  verdict?: string;
  generated_at?: string;
  failures?: number;
  total?: number;
  cases?: RedteamCase[];
  content: string;
}

/**
 * Security section: incidents (conversation content gated behind a mandatory,
 * audited reason), blocked requests, red team reports and the audit log.
 */
export default function SecurityClient({
  locale,
  dict,
  canViewRedTeamDetails,
}: SecurityClientProps) {
  const t = dict.dashboard.security;
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [revealTarget, setRevealTarget] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [blocked, setBlocked] = useState<BlockedRequest[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEventRow[]>([]);
  const [incidentsError, setIncidentsError] = useState<string | null>(null);

  // Rapports red team RÉELS (reports/*.json) — admin, auditeur, super admin.
  const [realReports, setRealReports] = useState<RedteamReport[] | null>(null);
  const [reportsError, setReportsError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setIncidentsError(null);
      setReportsError(null);
      if (!backendUrl) return;
      const headers = await backendAuthHeaders();
      if (!headers) return;
      const [incidentsResponse, blockedResponse, auditResponse, redTeamResponse] = await Promise.all([
        fetch(`${backendUrl}/api/security/incidents?limit=50`, { headers }),
        fetch(`${backendUrl}/api/security/blocked-requests?limit=50`, { headers }),
        fetch(`${backendUrl}/api/admin/audit-events?limit=8`, { headers }),
        fetch(`${backendUrl}/api/security/redteam-reports`, { headers }),
      ]);

      if (incidentsResponse.ok) {
        const body = (await incidentsResponse.json()) as { incidents?: SecurityIncident[] };
        if (!cancelled) setIncidents(body.incidents || []);
      }
      if (blockedResponse.ok) {
        const body = (await blockedResponse.json()) as { blockedRequests?: BlockedRequest[] };
        if (!cancelled) setBlocked(body.blockedRequests || []);
      }
      if (auditResponse.ok) {
        const body = (await auditResponse.json()) as { events?: AuditEventRow[] };
        if (!cancelled) setAuditEvents(body.events || []);
      }
      if (redTeamResponse.status === 403) {
        if (!cancelled) setReportsError("403");
      } else if (redTeamResponse.ok) {
        const body = (await redTeamResponse.json()) as { reports?: RedteamReport[] };
        if (!cancelled) setRealReports(body.reports || []);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function confirmReveal(incidentId: string) {
    setError(null);
    if (reason.trim().length < 3) {
      setError(t.reasonLabel);
      return;
    }
    if (!backendUrl) return;
    const headers = await backendAuthHeaders(true);
    if (!headers) return;
    try {
      const response = await fetch(`${backendUrl}/api/security/incidents/${encodeURIComponent(incidentId)}/reveal`, {
        method: "POST",
        headers,
        body: JSON.stringify({ reason: reason.trim() }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
      const body = (await response.json()) as { conversationContent: string };
      setRevealed((previous) => ({ ...previous, [incidentId]: body.conversationContent }));
      setRevealTarget(null);
      setReason("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.reasonLabel);
    }
  }

  return (
    <div className="space-y-8">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      {/* Incidents ------------------------------------------------------- */}
      <section className="space-y-3">
        <h2 className="card-title">{t.incidentsTitle}</h2>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr className="border-b border-stroke text-xs uppercase tracking-wide text-ink-secondary">
                <th className="px-5 py-3 text-start font-semibold">{t.colTime}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colAttack}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colRisk}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colDecision}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colReason}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colContent}</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => (
                <tr key={incident.id} className="border-b border-stroke align-top last:border-0">
                  <td className="px-5 py-3 text-ink-secondary">
                    {incident.id}
                    <br />
                    {incident.createdAt}
                  </td>
                  <td className="px-5 py-3">
                    {t.attacks[incident.attackType as AttackType] ?? incident.attackType}
                    <br />
                    <span className="text-xs text-ink-secondary">IP {incident.sourceIp}</span>
                  </td>
                  <td className="px-5 py-3">
                    <RiskBadge risk={incident.risk} labels={dict.dashboard.employee.risks} />
                  </td>
                  <td className="px-5 py-3">
                    <Badge
                      tone={
                        incident.decision === "BLOCK"
                          ? "danger"
                          : incident.decision === "REVIEW"
                            ? "warning"
                            : "info"
                      }
                    >
                      {incident.decision}
                    </Badge>
                  </td>
                  <td className="max-w-[240px] px-5 py-3 text-ink-secondary">{incident.reason}</td>
                  <td className="max-w-[280px] px-5 py-3">
                    {incident.hasConversationContent ? (
                      revealed[incident.id] ? (
                        <p className="rounded-md border border-warning/40 bg-warning/10 p-2 text-xs">
                          {revealed[incident.id]}
                        </p>
                      ) : revealTarget === incident.id ? (
                        <div className="space-y-2">
                          <label htmlFor={`reason-${incident.id}`} className="block text-xs font-medium">
                            {t.reasonLabel}
                          </label>
                          <input
                            id={`reason-${incident.id}`}
                            type="text"
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            placeholder={t.reasonPlaceholder}
                            className="input h-9 text-sm"
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              className="rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-white transition-colors duration-150 hover:bg-primary-dark"
                              onClick={() => confirmReveal(incident.id)}
                            >
                              {t.confirmReveal}
                            </button>
                            <button
                              type="button"
                              className="rounded-md border border-stroke px-2.5 py-1 text-xs font-medium text-ink transition-colors duration-150 hover:border-primary"
                              onClick={() => {
                                setRevealTarget(null);
                                setReason("");
                              }}
                            >
                              {t.cancel}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-ink-secondary">{t.contentHidden}</span>
                          <button
                            type="button"
                            className="rounded-md border border-stroke px-2.5 py-1 text-xs font-medium text-ink transition-colors duration-150 hover:border-primary hover:text-primary"
                            onClick={() => {
                              setRevealTarget(incident.id);
                              setReason("");
                            }}
                          >
                            {t.reveal}
                          </button>
                        </div>
                      )
                    ) : (
                      <span className="text-xs text-ink-secondary">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-ink-secondary">{t.revealNote}</p>
      </section>

      {/* Blocked requests -------------------------------------------------- */}
      <section className="space-y-3">
        <h2 className="card-title">{t.blockedTitle}</h2>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-stroke text-xs uppercase tracking-wide text-ink-secondary">
                <th className="px-5 py-3 text-start font-semibold">{t.colTime}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colAttack}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colRoute}</th>
              </tr>
            </thead>
            <tbody>
              {blocked.map((row) => (
                <tr key={row.id} className="border-b border-stroke last:border-0">
                  <td className="px-5 py-3 text-ink-secondary">
                    {row.id} · {row.createdAt}
                  </td>
                  <td className="px-5 py-3">{t.attacks[row.attackType as AttackType] ?? row.attackType}</td>
                  <td className="px-5 py-3 font-medium">{row.route}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Red team ----------------------------------------------------------- */}
      <section className="space-y-3">
        <h2 className="card-title">{t.redTeamTitle}</h2>
        {realReports && realReports.length > 0 ? (
          <div className="space-y-4">
            {realReports.map((report) => (
              <div key={report.filename} className="card p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-medium">{report.filename}</span>
                  <Badge tone={report.failures ? "danger" : "success"}>
                    {report.verdict || `${report.total ?? "?"} cas`}
                  </Badge>
                  {report.generated_at && (
                    <span className="text-xs text-ink-secondary">{report.generated_at}</span>
                  )}
                </div>
                {canViewRedTeamDetails && report.cases && report.cases.length > 0 && (
                  <table className="mt-3 w-full text-left text-sm">
                    <thead className="text-xs text-ink-secondary">
                      <tr>
                        <th className="py-1">Cas</th>
                        <th className="py-1">Décision</th>
                        <th className="py-1">Attendu</th>
                        <th className="py-1">Statut</th>
                        <th className="py-1">Layer 2</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.cases.map((redCase) => (
                        <tr key={redCase.case} className="border-t border-stroke">
                          <td className="py-1.5">{redCase.case}</td>
                          <td className="py-1.5">{redCase.decision}</td>
                          <td className="py-1.5">{redCase.expected}</td>
                          <td className="py-1.5">
                            {redCase.status === "PASS" ? "✅" : "❌"}
                          </td>
                          <td className="py-1.5 text-xs text-ink-secondary">{redCase.layer2}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {!canViewRedTeamDetails && (
                  <p className="mt-2 text-xs text-ink-secondary">{t.redTeamDetailsHidden}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-ink-secondary">
            {reportsError === "403"
              ? t.redTeamDetailsHidden
              : (locale === "ar" ? "لا توجد تقارير red team بعد." : "Aucun rapport red team n'est disponible pour le moment.")}
          </p>
        )}
      </section>

      {/* Audit log ----------------------------------------------------------- */}
      <section className="space-y-3">
        <h2 className="card-title">{t.auditTitle}</h2>
        <ul className="space-y-2">
          {auditEvents.map((event) => (
            <li
              key={event.id}
              className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-stroke bg-white px-3 py-2 text-sm"
            >
              <span className="font-medium">{event.action}</span>
              <span className="text-ink-secondary">{event.detail}</span>
              <span className="ms-auto text-xs text-ink-secondary">
                {t.colActor} : {event.actor} · {event.entity} · {event.createdAt}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
