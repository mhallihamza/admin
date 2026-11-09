import type { ReactNode } from "react";

type AlertTone = "danger" | "success" | "info";

const toneClasses: Record<AlertTone, string> = {
  danger: "border-danger/30 bg-danger/5 text-danger",
  success: "border-success/30 bg-success/5 text-success",
  info: "border-info/30 bg-info/5 text-info",
};

/** Inline status message with clear color semantics (no animation). */
export default function Alert({
  tone,
  children,
}: {
  tone: AlertTone;
  children: ReactNode;
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={`rounded-lg border px-4 py-3 text-sm ${toneClasses[tone]}`}
    >
      {children}
    </div>
  );
}
