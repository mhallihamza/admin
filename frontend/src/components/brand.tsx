import Link from "next/link";
import Logo from "@/components/logo";
import type { Locale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

/** Logo mark + platform name, linking back to the locale home. */
export default function Brand({ locale }: { locale: Locale }) {
  return (
    <Link href={`/${locale}`} className="flex items-center gap-3">
      <Logo />
      <span className="text-base font-semibold">{getDictionary(locale).brand}</span>
    </Link>
  );
}
