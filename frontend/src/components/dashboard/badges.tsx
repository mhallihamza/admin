import type { ReactNode } from "react";

type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const toneClasses: Record<Tone, string> = {
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-warning",
  danger: "border-danger/30 bg-danger/10 text-danger",
  info: "border-info/30 bg-info/10 text-info",
  neutral: "border-stroke bg-background text-ink-secondary",
};

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}

/** Risk badge: LOW/MEDIUM/HIGH/CRITICAL. */
export function RiskBadge({
  risk,
  labels,
}: {
  risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  labels: Record<string, string>;
}) {
  const tone: Tone =
    risk === "LOW" ? "success" : risk === "MEDIUM" ? "warning" : "danger";
  return <Badge tone={tone}>{labels[risk] ?? risk}</Badge>;
}

/** Review-case status badge. */
export function CaseStatusBadge({
  status,
  labels,
}: {
  status: string;
  labels: Record<string, string>;
}) {
  const tone: Tone =
    status === "APPROVED" || status === "CORRECTED"
      ? "success"
      : status === "REJECTED"
        ? "danger"
        : status === "IN_REVIEW"
          ? "warning"
          : "info";
  return <Badge tone={tone}>{labels[status] ?? status}</Badge>;
}

/** Document status badge. */
export function DocStatusBadge({
  status,
  labels,
}: {
  status: string;
  labels: Record<string, string>;
}) {
  const tone: Tone =
    status === "APPROVED"
      ? "success"
      : status === "PENDING_REVIEW"
        ? "warning"
        : status === "DISABLED"
          ? "neutral"
          : "info";
  return <Badge tone={tone}>{labels[status] ?? status}</Badge>;
}

/** Workflow execution status badge. */
export function WfStatusBadge({
  status,
  labels,
}: {
  status: string;
  labels: Record<string, string>;
}) {
  const tone: Tone =
    status === "SUCCESS" ? "success" : status === "ERROR" ? "danger" : "info";
  return <Badge tone={tone}>{labels[status] ?? status}</Badge>;
}
