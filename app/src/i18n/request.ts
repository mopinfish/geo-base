/**
 * next-intl の `getRequestConfig` を提供 (Phase 3 / Issue #107)。
 *
 * Server Components で `getTranslations()` を呼んだときに、ここで読んだ
 * messages が使われる。Client Components 側は `NextIntlClientProvider`
 * (app/src/app/layout.tsx) 経由で同じ messages が渡る。
 *
 * 解決優先順位 (spec 5.3 と整合):
 *  1. `NEXT_LOCALE` cookie (proxy.ts が事前にセット)
 *  2. それ以外は `DEFAULT_LOCALE`
 *
 * `users.preferred_locale` (DB) と `Accept-Language` の解決は proxy.ts 側で
 * 行い、結果を cookie に書く方式。これにより本ファイルは cookie だけを見れば
 * よい構造になる。
 */

import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";

import { DEFAULT_LOCALE, LOCALES, NAMESPACES, type Locale } from "./config";
import { LOCALE_COOKIE_NAME } from "./locale-cookie";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get(LOCALE_COOKIE_NAME)?.value ?? "";
  const locale: Locale = (LOCALES as readonly string[]).includes(raw)
    ? (raw as Locale)
    : DEFAULT_LOCALE;

  // namespace ごとに JSON を eager に読む。ファイル数が少ない (現状 2) ため
  // 性能影響は無視できる。Phase 3 後半で増えたらコード分割を検討する。
  const messages: Record<string, Record<string, unknown>> = {};
  for (const ns of NAMESPACES) {
    messages[ns] = (await import(`@/locales/${locale}/${ns}.json`)).default;
  }

  return { locale, messages };
});
