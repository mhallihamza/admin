import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { supabasePublicApiKey, supabaseUrl } from "./keys";
import { cookies } from "next/headers";

/**
 * Server-side Supabase client for App Router components (session cookies).
 * Returns null when the environment variables are missing so callers can
 * redirect to the login page (which shows the configuration error).
 * Identity and roles always come from the verified session token here —
 * never from user input.
 */
export async function createClient() {
  const url = supabaseUrl();
  const anonKey = supabasePublicApiKey();

  if (!url || !anonKey) {
    return null;
  }

  const cookieStore = await cookies();

  return createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        } catch {
          // Called from a Server Component — middleware refreshes sessions.
        }
      },
    },
  });
}
