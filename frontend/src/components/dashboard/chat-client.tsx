"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { backendAuthHeaders, backendUrl } from "@/lib/api";
import type { ChatMessage } from "@/lib/dashboard/api-types";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Rendu léger : **gras** -> <strong> (pas de HTML brut). */
function renderBold(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

/** Suggestions réelles, alignées sur le corpus ingéré. */
const REAL_SUGGESTIONS: Record<Locale, string[]> = {
  fr: [
    "Comment obtenir le certificat d'héritage ?",
    "Qui doit déclarer un décès et dans quel délai ?",
    "Comment immatriculer une société au registre du commerce ?",
    "ما هي شروط عقد الزواج في المغرب؟",
  ],
  ar: [
    "كيف أحصل على شهادة التوريث؟",
    "من يتوجب عليه التصريح بالوفاة وفي أي أجل؟",
    "كيف أسجل شركة في السجل التجاري؟",
    "What are the marriage conditions under the family code?",
  ],
};

/** Réponse du backend (POST /api/chat/message). */
interface ChatApiResponse {
  decision: string;
  answer?: string | null;
  detail?: string;
  citations?: { document_id?: string; article_number?: string; version?: string }[];
  conversation_id?: string | null;
  persistence_error?: string | null;
}

/** true quand le backend réel est configuré. */
const liveChatEnabled = Boolean(backendUrl);

/** Citizen chat panel: assistant messages start-aligned, user messages end-aligned. */
export default function ChatClient({
  locale,
  dict,
  conversationId,
}: {
  locale: Locale;
  dict: Dictionary;
  conversationId?: string;
}) {
  const t = dict.dashboard.citizen;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [savedTitles, setSavedTitles] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reviewRequested, setReviewRequested] = useState<Record<string, boolean>>({});
  // L'id de conversation réel survit au rafraîchissement (localStorage).
  const [liveConversationId, setLiveConversationId] = useState<string | null>(
    () =>
      conversationId ??
      (typeof window !== "undefined" ? window.localStorage.getItem("chat-conversation-id") : null)
  );
  const scrollRef = useRef<HTMLDivElement>(null);

  function adoptConversation(id: string | null | undefined) {
    if (!id) return;
    setLiveConversationId(id);
    try {
      window.localStorage.setItem("chat-conversation-id", id);
    } catch {
      /* stockage indisponible */
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!liveChatEnabled || !backendUrl) return;
      const headers = await backendAuthHeaders();
      if (!headers) return;

      try {
        const savedResponse = await fetch(`${backendUrl}/api/procedures/saved`, { headers });
        if (savedResponse.ok) {
          const body = (await savedResponse.json()) as { saved: { title: string }[] };
          if (!cancelled) setSavedTitles(body.saved.map((s) => s.title));
        }
      } catch {
        /* silencieux */
      }

      if (!liveConversationId) return;
      try {
        const response = await fetch(
          `${backendUrl}/api/chat/messages?conversation_id=${encodeURIComponent(liveConversationId)}`,
          { headers },
        );
        if (!response.ok) return;
        const body = (await response.json()) as {
          conversation_id: string;
          messages: { id: string; role: string; text: string }[];
        };
        if (cancelled || !body.messages?.length) return;
        setMessages(body.messages.map((m): ChatMessage => ({
          id: m.id,
          role: m.role as ChatMessage["role"],
          text: m.text,
        })));
      } catch {
        /* silencieux */
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveConversationId]);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    });
  }

  function pushMessage(message: ChatMessage) {
    setMessages((current) => [...current, message]);
  }

  function titleFromAnswer(text: string) {
    const clean = text.replace(/^\s*\[(?:PROCEDURE|LEGAL_RESEARCH|DOCUMENT_ADMIN|SUPERVISOR|DETECTION)_AGENT\]\s*\n?/gim, "");
    const first = clean.split("\n").map((line) => line.trim()).find(Boolean) ?? clean.trim();
    return first.replace(/^#+\s*/, "").replace(/^\*\*(.+)\*\*$/, "$1").slice(0, 120);
  }

  async function saveAnswer(message: ChatMessage) {
    setActionError(null);
    if (!message.text) return;
    const title = titleFromAnswer(message.text);
    const headers = await backendAuthHeaders(true);
    if (!headers || !backendUrl) return;
    try {
      const response = await fetch(`${backendUrl}/api/procedures/saved`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          title,
          snapshot: { answer: message.text, conversation_id: liveConversationId },
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setSavedTitles((current) => (current.includes(title) ? current : [...current, title]));
    } catch {
      setActionError(locale === "ar" ? "تعذر حفظ الإجابة." : "Impossible de sauvegarder cette réponse.");
    }
  }

  async function requestReview(message: ChatMessage, question: string) {
    setActionError(null);
    if (!message.text) return;
    const headers = await backendAuthHeaders(true);
    if (!headers || !backendUrl) return;
    try {
      const response = await fetch(`${backendUrl}/api/review-cases/request`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          question_summary: (question || message.text).slice(0, 500),
          proposed_answer: message.text,
          conversation_id: liveConversationId,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setReviewRequested((current) => ({ ...current, [message.id]: true }));
    } catch {
      setActionError(locale === "ar" ? "تعذر إرسال طلب المراجعة." : "Impossible d'envoyer la demande de revue.");
    }
  }

  async function askBackend(text: string): Promise<boolean> {
    if (!liveChatEnabled || !backendUrl) return false;
    const headers = await backendAuthHeaders(true);
    if (!headers) return false;
    try {
      const response = await fetch(`${backendUrl}/api/chat/message`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          text,
          locale,
          conversation_id: liveConversationId || undefined,
        }),
      });
      const status = response.status;
      const body = (await response.json().catch(() => ({}))) as ChatApiResponse & { detail?: string };
      if (!response.ok) {
        if (status === 403) {
          pushMessage({
            id: `m-${Date.now()}`,
            role: "system",
            text:
              locale === "ar"
                ? "حُظر طلبك لدى طبقة الأمان قبل الوصول إلى المساعد."
                : "Votre demande a été bloquée par le filtre de sécurité.",
          });
          return true;
        }
        pushMessage({
          id: `m-${Date.now()}`,
          role: "system",
          text: body.detail || (locale === "ar" ? "حدث خطأ أثناء معالجة طلبك." : "Une erreur est survenue lors du traitement de votre demande."),
        });
        return true;
      }
      adoptConversation(body.conversation_id);
      if (body.decision === "allow" && body.answer) {
        // le marqueur d'agent ([PROCEDURE_AGENT]…) est interne — pas montré
        const clean = body.answer.replace(/^\[[^\]]+\]\s*\n?/, "");
        pushMessage({ id: `m-${Date.now()}`, role: "assistant", text: clean });
      } else {
        pushMessage({
          id: `m-${Date.now()}`,
          role: "system",
          text: body.detail || "Réponse retenue pour vérification humaine.",
        });
      }
      if (body.persistence_error) {
        setActionError(
          locale === "ar" ? "تم الحصول على الجواب لكن تعذر حفظه." : "La réponse a été obtenue, mais sa sauvegarde a échoué."
        );
      }
      return true;
    } catch {
      return false;
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("message") as HTMLInputElement | null;
    const text = input?.value.trim();
    if (!text || pending) return;
    form.reset();
    setActionError(null);
    pushMessage({ id: `u-${Date.now()}`, role: "user", text });
    setPending(true);
    // indicateur d'attente : le pipeline complet peut prendre 30-60 s
    pushMessage({ id: `p-${Date.now()}`, role: "system", text: "…" });
    scrollToBottom();
    const handled = liveChatEnabled ? await askBackend(text) : false;
    // retire l'indicateur d'attente
    setMessages((current) => current.filter((m) => !m.id.startsWith("p-")));
    if (!handled) {
      // repli : backend injoignable — message honnête, pas de données d'exemple
      pushMessage({
        id: `e-${Date.now()}`,
        role: "system",
        text:
          locale === "ar"
            ? "تعذّر الاتصال بمحرك الإجابة — تحقق من تشغيل الخدمة وأعد المحاولة."
            : "Impossible de joindre le moteur de réponse — vérifiez le service et réessayez.",
      });
    }
    setPending(false);
    scrollToBottom();
  }

  async function handleSubmitPrefill(suggestion: string) {
    if (pending) return;
    pushMessage({ id: `u-${Date.now()}`, role: "user", text: suggestion });
    setPending(true);
    pushMessage({ id: `p-${Date.now()}`, role: "system", text: "…" });
    scrollToBottom();
    const handled = liveChatEnabled ? await askBackend(suggestion) : false;
    setMessages((current) => current.filter((m) => !m.id.startsWith("p-")));
    if (!handled) {
      pushMessage({
        id: `e-${Date.now()}`,
        role: "system",
        text:
          locale === "ar"
            ? "تعذّر الاتصال بمحرك الإجابة — أعد المحاولة."
            : "Impossible de joindre le moteur de réponse — réessayez.",
      });
    }
    setPending(false);
    scrollToBottom();
  }

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <section className="card flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between gap-3 border-b border-stroke px-5 py-3">
          <h2 className="card-title">{t.chatTitle}</h2>
        </div>

        {actionError ? (
          <p className="border-b border-stroke px-5 py-3 text-sm text-danger">{actionError}</p>
        ) : null}

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.map((message, index) => {
            if (message.role === "user") {
              return (
                <div key={message.id} className="flex justify-end">
                  <div className="max-w-[80%] rounded-lg bg-primary px-4 py-2.5 text-sm text-white">
                    {message.text}
                  </div>
                </div>
              );
            }
            const previousQuestion = [...messages.slice(0, index)]
              .reverse()
              .find((candidate) => candidate.role === "user")?.text ?? "";
            return (
              <div key={message.id} className="flex justify-start">
                <div className="max-w-[80%] whitespace-pre-wrap rounded-lg border border-stroke bg-white px-4 py-2.5 text-sm text-ink">
                  {renderBold(message.text ?? "")}
                  {message.role !== "assistant" || message.id.startsWith("p-") || message.id.startsWith("e-") ? null : (
                    <span className="mt-3 flex flex-wrap gap-2 border-t border-stroke pt-3">
                      <button
                        type="button"
                        className="btn-outline h-8 px-3 py-1 text-xs"
                        onClick={() => void saveAnswer(message)}
                      >
                        {t.saveProcedure}
                      </button>
                      <button
                        type="button"
                        className="btn-outline h-8 px-3 py-1 text-xs"
                        disabled={Boolean(reviewRequested[message.id])}
                        onClick={() => void requestReview(message, previousQuestion)}
                      >
                        {reviewRequested[message.id] ? t.reviewRequested : t.requestReview}
                      </button>
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="border-t border-stroke p-4">
          <p className="mb-3 text-xs text-ink-secondary">{t.engineNote}</p>
          <form onSubmit={handleSubmit} className="flex gap-2">
            <label htmlFor="chat-input" className="sr-only">
              {t.chatPlaceholder}
            </label>
            <input
              id="chat-input"
              name="message"
              type="text"
              placeholder={t.chatPlaceholder}
              className="input"
              autoComplete="off"
            />
            <button type="submit" className="btn-primary shrink-0">
              {t.send}
            </button>
          </form>
        </div>
      </section>

      <aside className="shrink-0 space-y-6 lg:w-[320px]">
        <div className="card p-5">
          <h3 className="card-title">{t.suggestedProcedures}</h3>
          <ul className="mt-4 space-y-2">
            {(REAL_SUGGESTIONS[locale] || []).map((suggestion) => (
              <li key={suggestion}>
                <button
                  type="button"
                  onClick={() => void handleSubmitPrefill(suggestion)}
                  className="block w-full rounded-md border border-stroke bg-background px-3 py-2 text-start text-sm transition hover:bg-primary-light"
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="card p-5">
          <h3 className="card-title">{t.savedProcedures}</h3>
          {savedTitles.length === 0 ? (
            <p className="mt-4 text-sm text-ink-secondary">{t.savedEmpty}</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {savedTitles.map((title) => (
                <li
                  key={title}
                  className="rounded-md border border-stroke bg-background px-3 py-2 text-sm"
                >
                  {title}
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}
