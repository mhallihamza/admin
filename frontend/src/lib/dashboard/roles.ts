import type { AppRole } from "@/lib/dashboard/nav";

/** Reusable role sets for section guards (mirrors the navigation rules).
 * Rôles fusionnés (2026-11) : l'ancien CONTENT_APPROVER rejoint SYSTEM_ADMIN
 * — un seul rôle « admin » gère documents + administration. CONTENT_APPROVER
 * reste accepté côté garde pour les jetons existants. */
export const CITIZEN_ONLY: AppRole[] = ["CITIZEN"];

export const REVIEW_STAFF: AppRole[] = [
  "EMPLOYEE",
  "SYSTEM_ADMIN",
  "PLATFORM_SUPER_ADMIN",
];

export const CONTENT_STAFF: AppRole[] = [
  "SYSTEM_ADMIN",
  "PLATFORM_SUPER_ADMIN",
  "CONTENT_APPROVER",
];

export const ADMIN_ONLY: AppRole[] = ["SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN"];

export const SECURITY_STAFF: AppRole[] = [
  "SECURITY_AUDITOR",
  "SYSTEM_ADMIN",
  "PLATFORM_SUPER_ADMIN",
];

/** Red team report details (2026-11, owner's request): auditor, admin and
 * super admin — the merged admin role follows the reports. */
export const RED_TEAM_DETAIL_ROLES: AppRole[] = [
  "SECURITY_AUDITOR",
  "SYSTEM_ADMIN",
  "PLATFORM_SUPER_ADMIN",
];
