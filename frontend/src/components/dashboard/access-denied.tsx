import Link from "next/link";
import { ShieldIcon } from "@/components/icons";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

/** Shown when the session has no staff role (VISITOR) or a disabled profile. */
export default function AccessDenied({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  return (
    <div className="mx-auto max-w-md pt-10">
      <div className="card p-8 text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-light text-primary">
          <ShieldIcon className="h-6 w-6" />
        </span>
        <h1 className="card-title mt-4">{dict.dashboard.accessDenied.title}</h1>
        <p className="mt-2 text-sm text-ink-secondary">{dict.dashboard.accessDenied.message}</p>
        <Link href={`/${locale}`} className="btn-primary mt-6">
          {dict.dashboard.accessDenied.backHome}
        </Link>
      </div>
    </div>
  );
}
