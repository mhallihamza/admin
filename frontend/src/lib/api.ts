import { createClient } from "@/lib/supabase/client";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

export async function getBackendAccessToken(): Promise<string | null> {
  if (!backendUrl) return null;
  const supabase = createClient();
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export async function backendAuthHeaders(includeJson = false): Promise<Record<string, string> | null> {
  const token = await getBackendAccessToken();
  if (!token) return null;
  return {
    ...(includeJson ? { "Content-Type": "application/json" } : {}),
    Authorization: `Bearer ${token}`,
  };
}

export { backendUrl };
