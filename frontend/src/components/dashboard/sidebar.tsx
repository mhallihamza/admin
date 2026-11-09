"use client";

import Link from "next/link";
import Brand from "@/components/brand";
import Logo from "@/components/logo";
import SidebarNav from "@/components/dashboard/sidebar-nav";
import type { AppRole } from "@/lib/dashboard/nav";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/**
 * Responsive sidebar: 260 px with labels at >=1024 px, icon rail between
 * 768 px and 1023 px, hidden below 768 px (the shell shows a drawer).
 */
export default function Sidebar({
  locale,
  dict,
  roles,
}: {
  locale: Locale;
  dict: Dictionary;
  roles: AppRole[];
}) {
  return (
    <aside className="sticky top-0 hidden h-screen w-[72px] shrink-0 flex-col border-e border-stroke bg-white md:flex lg:w-[260px]">
      <div className="flex h-16 shrink-0 items-center border-b border-stroke px-3 lg:px-5">
        <span className="lg:hidden">
          <Link href={`/${locale}`} aria-label={dict.brand}>
            <Logo />
          </Link>
        </span>
        <span className="hidden lg:block">
          <Brand locale={locale} />
        </span>
      </div>
      <SidebarNav locale={locale} dict={dict} roles={roles} />
    </aside>
  );
}
