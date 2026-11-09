import { NextResponse, type NextRequest } from "next/server";
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { supabasePublicApiKey, supabaseUrl } from "@/lib/supabase/keys";
import { defaultLocale, locales } from "@/lib/i18n/config";

/**
 * 1) Redirects every page request to a locale-prefixed path (/fr/..., /ar/...).
 * 2) Refreshes the Supabase auth session so server components always see a
 *    valid token (the recommended @supabase/ssr pattern).
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const hasLocale = locales.some(
    (locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)
  );
  if (!hasLocale) {
    const url = request.nextUrl.clone();
    url.pathname = `/${defaultLocale}${pathname === "/" ? "" : pathname}`;
    return NextResponse.redirect(url);
  }

  let response = NextResponse.next({ request });

  const url = supabaseUrl();
  const anonKey = supabasePublicApiKey();
  if (url && anonKey) {
    const supabase = createServerClient(url, anonKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    });
    // Validates the session and triggers a token refresh when needed.
    await supabase.auth.getUser();
  }

  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|icon|favicon.ico|.*\\..*).*)"],
};
