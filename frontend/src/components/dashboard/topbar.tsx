"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import LanguageSwitcher from "@/components/language-switcher";
import { BellIcon, LogoutIcon, MenuIcon } from "@/components/icons";
import { createClient } from "@/lib/supabase/client";
import { pageTitleForPath } from "@/lib/dashboard/nav";
import type { AppRole } from "@/lib/dashboard/nav";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface TopbarProps {
  locale: Locale;
  dict: Dictionary;
  user: { name: string; email: string };
  roles: AppRole[];
  onMenuClick: () => void;
}

/** 64 px top bar: page title, language switcher, notifications, user menu. */
export default function Topbar({ locale, dict, user, roles, onMenuClick }: TopbarProps) {
  const router = useRouter();
  const [notifOpen, setNotifOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const pathname = usePathname() || `/${locale}/dashboard`;
  const title = pageTitleForPath(pathname, locale, dict);

  const initials = (user.name || user.email || "?")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  async function handleSignOut() {
    setSigningOut(true);
    const supabase = createClient();
    if (supabase) {
      await supabase.auth.signOut();
    }
    router.push(`/${locale}/login`);
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-3 border-b border-stroke bg-white px-4 md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-stroke text-ink md:hidden"
          aria-label={dict.dashboard.topbar.menuOpen}
          onClick={onMenuClick}
        >
          <MenuIcon className="h-5 w-5" />
        </button>
        <h1 className="truncate text-lg font-semibold">{title}</h1>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <LanguageSwitcher locale={locale} />

        <div className="relative">
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-stroke text-ink-secondary transition-colors duration-150 hover:bg-primary-light hover:text-primary"
            aria-label={dict.dashboard.topbar.notifications}
            aria-expanded={notifOpen}
            onClick={() => {
              setNotifOpen((v) => !v);
              setMenuOpen(false);
            }}
          >
            <BellIcon className="h-5 w-5" />
          </button>
          {notifOpen ? (
            <>
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                className="fixed inset-0 z-30 cursor-default"
                onClick={() => setNotifOpen(false)}
              />
              <div className="card absolute end-0 z-40 mt-2 w-64 p-4 shadow-[0_4px_16px_rgba(20,32,26,0.08)]">
                <p className="text-sm font-semibold">{dict.dashboard.topbar.notifications}</p>
                <p className="mt-2 text-sm text-ink-secondary">
                  {dict.dashboard.topbar.notificationsEmpty}
                </p>
              </div>
            </>
          ) : null}
        </div>

        <div className="relative">
          <button
            type="button"
            className="flex items-center gap-2 rounded-md border border-stroke py-1 pe-2 ps-1 transition-colors duration-150 hover:bg-primary-light"
            aria-label={dict.dashboard.topbar.userMenu}
            aria-expanded={menuOpen}
            onClick={() => {
              setMenuOpen((v) => !v);
              setNotifOpen(false);
            }}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-xs font-semibold text-white">
              {initials}
            </span>
            <span className="hidden max-w-[160px] truncate text-sm sm:block">{user.name}</span>
          </button>
          {menuOpen ? (
            <>
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                className="fixed inset-0 z-30 cursor-default"
                onClick={() => setMenuOpen(false)}
              />
              <div className="card absolute end-0 z-40 mt-2 w-64 p-4 shadow-[0_4px_16px_rgba(20,32,26,0.08)]">
                <p className="truncate text-sm font-semibold">{user.name}</p>
                <p className="truncate text-xs text-ink-secondary">{user.email}</p>
                <ul className="mt-3 flex flex-wrap gap-1.5">
                  {roles.map((role) => (
                    <li
                      key={role}
                      className="rounded-md bg-primary-light px-2 py-0.5 text-xs font-medium text-primary"
                    >
                      {dict.dashboard.roles[role]}
                    </li>
                  ))}
                </ul>
                <div className="mt-4 border-t border-stroke pt-3">
                  <button
                    type="button"
                    disabled={signingOut}
                    onClick={handleSignOut}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-ink transition-colors duration-150 hover:bg-primary-light disabled:opacity-60"
                  >
                    <LogoutIcon className="h-4 w-4" />
                    {dict.dashboard.topbar.signOut}
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
