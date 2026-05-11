/**
 * next-intl の `getRequestConfig` を提供 (Phase 3 / Issue #107)。
 *
 * Server Components で `getTranslations()` を呼んだときに、ここで読んだ
 * messages が使われる。Client Components 側は `NextIntlClientProvider`
 * (app/src/app/layout.tsx) 経由で同じ messages が渡る。
 *
 * 解決優先順位 (spec 5.3 と整合):
 *  1. `NEXT_LOCALE` cookie (proxy.ts が前回までのリクエストで set 済み、
 *     または `useLocaleSwitcher` hook が明示切替時に書き込み — PR-B 実装予定)
 *  2. `Accept-Language` header の先頭から `LOCALES` に含まれる locale
 *     ← **初回 SSR (cookie 未セット)** のときの一次フォールバック。これが
 *     ないと proxy.ts は cookie を response 側にしかセットできないため
 *     最初のレンダーが常に `DEFAULT_LOCALE` (= `en`) になり、
 *     Accept-Language=ja のユーザーが初回だけ英語表示される
 *     (Copilot PR #127 round 1 指摘)。
 *  3. `FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE` (= `ja`、既存 JA ユーザー保護)
 */

import { getRequestConfig } from "next-intl/server";
import { cookies, headers } from "next/headers";

import {
  FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE,
  LOCALES,
  NAMESPACES,
  type Locale,
} from "./config";
import { LOCALE_COOKIE_NAME } from "./locale-cookie";
import { parseAcceptLanguage } from "./parse-accept-language";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get(LOCALE_COOKIE_NAME)?.value ?? "";
  let locale: Locale;
  if ((LOCALES as readonly string[]).includes(raw)) {
    locale = raw as Locale;
  } else {
    // 初回 SSR (cookie 不在) は Accept-Language → ja フォールバックの順。
    const headerStore = await headers();
    const acceptLanguage = headerStore.get("accept-language") ?? "";
    locale =
      parseAcceptLanguage(acceptLanguage) ?? FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE;
  }

  // namespace ごとに JSON を eager に読む。ファイル数が少ない (現状 2) ため
  // 性能影響は無視できる。Phase 3 後半で増えたらコード分割を検討する。
  const messages: Record<string, Record<string, unknown>> = {};
  for (const ns of NAMESPACES) {
    messages[ns] = (await import(`@/locales/${locale}/${ns}.json`)).default;
  }

  return { locale, messages };
});
