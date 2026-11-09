import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Trust band: green background, white text, three short points. */
export default function SourcesBand({ dict }: { dict: Dictionary["sources"] }) {
  return (
    <section id="sources" className="scroll-mt-6 bg-primary py-16 text-white">
      <div className="container-page">
        <h2 className="section-title">{dict.title}</h2>
        <div className="mt-8 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {dict.points.map((point) => (
            <div key={point.title}>
              <h3 className="text-lg font-semibold">{point.title}</h3>
              <p className="mt-2 text-sm text-white/80">{point.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
