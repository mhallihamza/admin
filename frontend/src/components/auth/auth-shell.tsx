import type { ReactNode } from "react";
import Brand from "@/components/brand";
import LanguageSwitcher from "@/components/language-switcher";
import type { Locale } from "@/lib/i18n/config";

/**
 * Shared shell for Login / Create account: top bar (brand + language
 * switcher) and a centered 420 px card on the page background.
 */
export default function AuthShell({
  locale,
  children,
}: {
  locale: Locale;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="border-b border-stroke bg-white">
        <div className="container-page flex h-16 items-center justify-between">
          <Brand locale={locale} />
          <LanguageSwitcher locale={locale} />
        </div>
        <div aria-hidden="true" className="h-[3px] bg-accent" />
      </div>
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-[420px]">{children}</div>
      </main>
    </div>
  );
}
