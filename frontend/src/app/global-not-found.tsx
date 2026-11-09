import Link from "next/link";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "404 — Page introuvable / الصفحة غير موجودة",
  description: "La page demandée n'existe pas. الصفحة المطلوبة غير موجودة.",
};

export default function GlobalNotFound() {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-background font-sans text-ink antialiased">
        <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-6 text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-accent">404</p>
          <h1 className="mt-3 text-2xl font-bold text-ink">Page introuvable</h1>
          <p className="mt-2 text-sm text-ink-secondary">الصفحة المطلوبة غير موجودة.</p>
          <Link
            href="/fr"
            className="mt-6 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-dark"
          >
            Retour à l’accueil / العودة إلى الرئيسية
          </Link>
        </main>
      </body>
    </html>
  );
}
