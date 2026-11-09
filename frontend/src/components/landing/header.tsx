"use client";

import { useState } from "react";
import Link from "next/link";
import Brand from "@/components/brand";
import LanguageSwitcher from "@/components/language-switcher";
import { CloseIcon, MenuIcon } from "@/components/icons";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/**
 * Landing header: 72 px, white, bottom border, centered nav, auth actions,
 * language switcher — and the 3 px red accent line underneath.
 * Collapses to a menu button below `lg`.
 */
export default function Header({ locale, dict }: { locale: Locale; dict: Dictionary }) {
  const [open, setOpen] = useState(false);

  const navItems = [
    { label: dict.header.nav.howItWorks, href: "#how-it-works" },
    { label: dict.header.nav.services, href: "#services" },
    { label: dict.header.nav.sources, href: "#sources" },
    { label: dict.header.nav.faq, href: "#faq" },
  ];

  return (
    <>
      <header className="border-b border-stroke bg-white">
        <div className="container-page grid h-[72px] grid-cols-[1fr_auto_1fr] items-center gap-4">
          <div className="justify-self-start">
            <Brand locale={locale} />
          </div>

          <nav aria-label={dict.brand} className="hidden lg:flex items-center gap-8">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-sm text-ink-secondary transition-colors duration-150 hover:text-ink"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="hidden lg:flex items-center justify-self-end gap-3">
            <LanguageSwitcher locale={locale} />
            <Link href={`/${locale}/login`} className="btn-outline">
              {dict.header.login}
            </Link>
            <Link href={`/${locale}/register`} className="btn-primary">
              {dict.header.createAccount}
            </Link>
          </div>

          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-stroke text-ink lg:hidden"
            aria-expanded={open}
            aria-label={open ? dict.header.menuClose : dict.header.menuOpen}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>

        {open ? (
          <div className="border-t border-stroke bg-white shadow-[0_4px_16px_rgba(20,32,26,0.06)] lg:hidden">
            <nav aria-label={dict.brand} className="container-page flex flex-col gap-1 py-4">
              {navItems.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-2 py-2 text-sm text-ink transition-colors duration-150 hover:bg-primary-light"
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </a>
              ))}
              <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-stroke pt-4">
                <LanguageSwitcher locale={locale} />
                <Link href={`/${locale}/login`} className="btn-outline">
                  {dict.header.login}
                </Link>
                <Link href={`/${locale}/register`} className="btn-primary">
                  {dict.header.createAccount}
                </Link>
              </div>
            </nav>
          </div>
        ) : null}
      </header>
      {/* 3 px red accent line under the header */}
      <div aria-hidden="true" className="h-[3px] bg-accent" />
    </>
  );
}
