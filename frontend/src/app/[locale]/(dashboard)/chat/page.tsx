import AccessDenied from "@/components/dashboard/access-denied";
import ChatClient from "@/components/dashboard/chat-client";
import { CITIZEN_ONLY } from "@/lib/dashboard/roles";
import { requireRoles } from "@/lib/dashboard/guard";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function ChatPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ conversation?: string }>;
}) {
  const { locale } = await params;
  const { conversation } = await searchParams;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  const { ok } = await requireRoles([...CITIZEN_ONLY]);
  if (!ok) {
    return <AccessDenied locale={safeLocale} dict={dict} />;
  }

  return <ChatClient locale={safeLocale} dict={dict} conversationId={conversation} />;
}
