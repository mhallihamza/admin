import Link from "next/link";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Footer: dark green, four columns (platform, legal, contact, language). */
export default function Footer({
  dict,
  activeLocale,
}: {
  dict: Dictionary["footer"];
  activeLocale: string;
}) {
  const columns = [
    { title: dict.platformTitle, links: dict.platformLinks },
    { title: dict.legalTitle, links: dict.legalLinks },
    { title: dict.contactTitle, links: dict.contactLinks },
  ];

  return (
    <footer className="bg-primary text-white">
      <div className="container-page py-12">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {columns.map((column) => (
            <div key={column.title}>
              <h3 className="text-base font-semibold">{column.title}</h3>
              <ul className="mt-4 space-y-2">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-white/75 transition-colors duration-150 hover:text-white"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div>
            <h3 className="text-base font-semibold">{dict.languageTitle}</h3>
            <ul className="mt-4 space-y-2">
              {dict.languageLinks.map((link) => (
                <li key={link.locale}>
                  <Link
                    href={link.href}
                    aria-current={link.locale === activeLocale ? "true" : undefined}
                    className={`text-sm transition-colors duration-150 hover:text-white ${
                      link.locale === activeLocale ? "text-white" : "text-white/75"
                    }`}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-10 border-t border-white/15 pt-6 text-sm text-white/70">
          {dict.copyright}
        </div>
      </div>
    </footer>
  );
}
