"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import Sidebar from "@/components/dashboard/sidebar";
import SidebarNav from "@/components/dashboard/sidebar-nav";
import Topbar from "@/components/dashboard/topbar";
import { CloseIcon } from "@/components/icons";
import type { AppRole } from "@/lib/dashboard/nav";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

interface DashboardShellProps {
  locale: Locale;
  dict: Dictionary;
  user: { name: string; email: string };
  roles: AppRole[];
  children: ReactNode;
}

/**
 * Shared dashboard shell: sidebar (260 px / icon rail / mobile drawer),
 * 64 px top bar, and the content area on the page background.
 */
export default function DashboardShell({
  locale,
  dict,
  user,
  roles,
  children,
}: DashboardShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar locale={locale} dict={dict} roles={roles} />

      {drawerOpen ? (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            aria-hidden="true"
            tabIndex={-1}
            className="absolute inset-0 cursor-default bg-ink/40"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 start-0 flex w-[260px] flex-col bg-white shadow-[0_4px_16px_rgba(20,32,26,0.08)]">
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-stroke px-5">
              <Link href={`/${locale}`}>{dict.brand}</Link>
              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-stroke text-ink"
                aria-label={dict.dashboard.topbar.menuClose}
                onClick={() => setDrawerOpen(false)}
              >
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>
            <SidebarNav locale={locale} dict={dict} roles={roles} />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          locale={locale}
          dict={dict}
          user={user}
          roles={roles}
          onMenuClick={() => setDrawerOpen(true)}
        />
        <main className="flex-1 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
