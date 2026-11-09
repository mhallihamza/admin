"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Alert from "@/components/alert";
import { createClient } from "@/lib/supabase/client";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/lib/i18n/dictionaries";

export default function RegisterForm({
  locale,
  dict,
}: {
  locale: Locale;
  dict: Dictionary;
}) {
  const t = dict.auth.register;
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(false);

    if (password !== confirmPassword) {
      setError(t.errorMismatch);
      return;
    }
    if (password.length < 8) {
      setError(t.errorShort);
      return;
    }

    const supabase = createClient();
    if (!supabase) {
      setError(t.errorConfig);
      return;
    }

    setSubmitting(true);
    const { data, error: authError } = await supabase.auth.signUp({
      email,
      password,
    });
    setSubmitting(false);

    if (authError) {
      if (/already/i.test(authError.message)) {
        setError(t.errorAlreadyExists);
      } else {
        setError(t.errorGeneric);
      }
      return;
    }

    if (data.session) {
      // Email confirmation disabled: the user is signed in immediately.
      // compte créé et session active -> tableau de bord
      router.push(`/${locale}/dashboard`);
      router.refresh();
      return;
    }

    setSuccess(true);
  }

  return (
    <div className="card p-8">
      <h1 className="page-title">{t.title}</h1>

      {error ? (
        <div className="mt-6">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}
      {success ? (
        <div className="mt-6">
          <Alert tone="success">{t.successMessage}</Alert>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="register-email" className="block text-sm font-medium">
            {t.emailLabel}
          </label>
          <input
            id="register-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="input mt-1.5"
          />
        </div>
        <div>
          <label htmlFor="register-password" className="block text-sm font-medium">
            {t.passwordLabel}
          </label>
          <input
            id="register-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="input mt-1.5"
          />
        </div>
        <div>
          <label htmlFor="register-confirm" className="block text-sm font-medium">
            {t.confirmPasswordLabel}
          </label>
          <input
            id="register-confirm"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="input mt-1.5"
          />
        </div>
        <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-60">
          {submitting ? t.submitting : t.submit}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-secondary">
        {t.haveAccount}{" "}
        <Link
          href={`/${locale}/login`}
          className="font-medium text-primary underline-offset-2 hover:underline"
        >
          {t.loginLink}
        </Link>
      </p>
    </div>
  );
}
