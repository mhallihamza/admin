import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Services grid: 6 cards (3 columns desktop, 2 tablet, 1 mobile). */
export default function Services({ dict }: { dict: Dictionary["services"] }) {
  return (
    <section id="services" className="scroll-mt-6 py-16 lg:py-20">
      <div className="container-page">
        <h2 className="section-title">{dict.title}</h2>
        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {dict.items.map((item) => (
            <article key={item.title} className="card p-6">
              <h3 className="card-title">{item.title}</h3>
              <p className="mt-2 text-sm text-ink-secondary">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
