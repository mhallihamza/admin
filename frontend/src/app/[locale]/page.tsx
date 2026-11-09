import Header from "@/components/landing/header";
import Hero from "@/components/landing/hero";
import HowItWorks from "@/components/landing/how-it-works";
import Services from "@/components/landing/services";
import SourcesBand from "@/components/landing/sources-band";
import Faq from "@/components/landing/faq";
import Footer from "@/components/landing/footer";
import { defaultLocale, isLocale, type Locale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/dictionaries";

export default async function LandingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const safeLocale: Locale = isLocale(locale) ? locale : defaultLocale;
  const dict = getDictionary(safeLocale);

  return (
    <>
      <Header locale={safeLocale} dict={dict} />
      <main>
        <Hero dict={dict.hero} />
        <HowItWorks dict={dict.howItWorks} />
        <Services dict={dict.services} />
        <SourcesBand dict={dict.sources} />
        <Faq dict={dict.faq} />
      </main>
      <Footer dict={dict.footer} activeLocale={safeLocale} />
    </>
  );
}
