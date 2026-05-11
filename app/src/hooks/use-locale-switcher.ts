"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import {
  LOCALE_COOKIE_MAX_AGE,
  LOCALE_COOKIE_NAME,
} from "@/i18n/locale-cookie";
import type { Locale } from "@/i18n/config";
import { authClient } from "@/lib/auth/client";

/**
 * 言語切替フロー (Phase 3 / Issue #107):
 *
 *  1. `document.cookie` に `NEXT_LOCALE=<locale>` を即時書き込み
 *     (`request.ts` の `getRequestConfig` は次の SSR でこの cookie を読む)
 *  2. ログイン中なら `PATCH /api/auth/me/locale` を投げて DB に永続化。
 *     ログアウト状態や API エラー時は cookie だけで動作するため silent
 *     (ユーザー視点では「とにかく言語が切り替わった」状態にする)
 *  3. `router.refresh()` で Server Components を再評価し、`next-intl` が
 *     新しい messages を載せ直して画面に反映される。
 *
 * `useTransition` で 1 トランザクションにまとめ、isPending を Switcher の
 * `disabled` に渡してユーザーが多重クリックできないようにする。
 */
export function useLocaleSwitcher() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const switchTo = (locale: Locale) => {
    startTransition(async () => {
      // 1) cookie は同期的に書く (router.refresh() より先)
      if (typeof document !== "undefined") {
        document.cookie =
          `${LOCALE_COOKIE_NAME}=${locale}; max-age=${LOCALE_COOKIE_MAX_AGE}; ` +
          `path=/; samesite=lax`;
      }

      // 2) DB 永続化 (失敗しても cookie で動くので fire-and-forget 風)
      try {
        await authClient.setPreferredLocale(locale);
      } catch (err) {
        // 未ログイン (401) や bare network エラーは cookie で十分機能するため
        // warn にとどめる。意図的にユーザーに見せない。
        console.warn(
          "[useLocaleSwitcher] setPreferredLocale failed (cookie still saved):",
          err,
        );
      }

      // 3) Server Components を再評価して翻訳を反映
      router.refresh();
    });
  };

  return { switchTo, isPending };
}
