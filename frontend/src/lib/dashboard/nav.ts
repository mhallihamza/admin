import type { Dictionary } from "@/lib/i18n/dictionaries";
import type { Locale } from "@/lib/i18n/config";

export type AppRole =
  | "VISITOR"
  | "CITIZEN"
  | "EMPLOYEE"
  | "CONTENT_APPROVER"
  | "SYSTEM_ADMIN"
  | "SECURITY_AUDITOR"
  | "PLATFORM_SUPER_ADMIN";

export interface NavItem {
  key: keyof Dictionary["dashboard"]["sidebar"]["items"];
  /** Route under /{locale}; only `dashboard` exists in Phase 2. */
  href: string;
  enabled: boolean;
  roles: AppRole[];
}

export interface NavGroup {
  key: keyof Dictionary["dashboard"]["sidebar"]["groups"];
  items: NavItem[];
}

const ALL_STAFF: AppRole[] = [
  "CITIZEN",
  "EMPLOYEE",
  "CONTENT_APPROVER",
  "SYSTEM_ADMIN",
  "SECURITY_AUDITOR",
  "PLATFORM_SUPER_ADMIN",
];

const CITIZEN_ONLY: AppRole[] = ["CITIZEN"];

const REVIEW_STAFF: AppRole[] = ["EMPLOYEE", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN"];

const CONTENT_STAFF: AppRole[] = ["CONTENT_APPROVER", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN"];

const ADMIN_ONLY: AppRole[] = ["SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN"];

const SECURITY_STAFF: AppRole[] = [
  "SECURITY_AUDITOR",
  "SYSTEM_ADMIN",
  "PLATFORM_SUPER_ADMIN",
];

/**
 * Shared dashboard navigation. All Phase 3 sections are enabled; access is
 * still filtered per role both here and on every page (server-side check).
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    key: "main",
    items: [{ key: "dashboard", href: "/dashboard", enabled: true, roles: ALL_STAFF }],
  },
  {
    key: "citizen",
    items: [
      { key: "chat", href: "/chat", enabled: true, roles: CITIZEN_ONLY },
      { key: "conversations", href: "/conversations", enabled: true, roles: CITIZEN_ONLY },
      { key: "saved", href: "/saved-procedures", enabled: true, roles: CITIZEN_ONLY },
      { key: "processes", href: "/processes", enabled: true, roles: CITIZEN_ONLY },
    ],
  },
  {
    key: "review",
    items: [{ key: "reviewQueue", href: "/review", enabled: true, roles: REVIEW_STAFF }],
  },
  {
    key: "content",
    items: [{ key: "documents", href: "/admin/documents", enabled: true, roles: CONTENT_STAFF }],
  },
  {
    key: "administration",
    items: [
      { key: "overview", href: "/admin/overview", enabled: true, roles: ADMIN_ONLY },
      { key: "usersRoles", href: "/admin/users", enabled: true, roles: ADMIN_ONLY },
      { key: "permissions", href: "/admin/permissions", enabled: true, roles: ADMIN_ONLY },
      { key: "workflows", href: "/admin/workflows", enabled: true, roles: ADMIN_ONLY },
    ],
  },
  {
    key: "security",
    items: [{ key: "security", href: "/security", enabled: true, roles: SECURITY_STAFF }],
  },
];

export function visibleNavGroups(roles: AppRole[]): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => item.roles.some((role) => roles.includes(role))),
  })).filter((group) => group.items.length > 0);
}

export function pageTitleForPath(
  pathname: string,
  locale: Locale,
  dict: Dictionary
): string {
  // Longest match wins; detail routes (/review/CR-2041) match their section.
  const matches = NAV_GROUPS.flatMap((group) => group.items)
    .filter((item) => {
      const base = `/${locale}${item.href}`;
      return pathname === base || pathname.startsWith(`${base}/`);
    })
    .sort((a, b) => b.href.length - a.href.length);
  if (matches.length > 0) {
    return dict.dashboard.sidebar.items[matches[0].key];
  }
  return dict.dashboard.sidebar.items.dashboard;
}
