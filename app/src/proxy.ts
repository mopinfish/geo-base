import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { decideProxy } from "@/lib/auth/proxy-decisions";
import {
  FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE,
  LOCALES,
  type Locale,
} from "@/i18n/config";
import {
  LOCALE_COOKIE_MAX_AGE,
  LOCALE_COOKIE_NAME,
} from "@/i18n/locale-cookie";

/**
 * Resolve locale for the incoming request (Phase 3 / Issue #107).
 *
 * Priority (spec 5.3):
 *  1. `NEXT_LOCALE` cookie (= 明示切替後の永続化値、ユーザーが Admin UI から
 *     切替えたときに `useLocaleSwitcher` hook が書く想定 / PR-B 実装予定)
 *  2. `Accept-Language` header の先頭から `LOCALES` に含まれる locale
 *  3. `FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE` (= `ja`、既存 JA ユーザー保護)
 *
 * `DEFAULT_LOCALE` (= `en`) は API のフォールバック相当だが、proxy 上では
 * 「Accept-Language なしの新規訪問者」もとりあえず ja を見る想定。
 * 明示的に英語に切替えた場合は cookie で記憶される。
 *
 * NOTE (Phase 3a): `users.preferred_locale` (DB 永続化) と cookie の同期は
 * PR-B (`useLocaleSwitcher`) で実装する。本 PR では cookie は proxy が
 * Accept-Language から自動セットする経路のみ存在。login 直後の cookie
 * 書き込みも PR-B で `authClient.login()` 側に追加する想定。
 */
function resolveLocale(request: NextRequest): Locale {
  const cookie = request.cookies.get(LOCALE_COOKIE_NAME)?.value ?? "";
  if ((LOCALES as readonly string[]).includes(cookie)) {
    return cookie as Locale;
  }

  const acceptLanguage = request.headers.get("accept-language") ?? "";
  const candidates = acceptLanguage
    .split(",")
    .map((part) => part.split(";")[0]?.trim().split("-")[0]?.toLowerCase())
    .filter((c): c is string => Boolean(c));
  for (const c of candidates) {
    if ((LOCALES as readonly string[]).includes(c)) {
      return c as Locale;
    }
  }

  return FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE;
}

/** locale を cookie に永続化する (Set-Cookie ヘッダ追加)。 */
function attachLocaleCookie(
  response: NextResponse,
  request: NextRequest,
): NextResponse {
  // すでに valid cookie があれば書き換えない (期限延長は不要、ユーザーが
  // 明示切替したときに別経路で更新される)。
  const existing = request.cookies.get(LOCALE_COOKIE_NAME)?.value ?? "";
  if ((LOCALES as readonly string[]).includes(existing)) {
    return response;
  }
  response.cookies.set(LOCALE_COOKIE_NAME, resolveLocale(request), {
    maxAge: LOCALE_COOKIE_MAX_AGE,
    path: "/",
    sameSite: "lax",
  });
  return response;
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasRefresh = !!request.cookies.get("geo_base_refresh");
  const decision = decideProxy(pathname, hasRefresh);

  let response: NextResponse;
  switch (decision.kind) {
    case "redirect-login": {
      const url = new URL("/login", request.url);
      url.searchParams.set("next", decision.next);
      response = NextResponse.redirect(url);
      break;
    }
    case "redirect-home":
      response = NextResponse.redirect(new URL("/", request.url));
      break;
    case "next":
      response = NextResponse.next();
      break;
    default: {
      // 網羅性チェック（実行時の保険）— 想定外の値が来ても undefined は返さない
      const _exhaustive: never = decision;
      void _exhaustive;
      response = NextResponse.next();
    }
  }

  return attachLocaleCookie(response, request);
}

// matcher パターン（仕様は proxy-decisions.ts の `PROXY_MATCHER` を参照）。
//
// Next.js (Turbopack) は `config.matcher` を **コンパイル時に静的解析** するため、
// 別ファイルの定数を import しても受け付けず、リテラル文字列を直接渡す必要がある。
// そのため `proxy-decisions.ts` の `PROXY_MATCHER` と本ファイルのリテラル
// は **同一文字列** に保つ必要があり、テスト
// （`proxy-decisions.test.ts` の "matcher と proxy.ts のリテラル同期"）
// で同期を担保している。
export const config = {
  matcher: ["/((?!api(?:/|$)|_next/|.*\\.\\w+$).*)"],
};
