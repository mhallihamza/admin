"use client";

import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import Alert from "@/components/alert";
import { DocStatusBadge } from "@/components/dashboard/badges";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { DocumentItem, DocumentStatus } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

const MAX_SIZE_MB = 20;
const ALLOWED = ["pdf", "docx", "txt"];

interface ApiDocument {
  id: string;
  title: string;
  fileName?: string;
  file_name?: string;
  fileType?: DocumentItem["fileType"];
  file_type?: string;
  sizeMb?: number;
  file_size_bytes?: number;
  status: DocumentStatus;
  uploadedAt?: string;
  created_at?: string;
  extractedPreview?: string;
  extracted_text?: string;
}

function normalize(row: ApiDocument): DocumentItem {
  const bytes = row.file_size_bytes ?? (row.sizeMb ?? 0) * 1024 * 1024;
  return {
    id: row.id,
    title: row.title,
    fileName: row.fileName ?? row.file_name ?? "",
    fileType: row.fileType ?? (row.file_type as DocumentItem["fileType"]) ?? "txt",
    sizeMb: row.sizeMb ?? Math.round((bytes / (1024 * 1024)) * 10) / 10,
    status: row.status,
    uploadedAt: row.uploadedAt ?? row.created_at ?? "",
    extractedPreview: row.extractedPreview ?? row.extracted_text ?? "",
  };
}

/**
 * Document management: upload via `POST /api/documents/upload`, list/actions via the
 * real admin document API. Uploading never publishes.
 */
export default function DocumentsClient({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.dashboard.admin;
  const [rows, setRows] = useState<DocumentItem[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setError(null);
    if (!backendUrl) {
      setRows([]);
      return;
    }
    const headers = await backendAuthHeaders();
    if (!headers) {
      setRows([]);
      return;
    }
    try {
      const response = await fetch(`${backendUrl}/api/documents`, { headers });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = (await response.json()) as { documents?: ApiDocument[] };
      setRows((body.documents || []).map(normalize));
    } catch {
      setRows([]);
      setError(locale === "ar" ? "تعذر تحميل المستندات." : "Impossible de charger les documents.");
    }
  }, [locale]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function uploadFile(file: File) {
    if (!backendUrl) {
      setError(locale === "ar" ? "الخدمة غير متاحة." : "Le service n'est pas configuré.");
      return;
    }
    const headers = await backendAuthHeaders(); // multipart requires no content-type
    if (!headers) return;
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${backendUrl}/api/documents/upload`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      setError(body.detail || (locale === "ar" ? "تعذر رفع الملف." : "Le fichier n'a pas pu être envoyé."));
    }
  }

  async function handleFiles(files: FileList | null) {
    setError(null);
    if (!files) return;
    for (const file of Array.from(files)) {
      const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
      if (!ALLOWED.includes(extension)) {
        setError(t.invalidType);
        continue;
      }
      if (file.size / (1024 * 1024) > MAX_SIZE_MB) {
        setError(t.tooLarge);
        continue;
      }
      await uploadFile(file);
    }
    await refresh();
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    void handleFiles(event.dataTransfer.files);
  }

  async function action(row: DocumentItem, status: DocumentItem["status"]) {
    if (!backendUrl) return;
    const headers = await backendAuthHeaders(true);
    if (!headers) return;
    setError(null);
    try {
      const response = await fetch(`${backendUrl}/api/documents/${encodeURIComponent(row.id)}/status`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.invalidType);
    }
  }

  const selected = rows?.find((row) => row.id === selectedId) ?? null;

  if (rows === null) return <p className="card p-6 text-sm text-ink-secondary">…</p>;

  return (
    <div className="space-y-6">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <div
        role="button"
        tabIndex={0}
        aria-label={t.dropzone}
        className={`card flex cursor-pointer flex-col items-center justify-center gap-2 border-dashed px-6 py-10 text-center transition-colors duration-150 ${
          dragOver ? "border-primary bg-primary-light/50" : ""
        }`}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <p className="text-sm font-medium">{t.dropzone}</p>
        <p className="text-xs text-ink-secondary">
          {t.allowedTypes} · {t.sizeLimit}
        </p>
        <p className="text-xs text-ink-secondary">{t.uploadNote}</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          multiple
          className="hidden"
          onChange={(event) => void handleFiles(event.target.files)}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-stroke text-xs uppercase tracking-wide text-ink-secondary">
                <th className="px-5 py-3 text-start font-semibold">{t.colTitle}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colFile}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colSize}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colStatus}</th>
                <th className="px-5 py-3 text-start font-semibold">{t.colDocActions}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className={`cursor-pointer border-b border-stroke last:border-0 hover:bg-primary-light/40 ${
                    selectedId === row.id ? "bg-primary-light/60" : ""
                  }`}
                  onClick={() => setSelectedId(row.id)}
                >
                  <td className="px-5 py-3 font-medium">{row.title}</td>
                  <td className="px-5 py-3 text-ink-secondary">{row.fileName}</td>
                  <td className="px-5 py-3 text-ink-secondary">{row.sizeMb} MB</td>
                  <td className="px-5 py-3">
                    <DocStatusBadge status={row.status} labels={t.docStatuses} />
                  </td>
                  <td className="px-5 py-3" onClick={(event) => event.stopPropagation()}>
                    <div className="flex flex-wrap gap-1.5">
                      {row.status === "UPLOADED" ? (
                        <SmallBtn onClick={() => void action(row, "PARSED")}>{t.sendIndexing}</SmallBtn>
                      ) : null}
                      {row.status === "PARSED" ? (
                        <SmallBtn onClick={() => void action(row, "PENDING_REVIEW")}>{t.sendReview}</SmallBtn>
                      ) : null}
                      {row.status === "PENDING_REVIEW" ? (
                        <>
                          <SmallBtn onClick={() => void action(row, "APPROVED")}>{t.approve}</SmallBtn>
                          <SmallBtn onClick={() => void action(row, "DISABLED")}>{t.reject}</SmallBtn>
                        </>
                      ) : null}
                      {row.status === "APPROVED" ? (
                        <SmallBtn onClick={() => void action(row, "DISABLED")}>{t.disable}</SmallBtn>
                      ) : null}
                      {row.status === "DISABLED" ? (
                        <SmallBtn onClick={() => void action(row, "UPLOADED")}>{t.retry}</SmallBtn>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <aside className="card h-fit p-5">
          <h2 className="card-title">{t.previewTitle}</h2>
          {selected ? (
            <div className="mt-4">
              <p className="text-sm font-medium">{selected.title}</p>
              <p className="mt-1 text-xs text-ink-secondary">{selected.fileName}</p>
              <div className="mt-3 max-h-72 overflow-y-auto rounded-md border border-stroke bg-background p-3 text-sm text-ink-secondary">
                {selected.extractedPreview || t.previewEmpty}
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-ink-secondary">{t.previewEmpty}</p>
          )}
        </aside>
      </div>
    </div>
  );
}

function SmallBtn({ onClick, children }: { onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      className="rounded-md border border-stroke px-2.5 py-1 text-xs font-medium text-ink transition-colors duration-150 hover:border-primary hover:text-primary"
      onClick={onClick}
    >
      {children}
    </button>
  );
}
