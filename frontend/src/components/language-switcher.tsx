"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { locales, type Locale } from "@/lib/i18n/config";

/**
 * Language switcher: FR / عربي. Swaps the first path segment so the
 * current page opens in the other language (RTL layout for Arabic).
 */
export default function LanguageSwitcher({ locale }: { locale: Locale }) {
  const pathname = usePathname() || `/${locale}`;

  function hrefFor(target: Locale) {
    const segments = pathname.split("/");
    segments[1] = target;
    return segments.join("/") || `/${target}`;
  }

  return (
    <div
      className="flex items-center overflow-hidden rounded-md border border-stroke"
      role="group"
      aria-label={locale === "ar" ? "اللغة" : "Langue"}
    >
      {locales.map((item) => {
        const active = item === locale;
        return (
          <Link
            key={item}
            href={hrefFor(item)}
            aria-current={active ? "true" : undefined}
            className={`px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
              active ? "bg-primary text-white" : "text-ink-secondary hover:bg-primary-light"
            }`}
          >
            {item === "fr" ? "FR" : "عربي"}
          </Link>
        );
      })}
    </div>
  );
}
