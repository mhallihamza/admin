import { ChevronDownIcon } from "@/components/icons";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/**
 * FAQ accordion using native details/summary (keyboard accessible by default,
 * no animation).
 */
export default function Faq({ dict }: { dict: Dictionary["faq"] }) {
  return (
    <section id="faq" className="scroll-mt-6 py-16 lg:py-20">
      <div className="container-page">
        <div className="mx-auto max-w-3xl">
          <h2 className="section-title text-center">{dict.title}</h2>
          <div className="mt-8 space-y-3">
            {dict.items.map((item) => (
              <details key={item.question} className="card group px-5 py-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium [&::-webkit-details-marker]:hidden">
                  <span>{item.question}</span>
                  <ChevronDownIcon className="h-4 w-4 shrink-0 text-ink-secondary group-open:rotate-180" />
                </summary>
                <p className="mt-3 text-sm text-ink-secondary">{item.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
