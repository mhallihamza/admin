import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Three-step row: numbered white cards. */
export default function HowItWorks({ dict }: { dict: Dictionary["howItWorks"] }) {
  return (
    <section id="how-it-works" className="scroll-mt-6 py-16 lg:py-20">
      <div className="container-page">
        <h2 className="section-title">{dict.title}</h2>
        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {dict.items.map((item, index) => (
            <article key={item.title} className="card p-6">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-light text-sm font-semibold text-primary">
                {index + 1}
              </span>
              <h3 className="card-title mt-4">{item.title}</h3>
              <p className="mt-2 text-sm text-ink-secondary">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
