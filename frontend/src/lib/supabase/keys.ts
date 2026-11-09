/**
 * Clés publiques Supabase (navigateur + middleware). Le nouveau format
 * « sb_publishable_... » remplace l'ancien « anon » JWT — les deux noms
 * de variable sont acceptés, l'un ou l'autre suffit. Valeurs jamais en
 * dur dans le code : uniquement dans .env.local.
 */
export function supabaseUrl(): string | undefined {
  return process.env.NEXT_PUBLIC_SUPABASE_URL || undefined;
}

export function supabasePublicApiKey(): string | undefined {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    undefined
  );
}
