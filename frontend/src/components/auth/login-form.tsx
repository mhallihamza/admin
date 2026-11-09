"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Alert from "@/components/alert";
import { createClient } from "@/lib/supabase/client";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

export default function LoginForm({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.auth.login;
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const supabase = createClient();
    if (!supabase) {
      setError(t.errorConfig);
      return;
    }

    setSubmitting(true);
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setSubmitting(false);

    if (authError) {
      if (authError.status === 400 && /invalid/i.test(authError.message)) {
        setError(t.errorInvalid);
      } else if (/confirm/i.test(authError.message)) {
        setError(t.errorNotConfirmed);
      } else {
        setError(t.errorGeneric);
      }
      return;
    }

    // connexion réussie -> tableau de bord (visiteur : carte « Accès restreint »)
    router.push(`/${locale}/dashboard`);
    router.refresh();
  }

  return (
    <div className="card p-8">
      <h1 className="page-title">{t.title}</h1>

      {error ? (
        <div className="mt-6">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="login-email" className="block text-sm font-medium">
            {t.emailLabel}
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="input mt-1.5"
          />
        </div>
        <div>
          <label htmlFor="login-password" className="block text-sm font-medium">
            {t.passwordLabel}
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="input mt-1.5"
          />
        </div>
        <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
          {submitting ? t.submitting : t.submit}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-secondary">
        {t.noAccount}{" "}
        <Link
          href={`/${locale}/register`}
          className="font-medium text-primary underline-offset-2 hover:underline"
        >
          {t.createAccountLink}
        </Link>
      </p>
    </div>
  );
}
