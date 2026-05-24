import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";
import { Noto_Sans_JP } from "next/font/google";

import "./globals.css";
import { AuthProvider } from "@/lib/auth/context";

const notoSansJP = Noto_Sans_JP({
  subsets: ["latin", "japanese" as any],
  weight: ["400", "500", "700"],
  display: "swap",
  variable: "--font-noto-sans-jp",
  preload: false,
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("common");
  return {
    title: t("app.title"),
    description: t("app.description"),
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // i18n Phase 3 (#107): `proxy.ts` がセットした `NEXT_LOCALE` cookie を
  // 元に、Server / Client Components 両側で使う messages を読む。
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} className={notoSansJP.variable}>
      <body className="antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <AuthProvider>{children}</AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
