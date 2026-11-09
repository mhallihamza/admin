"use client";

import { useRef, useState, type FormEvent } from "react";

/**
 * Chat public du hero — sans compte. Les questions partent vers
 * POST {NEXT_PUBLIC_BACKEND_URL}/api/chat/public : filtrage IP + détection
 * Layer 2 + réponse fondée sur les documents officiels APPROVED uniquement.
 * Hors ligne (backend absent) : message d'indisponibilité honnête.
 */
interface Exchange {
  id: number;
  question?: string;
  answer?: string;
  tone?: "ok" | "warn";
}

interface PublicChatProps {
  title: string;
  placeholder: string;
  button: string;
  examplesLabel: string;
  chips: string[];
  disclaimer: string;
  unavailable: string;
}

/** Rendu léger : **gras** -> <strong> (pas de HTML brut). */
function renderBold(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

export default function PublicChat({
  title,
  placeholder,
  button,
  examplesLabel,
  chips,
  disclaimer,
  unavailable,
}: PublicChatProps) {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [pending, setPending] = useState(false);
  const [value, setValue] = useState("");
  const counter = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  async function ask(question: string) {
    const q = question.trim();
    if (!q || pending) return;
    const id = ++counter.current;
    setExchanges((list) => [...list, { id, question: q }]);
    setValue("");
    setPending(true);
    scrollToBottom();

    let answer: string | null = null;
    let tone: "ok" | "warn" = "ok";
    try {
      if (backendUrl) {
        const response = await fetch(`${backendUrl}/api/chat/public`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: q, language: "fr" }),
        });
        if (response.ok) {
          const body = (await response.json()) as {
            decision: string; answer?: string; detail?: string;
          };
          if (body.decision === "allow" && body.answer) {
            // le marqueur d'agent en 1re ligne est interne — pas montré
            answer = body.answer.replace(/^\[[^\]]+\]\s*\n?/, "");
          } else {
            answer = body.detail || unavailable;
            tone = "warn";
          }
        }
      }
    } catch {
      /* réseau indisponible -> message ci-dessous */
    }
    if (answer === null) answer = unavailable;
    // clé unique : la réponse est une entrée propre (le compteur est partagé)
    const answerId = ++counter.current;
    setExchanges((list) => [...list, { id: answerId, answer, tone }]);
    setPending(false);
    scrollToBottom();
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(value);
  }

  return (
    <div className="public-chat rounded-2xl border border-white/15 bg-white/[0.06] p-5 shadow-2xl backdrop-blur-md sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-emerald-50/90">
          {title}
        </h3>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/15 px-2.5 py-1 text-[11px] font-medium text-emerald-100 ring-1 ring-emerald-300/30">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
          En ligne
        </span>
      </div>

      <div ref={scrollRef} className="mt-4 max-h-72 space-y-3 overflow-y-auto pr-1">
        {exchanges.length === 0 && (
          <p className="rounded-xl bg-white/5 px-4 py-3 text-sm text-emerald-50/80">
            {placeholder}
          </p>
        )}
        {exchanges.map((exchange) => (
          <div key={exchange.id} className="space-y-2">
            {exchange.question && (
              <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-white px-4 py-2.5 text-sm font-medium text-emerald-950 shadow">
                {exchange.question}
              </p>
            )}
            {exchange.answer && (
              <p
                className={`w-fit max-w-[92%] whitespace-pre-wrap rounded-2xl rounded-bl-md px-4 py-3 text-sm leading-relaxed shadow ${
                  exchange.tone === "warn"
                    ? "bg-amber-50 text-amber-900"
                    : "bg-white text-slate-800"
                }`}
              >
                {renderBold(exchange.answer)}
              </p>
            )}
          </div>
        ))}
        {pending && (
          <p className="w-fit rounded-2xl bg-white/10 px-4 py-2.5 text-sm text-emerald-50/80">
            <span className="animate-pulse">● ● ●</span>
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          maxLength={1000}
          className="h-12 flex-1 rounded-xl border border-white/20 bg-white/95 px-4 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-300"
        />
        <button
          type="submit"
          disabled={pending}
          className="h-12 rounded-xl bg-emerald-300 px-5 text-sm font-semibold text-emerald-950 transition hover:bg-emerald-200 disabled:opacity-60"
        >
          {button}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wide text-emerald-100/70">
          {examplesLabel}
        </span>
        {chips.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => void ask(chip)}
            disabled={pending}
            className="rounded-full border border-white/25 bg-white/10 px-3 py-1 text-xs text-emerald-50 transition hover:bg-white/20 disabled:opacity-50"
          >
            {chip}
          </button>
        ))}
      </div>

      <p className="mt-3 border-t border-white/10 pt-3 text-[11px] leading-relaxed text-emerald-100/60">
        {disclaimer}
      </p>
    </div>
  );
}
