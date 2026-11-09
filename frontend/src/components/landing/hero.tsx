import PublicChat from "@/components/landing/public-chat";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/**
 * Hero premium : fond vert émeraude + motif zellige subtil (étoile à
 * huit branches, patrimoine marocain) et — pièce maîtresse — le chat
 * public : le visiteur pose sa question SANS compte et reçoit une
 * réponse fondée sur les documents officiels approuvés.
 */
export default function Hero({ dict }: { dict: Dictionary["hero"] }) {
  return (
    <section className="hero-premium relative overflow-hidden bg-emerald-950 text-white">
      {/* motif zellige — étoile à 8 branches, opacité faible */}
      <div className="hero-zellige pointer-events-none absolute inset-0" aria-hidden />
      <div
        className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-emerald-400/10 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -bottom-40 -left-24 h-96 w-96 rounded-full bg-red-500/10 blur-3xl"
        aria-hidden
      />

      <div className="container-page relative grid items-center gap-12 py-16 lg:grid-cols-2 lg:py-24">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-300/30 bg-emerald-400/10 px-3.5 py-1.5 text-xs font-medium tracking-wide text-emerald-100">
            <span className="text-base leading-none">★</span>
            Royaume du Maroc — service public administratif
          </span>
          <h1 className="mt-6 text-4xl font-bold leading-[1.15] tracking-tight sm:text-5xl">
            {dict.headline}
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-emerald-50/85">
            {dict.subtitle}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-emerald-50/80">
            <span className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400/20 text-xs text-emerald-200">
                ✓
              </span>
              Documents officiels approuvés uniquement
            </span>
            <span className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400/20 text-xs text-emerald-200">
                ✓
              </span>
              Réponses citées (document, article, version)
            </span>
            <span className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400/20 text-xs text-emerald-200">
                ✓
              </span>
              Français et العربية
            </span>
          </div>
        </div>

        <PublicChat
          title={dict.chat.title}
          placeholder={dict.chat.placeholder}
          button={dict.chat.button}
          examplesLabel={dict.chat.examplesLabel}
          chips={dict.chat.chips}
          disclaimer={dict.chat.disclaimer}
          unavailable={dict.chat.unavailable}
        />
      </div>
    </section>
  );
}
