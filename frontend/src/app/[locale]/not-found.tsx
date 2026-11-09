import Link from "next/link";

/** Fallback for unknown paths under a locale (bilingual, minimal). */
export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="card p-8 text-center">
        <p className="text-3xl font-semibold">404</p>
        <p className="mt-2 text-sm text-ink-secondary">
          Page introuvable · الصفحة غير موجودة
        </p>
        <Link href="/fr" className="btn-primary mt-6">
          Retour à l'accueil · العودة إلى الرئيسية
        </Link>
      </div>
    </main>
  );
}
