import { createBrowserClient } from "@supabase/ssr";
import { supabasePublicApiKey, supabaseUrl } from "./keys";

/**
 * Browser Supabase client for Auth. Returns null when the environment
 * variables are missing so pages can show a clear configuration error
 * instead of crashing. Values never live in code — only in .env.local.
 */
export function createClient() {
  const url = supabaseUrl();
  const anonKey = supabasePublicApiKey();

  if (!url || !anonKey) {
    return null;
  }

  return createBrowserClient(url, anonKey);
}

export type SupabaseBrowserClient = ReturnType<typeof createBrowserClient>;
