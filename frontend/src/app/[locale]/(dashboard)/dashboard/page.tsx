import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import type { AppRole } from "@/lib/dashboard/nav";
import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

type LatestConversation = { id: string; title: string; updated_at: string };
type Reminder = { id: string; title: string; notes: string; status: string };

async function countRows(
  supabase: NonNullable<Awaited<ReturnType<typeof createClient>>>,
  table: string,
  userId: string,
  filters: Array<[string, string]> = []
) {
  let query = supabase.from(table).select("id", { count: "exact", head: true }).eq("user_id", userId);
  for (const [column, value] of filters) {
    query = query.eq(column, value);
  }
  const result = await query;
  return result.error ? 0 : result.count ?? 0;
}

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);
  const isAr = safeLocale === "ar";

  const copy = isAr
    ? {
        eyebrow: "المساعدة الرسمية المعتمدة",
        title: "كيف يمكننا مساعدتك اليوم؟",
        subtitle:
          "احصل على جواب موثوق انطلاقاً من الوثائق الرسمية المعتمدة فقط. وإذا لم يجد المساعد جواباً معتمداً، يمكنك طلب مراجعة إنسانية.",
        ask: "اطرح سؤالك",
        reminders: "ملاحظاتي",
        conversations: "محادثاتي",
        saved: "إجابات محفوظة",
        remindersLabel: "ملاحظاتي المفتوحة",
        verifiedTitle: "جواب مبني على الوثائق المعتمدة",
        verifiedBody: "المصادر المعروضة مع كل جواب هي وثائق رسمية مُعتمدة في المنصة (الوثيقة، المادة والنسخة).",
        askHumanTitle: "لا جواب معتمد؟",
        askHumanBody: "اطلب مراجعة إنسانية من فريق مختص. لا نرسل طلب CNIE أو جواز سفر ولا نعالجه نيابة عنك.",
        howTitle: "كيف يعمل",
        step1: "اطرح سؤالك بكلماتك (بالفرنسية أو العربية)",
        step2: "راجع الجواب ومصادره الرسمية المقترحة",
        step3: "احفظ الجواب أو اطرحه على مراجع بشري",
        latest: "آخر محادثاتك",
        openConversation: "فتح",
        openReminders: "فتح ملاحظاتي",
        account: "حسابك ومسؤولياتك",
        roles: "الأدوار",
        privateNote: "كل محادثة وكل جواب تحفظه خاص برمز حسابك فقط.",
        privacyTitle: "خصوصيتك محمية",
        privacyBody: "لا تظهر محتوى محادثاتك إلا إذا طلبت مراجعة إنسانية وقمت باختيار السبب.",
      }
    : {
        eyebrow: "Aide officielle, vérifiée",
        title: "Comment pouvons-nous vous aider aujourd'hui ?",
        subtitle:
          "Obtenez une réponse fiable à partir des documents officiels approuvés uniquement. Si aucun élément officiel ne répond à votre question, vous pouvez demander une revue humaine.",
        ask: "Poser une question",
        reminders: "Mes démarches",
        conversations: "Conversations",
        saved: "Réponses enregistrées",
        remindersLabel: "Démarches à retenir",
        verifiedTitle: "Réponses fondées sur les documents approuvés",
        verifiedBody: "Chaque réponse cite les documents officiels approuvés (document, article, version).",
        askHumanTitle: "Aucune réponse approuvée ?",
        askHumanBody: "Demandez une revue humaine par un spécialiste. Aucune demande CNIE ou passeport n'est déposée ou traitée ici.",
        howTitle: "Comment ça fonctionne",
        step1: "Posez votre question avec vos mots (français ou arabe)",
        step2: "Consultez la réponse et ses sources officielles",
        step3: "Enregistrez la réponse ou demandez une revue humaine",
        latest: "Vos dernières conversations",
        openConversation: "Ouvrir",
        openReminders: "Ouvrir mes démarches",
        account: "Votre compte et vos responsabilités",
        roles: "Rôles",
        privateNote: "Chaque conversation et chaque réponse enregistrée reste liée à votre compte.",
        privacyTitle: "Votre vie privée est protégée",
        privacyBody: "Le contenu de vos conversations n'est consultable que si vous demandez une revue humaine en précisant un motif.",
      };

  const supabase = await createClient();
  if (!supabase) {
    redirect(`/${safeLocale}/login`);
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect(`/${safeLocale}/login`);
  }

  const [
    profileResult,
    rolesResult,
    conversationsCount,
    savedCount,
    openRemindersCount,
    latestConversationsResult,
    openRemindersResult,
  ] = await Promise.all([
    supabase.from("profiles").select("full_name").eq("id", user.id).single(),
    supabase.from("user_roles").select("role").eq("user_id", user.id),
    countRows(supabase, "conversations", user.id),
    countRows(supabase, "saved_procedures", user.id),
    countRows(supabase, "citizen_reminders", user.id, [["status", "OPEN"]]),
    supabase
      .from("conversations")
      .select("id, title, updated_at")
      .eq("user_id", user.id)
      .order("updated_at", { ascending: false })
      .limit(3),
    supabase
      .from("citizen_reminders")
      .select("id, title, notes, status")
      .eq("user_id", user.id)
      .eq("status", "OPEN")
      .order("updated_at", { ascending: false })
      .limit(3),
  ]);

  const roles = ((rolesResult.data ?? []) as { role: AppRole }[]).map((row) => row.role);
  const displayName = profileResult.data?.full_name || user.email || "";
  const latestConversations = (latestConversationsResult.data ?? []) as LatestConversation[];
  const openReminders = (openRemindersResult.data ?? []) as Reminder[];
  const stats = [
    { label: copy.conversations, value: conversationsCount, href: `/${safeLocale}/conversations` },
    { label: copy.saved, value: savedCount, href: `/${safeLocale}/saved-procedures` },
    { label: copy.remindersLabel, value: openRemindersCount, href: `/${safeLocale}/processes` },
  ];

  return (
    <div className="space-y-6">
      {/* Premium citizen hero */}
      <section className="relative overflow-hidden rounded-xl border border-primary/20 bg-gradient-to-br from-[#052e22] via-primary to-[#0d6b44] px-6 py-8 text-white sm:px-8 sm:py-10">
        <div aria-hidden="true" className="pointer-events-none absolute -end-16 -top-20 h-72 w-72 rounded-full border border-white/10 bg-white/5" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-24 -start-20 h-72 w-72 rounded-full border border-white/10 bg-white/5" />
        <div className="relative max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#F4C95D]">{copy.eyebrow}</p>
          <p className="mt-3 text-sm text-white/80">{dict.dashboard.home.welcome}, {displayName}</p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">{copy.title}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-white/90">{copy.subtitle}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href={`/${safeLocale}/chat`} className="inline-flex items-center rounded-md bg-white px-5 py-3 text-sm font-semibold text-primary transition-colors hover:bg-primary-light">
              {copy.ask} →
            </Link>
            <Link href={`/${safeLocale}/processes`} className="inline-flex items-center rounded-md border border-white/25 bg-white/10 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-white/20">
              {copy.reminders}
            </Link>
          </div>
        </div>
      </section>

      {/* KPIs */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {stats.map((stat) => (
          <Link key={stat.label} href={stat.href} className="card p-5 transition-colors hover:border-primary/40 hover:bg-primary-light/30">
            <p className="text-sm text-ink-secondary">{stat.label}</p>
            <p className="mt-3 text-4xl font-semibold leading-none">{stat.value}</p>
            <p className="mt-3 text-xs font-medium text-primary">{isAr ? "فتح" : "Ouvrir"} →</p>
          </Link>
        ))}
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_1fr]">
        {/* Latest conversations */}
        <section className="card p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stroke pb-4">
            <div>
              <h2 className="card-title">{copy.latest}</h2>
              <p className="mt-1 text-xs text-ink-secondary">{copy.privateNote}</p>
            </div>
            <Link href={`/${safeLocale}/conversations`} className="btn-outline h-9 px-4 text-xs">
              {isAr ? "عرض الكل" : "Voir tout"}
            </Link>
          </div>
          {latestConversations.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-ink-secondary">{dict.dashboard.citizen.historyEmpty}</p>
              <Link href={`/${safeLocale}/chat`} className="btn-primary mt-4">{copy.ask}</Link>
            </div>
          ) : (
            <ul className="mt-2 divide-y divide-stroke">
              {latestConversations.map((conversation) => (
                <li key={conversation.id} className="py-3">
                  <Link href={`/${safeLocale}/chat?conversation=${encodeURIComponent(conversation.id)}`} className="group flex items-center justify-between gap-4">
                    <span className="font-medium transition-colors group-hover:text-primary">{conversation.title}</span>
                    <span className="shrink-0 text-xs text-ink-secondary">{copy.openConversation} →</span>
                  </Link>
                  <p className="mt-1 text-xs text-ink-secondary">{conversation.updated_at?.slice(0, 16).replace("T", " ")}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Personal reminders */}
        <section className="card p-6">
          <div className="flex items-center justify-between gap-3 border-b border-stroke pb-4">
            <div>
              <h2 className="card-title">{copy.remindersLabel}</h2>
              <p className="mt-1 text-xs text-ink-secondary">{isAr ? "خاص بك فقط" : "Privé — visible uniquement par vous"}</p>
            </div>
            <Link href={`/${safeLocale}/processes`} className="btn-outline h-9 px-4 text-xs">
              {isAr ? "إضافة" : "Ajouter"}
            </Link>
          </div>
          {openReminders.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-ink-secondary">{isAr ? "لا توجد ملاحظات مفتوحة." : "Aucune démarche à retenir."}</p>
              <Link href={`/${safeLocale}/processes`} className="btn-outline mt-4">{copy.openReminders}</Link>
            </div>
          ) : (
            <ul className="mt-4 space-y-3">
              {openReminders.map((reminder) => (
                <li key={reminder.id} className="rounded-md border border-stroke bg-background p-3">
                  <p className="text-sm font-medium">{reminder.title}</p>
                  {reminder.notes ? <p className="mt-1 line-clamp-2 text-xs text-ink-secondary">{reminder.notes}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* How it works + trust */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card p-6 lg:col-span-2">
          <h2 className="card-title">{copy.howTitle}</h2>
          <ol className="mt-5 grid gap-4 sm:grid-cols-3">
            {[copy.step1, copy.step2, copy.step3].map((step, index) => (
              <li key={step} className="rounded-md border border-stroke bg-background p-4">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white">{index + 1}</span>
                <p className="mt-3 text-sm leading-6 text-ink-secondary">{step}</p>
              </li>
            ))}
          </ol>
        </div>
        <aside className="card border-primary/20 bg-primary-light/40 p-6">
          <h2 className="card-title text-primary">{copy.verifiedTitle}</h2>
          <p className="mt-2 text-sm leading-6 text-ink-secondary">{copy.verifiedBody}</p>
          <h3 className="mt-5 text-sm font-semibold text-primary">{copy.askHumanTitle}</h3>
          <p className="mt-1 text-sm leading-6 text-ink-secondary">{copy.askHumanBody}</p>
        </aside>
      </section>

      {/* Account */}
      <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="card-title">{copy.account}</h2>
            <p className="mt-1 max-w-2xl text-sm text-ink-secondary">{copy.privacyTitle}: {copy.privacyBody}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-secondary">{copy.roles}</p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {roles.map((role) => (
                <li key={role} className="rounded-md bg-primary-light px-2.5 py-1 text-xs font-medium text-primary">
                  {dict.dashboard.roles[role]}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
