import type { Metadata } from "next";
import AuthShell from "@/components/auth/auth-shell";
import LoginForm from "@/components/auth/login-form";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const dict = getDictionary(isLocale(locale) ? locale : defaultLocale);
  return { title: `${dict.auth.login.title} — ${dict.meta.title}` };
}

export default async function LoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  return (
    <AuthShell locale={safeLocale}>
      <LoginForm locale={safeLocale} dict={dict} />
    </AuthShell>
  );
}
