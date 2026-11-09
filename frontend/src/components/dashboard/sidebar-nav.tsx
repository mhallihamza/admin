"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, SVGProps } from "react";
import {
  ActivityIcon,
  BookmarkIcon,
  ChatIcon,
  ClockIcon,
  FileTextIcon,
  GridIcon,
  HomeIcon,
  InboxIcon,
  KeyIcon,
  ShieldIcon,
  UsersIcon,
} from "@/components/icons";
import type { AppRole, NavGroup } from "@/lib/dashboard/nav";
import { visibleNavGroups } from "@/lib/dashboard/nav";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

type ItemKey = keyof Dictionary["dashboard"]["sidebar"]["items"];

const ITEM_ICONS: Record<ItemKey, ComponentType<SVGProps<SVGSVGElement>>> = {
  dashboard: HomeIcon,
  chat: ChatIcon,
  conversations: ClockIcon,
  saved: BookmarkIcon,
  processes: InboxIcon,
  reviewQueue: InboxIcon,
  documents: FileTextIcon,
  overview: GridIcon,
  usersRoles: UsersIcon,
  permissions: KeyIcon,
  workflows: ActivityIcon,
  security: ShieldIcon,
};

interface SidebarNavProps {
  locale: Locale;
  dict: Dictionary;
  roles: AppRole[];
}

/**
 * Navigation list shared by the responsive sidebar and the mobile drawer.
 * Active item: 3 px green start bar + light green background (flips with RTL
 * thanks to the logical border-s utility).
 */
export default function SidebarNav({ locale, dict, roles }: SidebarNavProps) {
  const pathname = usePathname();
  const groups: NavGroup[] = visibleNavGroups(roles);

  return (
    <nav aria-label={dict.brand} className="flex-1 space-y-6 overflow-y-auto p-3 lg:p-5">
      {groups.map((group) => (
        <div key={group.key}>
          <p className="mb-2 hidden px-2 text-xs font-semibold uppercase tracking-wide text-ink-secondary lg:block">
            {dict.dashboard.sidebar.groups[group.key]}
          </p>
          <ul className="space-y-1">
            {group.items.map((item) => {
              const Icon = ITEM_ICONS[item.key];
              const label = dict.dashboard.sidebar.items[item.key];
              const active = pathname === `/${locale}${item.href}`;
              const base =
                "flex items-center gap-3 rounded-md border-s-[3px] px-2 py-2 text-sm transition-colors duration-150";

              if (!item.enabled) {
                return (
                  <li key={item.key}>
                    <span
                      aria-disabled="true"
                      title={dict.dashboard.sidebar.disabledHint}
                      className={`${base} cursor-not-allowed border-transparent text-ink-secondary/60`}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="hidden lg:block">{label}</span>
                    </span>
                  </li>
                );
              }

              return (
                <li key={item.key}>
                  <Link
                    href={`/${locale}${item.href}`}
                    aria-current={active ? "page" : undefined}
                    className={`${base} ${
                      active
                        ? "border-primary bg-primary-light font-medium text-primary"
                        : "border-transparent text-ink-secondary hover:bg-primary-light/60 hover:text-ink"
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="hidden lg:block">{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
